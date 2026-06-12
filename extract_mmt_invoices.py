import os
import base64
import re
import pickle
import time
from datetime import datetime, date
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def authenticate_gmail(token_path: str = "token.pickle", credentials_path: str = "cred.json") -> Credentials:
    creds = None
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)
            
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            # This single line handles opening the browser, catching the localhost redirect, and getting the token
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)
            
    return creds

def search_messages(service, query: str, max_results: int = 200):
    messages = []
    page_token = None
    while len(messages) < max_results:
        result = service.users().messages().list(
            userId="me", q=query, pageToken=page_token, maxResults=min(100, max_results - len(messages))
        ).execute()
        messages.extend(result.get("messages", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return messages


def get_message_details(service, msg_id: str):
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()


def get_attachment(service, user_id: str, msg_id: str, attachment_id: str) -> Optional[bytes]:
    try:
        att = service.users().messages().attachments().get(
            userId=user_id, messageId=msg_id, id=attachment_id
        ).execute()
        file_data = base64.urlsafe_b64decode(att["data"])
        return file_data
    except HttpError as e:
        print(f"  Failed to download attachment: {e}")
        return None


def extract_pdf_attachments(service, msg, download_dir: str):
    msg_id = msg["id"]
    payload = msg["payload"]
    attachments = []

    def walk_parts(parts):
        for part in parts:
            if part.get("filename"):
                attachments.append(part)
            if part.get("parts"):
                walk_parts(part["parts"])

    if payload.get("parts"):
        walk_parts(payload["parts"])
    elif payload.get("filename"):
        attachments.append(payload)

    saved = []
    for part in attachments:
        filename = part["filename"]
        if not filename.lower().endswith(".pdf"):
            continue
        att_id = part["body"].get("attachmentId")
        if not att_id:
            continue
        data = get_attachment(service, "me", msg_id, att_id)
        if data is None:
            continue
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)
        filepath = os.path.join(download_dir, safe_name)
        if os.path.exists(filepath):
            base, ext = os.path.splitext(safe_name)
            filepath = os.path.join(download_dir, f"{base}_{msg_id[:7]}{ext}")
        with open(filepath, "wb") as f:
            f.write(data)
        saved.append(filepath)
    return saved


def extract_mmt_invoices(
    output_dir: str = "./mmt_invoices",
    start_year: int = 2024,
    end_year: int = 2026,
    credentials_path: str = "cred.json",
    token_path: str = "token.pickle",
    max_emails: int = 200,
):
    os.makedirs(output_dir, exist_ok=True)

    creds = authenticate_gmail(token_path, credentials_path)
    service = build("gmail", "v1", credentials=creds)

    query = (
        "(from:makemytrip OR from:confirm@makemytrip OR from:booking@makemytrip "
        "OR from:noreply@makemytrip OR from:info@makemytrip OR from:eticket@makemytrip "
        "OR from:tripit@makemytrip OR subject:MakeMyTrip OR subject:makemytrip) "
        f"after:{start_year}/1/1 before:{end_year + 1}/1/1 "
        "has:attachment"
    )

    print(f"Searching Gmail with query: {query}")
    messages = search_messages(service, query, max_results=max_emails)
    print(f"Found {len(messages)} matching emails")

    total_pdfs = 0
    for i, msg in enumerate(messages, 1):
        print(f"[{i}/{len(messages)}] Processing message {msg['id']}...")
        details = get_message_details(service, msg["id"])
        saved = extract_pdf_attachments(service, details, output_dir)
        if saved:
            for f in saved:
                print(f"  Saved: {f}")
            total_pdfs += len(saved)

    print(f"\nDone! Extracted {total_pdfs} PDF(s) to {output_dir}/")
    return total_pdfs


if __name__ == "__main__":
    extract_mmt_invoices()
