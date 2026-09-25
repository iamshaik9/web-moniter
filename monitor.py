import os
import hashlib
import requests
from bs4 import BeautifulSoup

WEBSITE_URL = "https://httpbin.org/html"
TEST_MODE = os.environ.get("TEST_MODE", "false") == "true"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "previous_hash.txt"


def get_website_content():
    response = requests.get(
        WEBSITE_URL,
        timeout=30,
        headers={
            "User-Agent": "WebsiteMonitor/1.0"
        }
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove things that normally don't matter
    for element in soup(["script", "style"]):
        element.decompose()

    text = soup.get_text(" ", strip=True)

    return text


def calculate_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()


def main():
    print(f"Checking: {WEBSITE_URL}")

    content = get_website_content()
    content = get_website_content()
    
    if TEST_MODE:
        content += os.environ.get("TEST_VALUE", "")
    
    current_hash = calculate_hash(content)

    print(f"Current hash: {current_hash}")

    # First run
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as file:
            file.write(current_hash)

        print("First run. Baseline saved.")
        return

    # Read previous hash
    with open(STATE_FILE, "r") as file:
        previous_hash = file.read().strip()

    if current_hash == previous_hash:
        print("No change detected.")
        return

    print("🚨 CHANGE DETECTED!")

    send_telegram(
        f"🚨 WEBSITE CHANGE DETECTED!\n\n"
        f"Website: {WEBSITE_URL}\n\n"
        f"The webpage content has changed.\n\n"
        f"🔗 {WEBSITE_URL}"
    )

    with open(STATE_FILE, "w") as file:
        file.write(current_hash)

    print("Telegram notification sent.")


if __name__ == "__main__":
    main()
