import os
import json
import requests
from datetime import datetime, timezone, timedelta

# =========================
# CONFIG
# =========================

ATTENDANCE_URL = "https://ngit-api.teleuniv.in/sanjaya/getAttendance"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ACCESS_TOKEN = os.environ["NETRA_ACCESS_TOKEN"]

STATE_FILE = "attendance_state.json"

# India timezone
IST = timezone(timedelta(hours=5, minutes=30))


# =========================
# TELEGRAM
# =========================

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

    print("Telegram notification sent.")


# =========================
# GET ACCESS TOKEN
# =========================

def get_access_token():
    print("Using temporary GitHub access token...")

    if not ACCESS_TOKEN:
        raise RuntimeError(
            "NETRA_ACCESS_TOKEN secret is missing."
        )

    print("Access token loaded successfully.")

    return ACCESS_TOKEN


# =========================
# GET ATTENDANCE
# =========================

def get_attendance(access_token):
    print("Fetching attendance...")

    response = requests.get(
        ATTENDANCE_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        timeout=30
    )

    print("Attendance status:", response.status_code)

    response.raise_for_status()

    data = response.json()

    if data.get("Error"):
        raise RuntimeError(
            f"Attendance API error: "
            f"{data.get('message', 'Unknown error')}"
        )

    return data


# =========================
# FIND TODAY'S ATTENDANCE
# =========================

def get_today_periods(data):
    today = datetime.now(IST).strftime("%Y-%m-%d")

    print("Today's date:", today)

    payload = data.get("payload", {})
    attendance_details = payload.get("attendanceDetails", [])

    print(
        "Attendance detail entries:",
        len(attendance_details)
    )

    available_dates = [
        day.get("date")
        for day in attendance_details
        if day.get("date")
    ]

    print("Dates returned by Netra:", available_dates)

    # Netra identifies today's entry as "Today"
    # instead of using the actual YYYY-MM-DD date.
    for day in attendance_details:

        day_date = day.get("date")

        if day_date == today or day_date == "Today":

            periods = day.get("periods", [])

            print(
                f"Found {len(periods)} periods for today."
            )

            return periods

    print(
        f"Today's date {today} was not found in the API response."
    )

    return []

# =========================
# STATE MANAGEMENT
# =========================

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r") as file:
            return json.load(file)

    except Exception:
        print(
            "State file could not be read. "
            "Starting fresh."
        )

        return {}


def save_state(state):
    with open(STATE_FILE, "w") as file:
        json.dump(
            state,
            file,
            indent=2,
            sort_keys=True
        )


# =========================
# STATUS NAMES
# =========================

STATUS_NAMES = {
    0: "Absent",
    1: "Present",
    2: "Not marked"
}


# =========================
# CHECK CHANGES
# =========================

def check_attendance_changes(
    periods,
    previous_state
):

    today = datetime.now(IST).strftime("%Y-%m-%d")

    current_state = previous_state.copy()

    notifications = []

    for period in periods:

        period_no = str(period.get("period_no"))
        status = period.get("status")

        if status not in (0, 1, 2):
            print(
                f"Unknown status for period "
                f"{period_no}: {status}"
            )
            continue

        key = f"{today}_period_{period_no}"

        previous_status = previous_state.get(key)

        print(
            f"Period {period_no}: "
            f"previous={previous_status}, "
            f"current={status}"
        )

        # First time seeing this period.
        # Save it as baseline and DO NOT notify.
        if previous_status is None:
            current_state[key] = status
            continue

        # ONLY notify for:
        #
        # 2 -> 1 = Present
        # 2 -> 0 = Absent

        if previous_status == 2 and status == 1:

            notifications.append(
                f"🟢 Attendance Updated\n\n"
                f"Date: {today}\n"
                f"Period: {period_no}\n"
                f"Status: Present"
            )

        elif previous_status == 2 and status == 0:

            notifications.append(
                f"🔴 Attendance Updated\n\n"
                f"Date: {today}\n"
                f"Period: {period_no}\n"
                f"Status: Absent"
            )

        else:

            print(
                f"No notification for "
                f"{previous_status} → {status}"
            )

        current_state[key] = status

    return current_state, notifications


# =========================
# MAIN
# =========================

def main():

    print("=" * 50)
    print("Tracky Netra Attendance Monitor")
    print("=" * 50)

    # 1. Get temporary access token
    access_token = get_access_token()

    # 2. Get attendance
    attendance_data = get_attendance(access_token)

    # 3. Get today's periods
    periods = get_today_periods(attendance_data)

    # If today's attendance isn't available,
    # don't modify the state.
    if not periods:
        print("No attendance data for today.")
        return

    # 4. Load previous state
    previous_state = load_state()

    # 5. Compare
    new_state, notifications = check_attendance_changes(
        periods,
        previous_state
    )

    # 6. Save state
    save_state(new_state)

    # 7. Send notifications
    for message in notifications:
        send_telegram(message)

    if not notifications:
        print("No relevant attendance changes.")

    print("=" * 50)
    print("Check completed.")
    print("=" * 50)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
