import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def generate_calendar_token():
    client_id = os.getenv("CALENDAR_CLIENT_ID")
    client_secret = os.getenv("CALENDAR_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("CALENDAR_CLIENT_ID or CALENDAR_CLIENT_SECRET is missing from .env")
        return

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        SCOPES,
    )

    credentials = flow.run_local_server(port=0)
    print("\nCopy this refresh token into your .env:\n")
    print(f"CALENDAR_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    generate_calendar_token()
