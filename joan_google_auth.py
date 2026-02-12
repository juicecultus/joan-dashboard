#!/usr/bin/env python3
"""One-time Google OAuth2 setup for Joan Dashboard.

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create a project (or select existing)
  3. Enable "Google Calendar API" and "Google Tasks API"
  4. Go to Credentials -> Create Credentials -> OAuth client ID
  5. Application type: Desktop app
  6. Download the JSON and save as credentials.json in this directory

Usage:
    python joan_google_auth.py

This will open a browser for you to log in with your Google account
and save the token to token.json for the dashboard to use.
"""

import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
]

CREDS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")


def main():
    if not os.path.exists(CREDS_FILE):
        print(f"ERROR: {CREDS_FILE} not found.")
        print()
        print("To create it:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create/select a project")
        print("  3. Enable 'Google Calendar API' and 'Google Tasks API'")
        print("  4. Go to APIs & Services -> Credentials")
        print("  5. Create Credentials -> OAuth client ID -> Desktop app")
        print("  6. Download JSON -> save as credentials.json here")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Opening browser for Google login...")
            print("Log in with your Google account...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")
    else:
        print(f"Token already valid: {TOKEN_FILE}")

    print("Done! The dashboard can now access Calendar and Tasks.")


if __name__ == "__main__":
    main()
