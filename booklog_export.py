from playwright.sync_api import sync_playwright
import csv
import json
import os
import smtplib
from pathlib import Path
from email.message import EmailMessage

BASE_URL = "https://booklog.jp/users/soraaa51"
OUTPUT = Path("books.csv")

all_books = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page_number = 1

    while True:
        url = f"{BASE_URL}?page={page_number}"

        print(f"{page_number}ページ目を取得中...")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        elements = page.locator("[data-book]")
        count = elements.count()

        print(f"  {count}冊見つかりました")

        if count == 0:
            break

        page_books = []

        for i in range(count):
            raw = elements.nth(i).get_attribute("data-book")

            if not raw:
                continue

            try:
                data = json.loads(raw)
            except Exception:
                continue

            item = data.get("item", {})

            book = {
                "booklog_id": data.get("book_id", ""),
                "title": data.get("title", ""),
                "author": item.get("author", ""),
                "rating": data.get("rank", ""),
                "status": data.get("status_name", ""),
                "read_at": data.get("read_at", ""),
                "isbn": item.get("EAN", ""),
                "publisher": item.get("publisher", ""),
            }

            if book["title"]:
                page_books.append(book)

        existing_ids = {b["booklog_id"] for b in all_books}

        new_books = [
            b for b in page_books
            if b["booklog_id"] not in existing_ids
        ]

        if not new_books:
            print("新しい本がないため終了します")
            break

        all_books.extend(new_books)
        page_number += 1

    browser.close()

unique_books = {}

for book in all_books:
    key = book["booklog_id"] or book["title"]
    unique_books[key] = book

books = list(unique_books.values())

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "booklog_id",
            "title",
            "author",
            "rating",
            "status",
            "read_at",
            "isbn",
            "publisher",
        ],
    )

    writer.writeheader()
    writer.writerows(books)

print()
print("==============================")
print(f"合計 {len(books)}冊を取得しました")
print(f"保存先: {OUTPUT.resolve()}")
print("==============================")

gmail_address = os.environ["GMAIL_ADDRESS"]
gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]

msg = EmailMessage()
msg["Subject"] = "Booklog latest CSV"
msg["From"] = gmail_address
msg["To"] = gmail_address
msg.set_content("最新のブクログCSVです。")

with open(OUTPUT, "rb") as f:
    file_data = f.read()
    msg.add_attachment(
        file_data,
        maintype="text",
        subtype="csv",
        filename=OUTPUT.name
    )

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(gmail_address, gmail_app_password)
    smtp.send_message(msg)

print("GmailへCSVを送信しました")
