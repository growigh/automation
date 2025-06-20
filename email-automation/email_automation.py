#!/usr/bin/env python3
"""
Email Automation Script - Send emails and generate email bodies
"""

import os
import warnings
# Suppress urllib3 OpenSSL warning on macOS
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

import gspread
import smtplib
import imaplib
import time
import logging
import re
import getpass
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_validator import validate_email
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from urllib.parse import urlparse

# Import AI components for email generation
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_google_genai import ChatGoogleGenerativeAI
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# Load environment variables from the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(script_dir, '.env')
load_dotenv(env_file)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


class EmailAutomation:
    def __init__(self):
        self.gc = None
        self.llm = None
        self.email_prompt = None
        self.setup_google_sheets()
        
    def setup_google_sheets(self):
        """Setup Google Sheets authentication"""
        try:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "key.json")
            
            # If the file doesn't exist in current directory, try the script's directory
            if not os.path.exists(service_account_file):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                service_account_file = os.path.join(script_dir, service_account_file)
                
            credentials = Credentials.from_service_account_file(
                service_account_file, scopes=scope
            )
            self.gc = gspread.authorize(credentials)
            print("✅ Connected to Google Sheets")
        except Exception as e:
            print(f"❌ Failed to connect to Google Sheets: {e}")
            print(f"Make sure you have key.json file in your email-automation directory")
            print(f"Looking for: {service_account_file}")
    
    def initialize_llm(self):
        """Initialize the language model for email generation"""
        if not AI_AVAILABLE:
            print("❌ AI dependencies not installed. Please install langchain packages.")
            return False
            
        try:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            
            if not api_key:
                api_key = getpass.getpass("Enter your Google AI API key: ")
                os.environ["GOOGLE_API_KEY"] = api_key
            
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash-8b-001",
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                google_api_key=api_key,
            )
            print("✅ AI model initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AI model: {e}")
            return False
    
    def load_email_prompt(self):
        """Load the email prompt template"""
        default_prompt = """Act as an outreach copywriter for a web design and digital growth agency.
My brand communication is Formal and Little Witty(Little funny, humorous). 

I'll provide you with details about a specific company, including the recipient's name, their role, company website, observed website issues (performance, design, UX, etc.), and relevant context.

Write a concise, respectful outreach email using commonly used english words within 100 words

Based on the provided details:

Include an engaging yet clear subject line using the format: "[theirwebsite.com] has a hidden problem." Don't sound like an ordinary salesperson.

Email Body:
Begins with a brief acknowledgment of the company's strengths or services.

Clearly highlights 2–3 specific website issues I've mentioned, such as slow performance, design issues, poor readability, missing interactive elements, etc.

Suggests clear and direct benefits the company can achieve by addressing these issues, like building credibility, improving user engagement, and accurately reflecting their service quality.

Offers to discuss solutions or share specific suggestions in a short call (15–30 minutes), presenting it as an opportunity rather than a sales push.

Includes the calendar scheduling link explicitly (without hyperlink).
https://calendar.app.google/tZEYH6Uyp5nWnpqVA

Use a professional and engaging tone. Don't add signature in the end of mail."""

        try:
            # Try to load from prompt.txt file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_files = [
                os.path.join(script_dir, "prompt.txt"),
                os.path.join(script_dir, "..", "email-body", "prompt.txt"),
                "prompt.txt"  # Fallback to current directory
            ]
            for prompt_file in prompt_files:
                if os.path.exists(prompt_file):
                    with open(prompt_file, "r") as f:
                        self.email_prompt = f.read()
                        print(f"✅ Loaded email prompt from {prompt_file}")
                        return True
            
            # Use default prompt if file not found
            print("⚠️  Using default email prompt template")
            self.email_prompt = default_prompt
            return True
            
        except Exception as e:
            print(f"❌ Error loading prompt: {e}")
            self.email_prompt = default_prompt
            return True
    
    def extract_domain_from_url(self, url):
        """Extract domain from URL"""
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            domain = urlparse(url).netloc
            return domain.replace("www.", "") if domain else url
        except:
            return url
    
    def extract_sheet_id_from_url(self, url):
        """Extract Google Sheets ID from URL"""
        try:
            if "/spreadsheets/d/" in url:
                start = url.find("/spreadsheets/d/") + len("/spreadsheets/d/")
                end = url.find("/", start)
                if end == -1:
                    end = len(url)
                sheet_id = url[start:end]
                return sheet_id
            else:
                return url
        except Exception as e:
            print(f"Error extracting sheet ID from URL: {e}")
            return url
    
    def generate_email_content(self, row_data):
        """Generate email content for a single row of data"""
        if not self.llm or not self.email_prompt:
            return "Error: AI model not initialized"
            
        try:
            # Extract relevant information from the row
            name = row_data.get("Name", "")
            title = row_data.get("Title", "")
            company = row_data.get("Company", "")
            website = row_data.get("Website", "")
            issues = row_data.get("ISSUES", "")
            keywords = row_data.get("Keywords", "")

            # Skip if essential data is missing
            if not name or not company or not website:
                return "Error: Missing essential data (Name, Company, or Website)"

            # Extract domain for subject line
            domain = self.extract_domain_from_url(website)

            # Create the user prompt with the data
            user_prompt = f"""
            Generate an outreach email with the following details:
            
            Recipient Name: {name}
            Title: {title}
            Company: {company}
            Website: {website}
            Domain: {domain}
            Issues: {issues}
            Keywords/Services: {keywords}
            
            Follow the template format and guidelines provided in the system prompt.
            """

            # Create the complete prompt
            chat_prompt = ChatPromptTemplate(
                [("system", self.email_prompt), ("user", user_prompt)]
            )

            # Generate the email
            chain = chat_prompt | self.llm | StrOutputParser()
            result = chain.invoke({})

            return result

        except Exception as e:
            print(f"Error generating email for {name}: {e}")
            return f"Error generating email: {str(e)}"
    
    def save_to_sent_folder(self, email_address, email_password, msg_string):
        """Save sent email to the Sent folder using IMAP"""
        try:
            print("   📁 Saving to Sent folder...")
            # Get IMAP settings from environment
            imap_server_host = os.getenv("IMAP_SERVER", "imap.secureserver.net")
            imap_port = int(os.getenv("IMAP_PORT", 993))
            
            # Connect to IMAP server
            imap_server = imaplib.IMAP4_SSL(imap_server_host, imap_port)
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
    
    def send_emails(self):
        """Send emails from Google Sheets"""
        if not self.gc:
            print("❌ Google Sheets not connected")
            return
            
        # Configuration from .env
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        sheets_urls = os.getenv("GOOGLE_SHEETS_URLS", "").split(",")
        email_address = os.getenv("EMAIL_ADDRESS")
        email_password = os.getenv("EMAIL_PASSWORD")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.godaddy.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))

        if not email_address or not email_password:
            print("❌ Email credentials not found in .env file")
            print("   Please check your .env file contains:")
            print("   EMAIL_ADDRESS=your-email@domain.com")
            print("   EMAIL_PASSWORD=your-password")
            return

        print(f"🚀 Starting email automation at {datetime.now()}")
        print(f"📧 Using email: {email_address}")
        print(f"🔧 SMTP Server: {smtp_server}:{smtp_port}")
        print(f"🔑 Password: {'*' * len(email_password)}")

        emails_sent = 0
        total_rows = 0
        approved_rows = 0
        not_approved_rows = 0

        # Process each sheet
        for sheet_url in sheets_urls:
            if not sheet_url.strip():
                continue

            try:
                spreadsheet = self.gc.open_by_url(sheet_url.strip())
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
                                server = None
                                
                                # Try multiple SMTP configurations for GoDaddy
                                smtp_configs = [
                                    (smtp_server, smtp_port, "SSL" if smtp_port == 465 else "TLS"),
                                    ("smtpout.secureserver.net", 465, "SSL"),
                                    ("smtpout.secureserver.net", 587, "TLS"),
                                    ("smtpout.secureserver.net", 25, "TLS"),
                                    ("smtp.secureserver.net", 465, "SSL"),
                                    ("smtp.secureserver.net", 587, "TLS")
                                ]
                                
                                success = False
                                for server_host, port, connection_type in smtp_configs:
                                    try:
                                        print(f"   � Trying {server_host}:{port} ({connection_type})...")
                                        
                                        if connection_type == "SSL":
                                            server = smtplib.SMTP_SSL(server_host, port, timeout=30)
                                            print(f"   🔒 Using SSL connection to {server_host}:{port}")
                                        else:
                                            server = smtplib.SMTP(server_host, port, timeout=30)
                                            print(f"   🔐 Starting TLS connection to {server_host}:{port}...")
                                            server.starttls()
                                        
                                        print("   🔑 Logging in...")
                                        server.login(email_address, email_password)
                                        
                                        print("   📤 Sending message...")
                                        msg_string = msg.as_string()
                                        server.sendmail(email_address, email, msg_string)
                                        server.quit()
                                        
                                        print(f"   ✅ Successfully sent via {server_host}:{port}")
                                        success = True
                                        break
                                        
                                    except Exception as smtp_error:
                                        print(f"   ❌ Failed with {server_host}:{port} - {smtp_error}")
                                        if server:
                                            try:
                                                server.quit()
                                            except:
                                                pass
                                        continue
                                
                                if not success:
                                    raise Exception("All SMTP configurations failed")

                                print(f"✅ Email sent to {email}")
                                
                                # Save to Sent folder
                                self.save_to_sent_folder(email_address, email_password, msg_string)
                                
                                emails_sent += 1

                                # Update SENT? column
                                headers = worksheet.row_values(1)
                                for j, header in enumerate(headers, 1):
                                    if header.strip().lower() in [
                                        "sent?",
                                        "issent?",
                                        "is sent?",
                                        "issent",
                                        "sent"
                                    ]:
                                        # +1 for header row
                                        worksheet.update_cell(i + 1, j, "True")
                                        print(f"   📝 Updated {header} column to 'True'")
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
                print(f"   Change the 'Status' column to 'Approved' for rows you want to send.")
            elif approved_rows > 0:
                print(f"⚠️  No emails sent - All approved emails may be missing required fields or already sent.")
            else:
                print(f"⚠️  No emails sent - No data found in sheets.")
        else:
            print(f"🎉 Successfully sent {emails_sent} emails!")
    
    def generate_email_bodies(self):
        """Generate email bodies using AI"""
        if not AI_AVAILABLE:
            print("❌ AI dependencies not installed. Please install:")
            print("   pip install langchain-core langchain-google-genai")
            return
            
        if not self.initialize_llm():
            return
            
        if not self.load_email_prompt():
            return
            
        # Get Google Sheets URLs
        env_urls = os.getenv("GOOGLE_SHEETS_URLS", "").split(",")
        env_urls = [url.strip() for url in env_urls if url.strip()]
        
        if env_urls:
            print(f"📋 Found {len(env_urls)} Google Sheets URL(s) in .env file:")
            for i, url in enumerate(env_urls, 1):
                sheet_id = self.extract_sheet_id_from_url(url)
                print(f"   {i}. {url} (ID: {sheet_id})")

            use_env = input("\n🤔 Use URLs from .env file? (y/n): ").strip().lower()

            if use_env == "y":
                # Process each URL from .env file
                all_successful = True
                for i, url in enumerate(env_urls, 1):
                    sheet_id = self.extract_sheet_id_from_url(url)
                    print(f"\n🔄 Processing sheet {i}/{len(env_urls)}: {sheet_id}")

                    # Optional: Get specific sheet name
                    sheet_name = input(
                        f"📝 Enter specific sheet name for sheet {i} (or press Enter for all sheets): "
                    ).strip()
                    sheet_name = sheet_name if sheet_name else None

                    print(f"🔄 Starting email generation process for sheet {i}...")
                    success = self.process_google_sheet_for_generation(sheet_id, sheet_name)
                    
                    if not success:
                        all_successful = False
                        print(f"❌ Processing failed for sheet {i}")

                if all_successful:
                    print(f"\n🎉 All sheets processed successfully!")
                else:
                    print(f"\n❌ Some sheets failed to process. Please check the errors above.")
                return

        # Manual input if no .env URLs or user chooses manual input
        print("📋 Manual Google Sheets ID Entry")

        # Get Google Sheets ID or URL from user
        sheet_input = input("📋 Enter Google Sheets ID or URL: ").strip()

        if not sheet_input:
            print("❌ Please provide a valid Google Sheets ID or URL")
            return

        # Extract sheet ID if URL is provided
        sheet_id = self.extract_sheet_id_from_url(sheet_input)

        # Optional: Get specific sheet name
        sheet_name = input(
            "📝 Enter specific sheet name (or press Enter for all sheets): "
        ).strip()
        sheet_name = sheet_name if sheet_name else None

        print(f"\n🔄 Starting email generation process...")
        print(f"📊 Sheet ID: {sheet_id}")
        if sheet_name:
            print(f"📋 Target sheet: {sheet_name}")
        else:
            print(f"📋 Processing all sheets")

        # Process the sheet
        success = self.process_google_sheet_for_generation(sheet_id, sheet_name)

        if success:
            print(f"\n✅ Email generation completed!")
            print(f"\n💡 Next steps:")
            print(f"   1. Review generated emails in your Google Sheet")
            print(f"   2. Set 'Status' column to 'Approved' for emails you want to send")
            print(f"   3. Use option 1 to send the generated emails")
        else:
            print(f"\n❌ Email generation failed! Please check the errors above.")
    
    def process_google_sheet_for_generation(self, sheet_id, sheet_name=None):
        """Process a Google Sheet and generate emails for approved rows"""
        if not self.gc:
            print("❌ Google Sheets not connected")
            return False

        try:
            # Open the spreadsheet
            spreadsheet = self.gc.open_by_key(sheet_id)

            # Get all worksheets if no specific sheet name provided
            worksheets = (
                [spreadsheet.worksheet(sheet_name)]
                if sheet_name
                else spreadsheet.worksheets()
            )

            for worksheet in worksheets:
                print(f"\nProcessing worksheet: {worksheet.title}")

                # Get header row to map column names to indices
                header_row = worksheet.row_values(1)

                # Create column mapping
                column_map = {}
                for i, header in enumerate(header_row, start=1):
                    column_map[header] = i

                # Print available columns for debugging
                # print(f"Available columns: {list(column_map.keys())}")
                
                # Check for required columns
                required_columns = ["Read For Body?", "Name", "Company", "Website", "Body", "Subject"]
                missing_columns = []
                
                for col in required_columns:
                    if col not in column_map:
                        missing_columns.append(col)
                
                if missing_columns:
                    error_msg = f"❌ ERROR: Missing required columns in worksheet '{worksheet.title}': {', '.join(missing_columns)}"
                    print(error_msg)
                    print(f"   Available columns: {list(column_map.keys())}")
                    print(f"   Required columns: {required_columns}")
                    print("   Please add the missing columns to your spreadsheet and try again.")
                    return False

                # Get all records
                records = worksheet.get_all_records()

                if not records:
                    print(f"No data found in worksheet {worksheet.title}")
                    continue

                # Process each row
                processed_count = 0
                for idx, row in enumerate(records, start=2):  # Start from row 2 (header is row 1)
                    # Check if "Read For Body?" column is "Approved"
                    read_for_body = row.get("Read For Body?", "").strip().lower()

                    if read_for_body == "approved":
                        name = row.get("Name", "Unknown")
                        print(f"📧 Processing row {idx}: {name}")

                        # Generate email
                        email_content = self.generate_email_content(row)

                        if email_content.startswith("Error:"):
                            print(f"❌ {email_content}")
                            continue

                        # Extract subject and body from generated email
                        subject_match = re.search(
                            r"Subject:\s*(.+?)(?:\n|$)", email_content, re.IGNORECASE
                        )
                        subject = subject_match.group(1).strip() if subject_match else ""

                        # Remove subject line from body
                        body = re.sub(
                            r"Subject:\s*.+?(?:\n|$)",
                            "",
                            email_content,
                            flags=re.IGNORECASE,
                        ).strip()

                        # Update the row with generated content
                        try:
                            # Find column indices dynamically
                            body_col = column_map.get("Body")
                            subject_col = column_map.get("Subject")
                            
                            # Check if required columns for updates exist
                            if not body_col:
                                print(f"❌ ERROR: 'Body' column not found in worksheet '{worksheet.title}'")
                                print("   Cannot update email body. Please add a 'Body' column to your spreadsheet.")
                                break
                            
                            if not subject_col:
                                print(f"❌ ERROR: 'Subject' column not found in worksheet '{worksheet.title}'")
                                print("   Cannot update email subject. Please add a 'Subject' column to your spreadsheet.")
                                break

                            # Convert column numbers to letters
                            def col_num_to_letter(col_num):
                                result = ""
                                while col_num > 0:
                                    col_num -= 1
                                    result = chr(col_num % 26 + ord("A")) + result
                                    col_num //= 26
                                return result

                            # Update Body column
                            if body and body_col:
                                body_col_letter = col_num_to_letter(body_col)
                                worksheet.update(f"{body_col_letter}{idx}", body)
                                print(f"  ✅ Updated body ({len(body)} characters)")
                            else:
                                print(f"  ⚠️  Warning: No body content generated for row {idx}")

                            # Update Subject column
                            if subject and subject_col:
                                subject_col_letter = col_num_to_letter(subject_col)
                                worksheet.update(f"{subject_col_letter}{idx}", subject)
                                print(f"  ✅ Updated subject: {subject[:50]}...")
                            else:
                                print(f"  ⚠️  Warning: No subject content generated for row {idx}")

                            processed_count += 1

                        except Exception as e:
                            print(f"❌ Error updating row {idx}: {e}")

                        # Add delay to avoid API rate limits
                        time.sleep(3)

                print(f"\n📊 Completed worksheet '{worksheet.title}': {processed_count} emails generated")
            
            return True

        except Exception as e:
            print(f"Error processing spreadsheet: {e}")
            print(f"Make sure the Google Sheets ID is correct and you have proper access permissions")
            return False

    def show_menu(self):
        """Display the main menu"""
        print("\n" + "="*60)
        print("🚀 Email Automation Suite")
        print("="*60)
        print("1. 📧 Send Emails (from Google Sheets)")
        print("2. ✍️  Generate Email Bodies (using AI)")
        print("3. 🚪 Exit")
        print("="*60)
        
    def run(self):
        """Main function to run the email automation suite"""
        print("🎯 Welcome to Email Automation Suite!")
        
        while True:
            self.show_menu()
            choice = input("👉 Enter your choice (1-3): ").strip()
            
            if choice == "1":
                print("\n📧 Starting Email Sending Process...")
                self.send_emails()
                
            elif choice == "2":
                print("\n✍️  Starting Email Body Generation Process...")
                self.generate_email_bodies()
                
            elif choice == "3":
                print("\n👋 Goodbye! Thanks for using Email Automation Suite!")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
            
            input("\n📝 Press Enter to continue...")


def main():
    """Entry point of the application"""
    automation = EmailAutomation()
    automation.run()


if __name__ == "__main__":
    main()
