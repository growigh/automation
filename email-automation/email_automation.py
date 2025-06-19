#!/usr/bin/env python3
"""
Email Automation Script - Sends emails immediately via GoDaddy
Usage: python email_automation.py
"""

import os
import gspread
import smtplib
import imaplib
import time
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_validator import validate_email
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def save_to_sent_folder(email_address, email_password, msg_string):
    """Save sent email to the Sent folder using IMAP"""
    try:
        print("   📁 Saving to Sent folder...")
        # Connect to IMAP server
        imap_server = imaplib.IMAP4_SSL('imap.secureserver.net', 993)
        imap_server.login(email_address, email_password)
        
        # Select the Sent folder (try different common names)
        sent_folders = ['Sent', 'Sent Items', 'INBOX.Sent']
        sent_folder = None
        
        for folder in sent_folders:
            try:
                imap_server.select(folder)
                sent_folder = folder
                break
            except:
                continue
        
        if sent_folder:
            # Append the message to the Sent folder
            imap_server.append(sent_folder, '\\Seen', None, msg_string.encode('utf-8'))
            print(f"   ✅ Email saved to {sent_folder} folder")
        else:
            print("   ⚠️  Could not find Sent folder")
            
        imap_server.close()
        imap_server.logout()
        
    except Exception as e:
        print(f"   ⚠️  Could not save to Sent folder: {e}")


def send_emails():
    """Main function - reads sheets and sends emails"""

    # Configuration from .env
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    sheets_urls = os.getenv("GOOGLE_SHEETS_URLS", "").split(",")
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.godaddy.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    print(f"🚀 Starting email automation at {datetime.now()}")

    # Connect to Google Sheets
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(
            service_account_file, scopes=scope
        )
        gc = gspread.authorize(credentials)
        print("✅ Connected to Google Sheets")
    except Exception as e:
        print(f"❌ Failed to connect to Google Sheets: {e}")
        return

    emails_sent = 0
    total_rows = 0
    approved_rows = 0
    not_approved_rows = 0

    # Process each sheet
    for sheet_url in sheets_urls:
        if not sheet_url.strip():
            continue

        try:
            spreadsheet = gc.open_by_url(sheet_url.strip())
            print(f"📊 Processing: {spreadsheet.title}")

            # Process each worksheet
            for worksheet in spreadsheet.worksheets():
                records = worksheet.get_all_records()

                for i, record in enumerate(records, 1):
                    total_rows += 1
                    # Get required fields
                    status = str(record.get("Status", "")).strip()
                    is_sent = str(record.get("isSent?", "")).strip().lower()
                    email = str(record.get("Email", "")).strip()
                    subject = str(record.get("Subject", "")).strip()
                    body = str(record.get("Body", "")).strip()
                    name = str(record.get("Name", "")).strip()

                    # Track status counts
                    if status.lower() == "approved":
                        approved_rows += 1
                    else:
                        not_approved_rows += 1

                    # Check if should send email
                    if (
                        status.lower() == "approved"
                        and is_sent not in ["true", "yes", "1"]
                        and email
                        and subject
                        and body
                    ):

                        print(f"📧 Sending email to: {email}")
                        print(f"   Using SMTP: {smtp_server}:{smtp_port}")

                        # Personalize body
                        if name and "[Name]" in body:
                            body = body.replace("[Name]", name)

                        # Add email signature
                        signature = """
                        Best Regards,
                        Nikhil Nigam
                        IIT Kanpur
                        Growigh.com"""

                        html_signature = """<br><br>
Best Regards,<br>
Nikhil Nigam<br>
IIT Kanpur<br>
<a href="https://Growigh.com">Growigh.com</a>"""

                        # Add signature to body
                        body_with_signature = body + signature
                        html_body = body.replace("\n", "<br>") + html_signature

                        # Send email
                        try:
                            print("   📦 Creating message...")
                            # Create message with both text and HTML parts
                            msg = MIMEMultipart("alternative")
                            msg["From"] = f"Nikhil Nigam <{email_address}>"
                            msg["To"] = email
                            msg["Subject"] = subject

                            # Create text and HTML parts
                            text_part = MIMEText(body_with_signature, "plain")
                            html_part = MIMEText(html_body, "html")

                            # Attach parts
                            msg.attach(text_part)
                            msg.attach(html_part)

                            print("   🔌 Connecting to SMTP server...")
                            # Send via SMTP (handle both SSL and STARTTLS)
                            if smtp_port == 465:
                                # Use SSL for port 465
                                server = smtplib.SMTP_SSL(
                                    smtp_server, smtp_port, timeout=30
                                )
                                print("   🔒 Using SSL connection")
                            else:
                                # Use STARTTLS for port 587
                                server = smtplib.SMTP(
                                    smtp_server, smtp_port, timeout=30
                                )
                                print("   🔐 Starting TLS...")
                                server.starttls()

                            print("   🔑 Logging in...")
                            server.login(email_address, email_password)
                            print("   📤 Sending message...")
                            
                            # Get the message string for both sending and saving
                            msg_string = msg.as_string()
                            server.sendmail(email_address, email, msg_string)
                            server.quit()

                            print(f"✅ Email sent to {email}")
                            
                            # Save to Sent folder
                            save_to_sent_folder(email_address, email_password, msg_string)
                            
                            emails_sent += 1

                            # Update isSent? column
                            headers = worksheet.row_values(1)
                            for j, header in enumerate(headers, 1):
                                if header.strip().lower() in [
                                    "issent?",
                                    "is sent?",
                                    "issent",
                                ]:
                                    # +1 for header row
                                    worksheet.update_cell(i + 1, j, "True")
                                    break

                            time.sleep(2)  # Rate limiting

                        except Exception as e:
                            print(f"❌ Failed to send email to {email}: {e}")

                    elif status.lower() == "approved":
                        # Debug why email wasn't sent
                        missing = []
                        if not email:
                            missing.append("Email")
                        if not subject:
                            missing.append("Subject")
                        if not body:
                            missing.append("Body")
                        if is_sent in ["true", "yes", "1"]:
                            missing.append("Already Sent")

                        if missing:
                            print(f"⏭️  Skipping row {i}: Missing {', '.join(missing)}")

        except Exception as e:
            print(f"❌ Error processing sheet {sheet_url}: {e}")

    # Enhanced completion message
    print(f"\n📊 Summary:")
    print(f"   Total rows processed: {total_rows}")
    print(f"   Approved rows: {approved_rows}")
    print(f"   Not approved rows: {not_approved_rows}")
    print(f"   Emails sent: {emails_sent}")

    if emails_sent == 0:
        if not_approved_rows > 0 and approved_rows == 0:
            print(f"⚠️  No emails sent - No approved emails found!")
            print(
                f"   Change the 'Status' column to 'Approved' for rows you want to send."
            )
        elif approved_rows > 0:
            print(
                f"⚠️  No emails sent - All approved emails may be missing required fields or already sent."
            )
        else:
            print(f"⚠️  No emails sent - No data found in sheets.")
    else:
        print(f"🎉 Successfully sent {emails_sent} emails!")


def main():
    """Run the email automation immediately"""
    send_emails()


if __name__ == "__main__":
    main()
