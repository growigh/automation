from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time
import getpass
import os
import re
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Google Sheets setup
def setup_google_sheets():
    """Setup Google Sheets authentication"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    try:

        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "key.json")

        creds = Credentials.from_service_account_file(
            service_account_file, scopes=scopes
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error setting up Google Sheets: {e}")
        print(
            f"Make sure you have {service_account_file} file in your project directory"
        )
        return None


# Initialize LLM with API key from environment
def initialize_llm():
    """Initialize the language model with API key from environment"""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        api_key = getpass.getpass("Enter your Google AI API key: ")
        os.environ["GOOGLE_API_KEY"] = api_key

    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-8b-001",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        google_api_key=api_key,
    )


# Initialize the LLM
llm = initialize_llm()


def load_email_prompt():
    """Load the email prompt from prompt.txt"""
    try:
        with open("prompt.txt", "r") as f:
            return f.read()
    except Exception as e:
        print(f"Error loading prompt: {e}")
        return ""


def extract_domain_from_url(url):
    """Extract domain from URL"""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        domain = urlparse(url).netloc
        return domain.replace("www.", "") if domain else url
    except:
        return url


def extract_sheet_id_from_url(url):
    """Extract Google Sheets ID from URL"""
    try:
        # Handle different Google Sheets URL formats
        if "/spreadsheets/d/" in url:
            # Extract ID from URL like: https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=0
            start = url.find("/spreadsheets/d/") + len("/spreadsheets/d/")
            end = url.find("/", start)
            if end == -1:
                end = len(url)
            sheet_id = url[start:end]
            return sheet_id
        else:
            # Assume it's already a sheet ID
            return url
    except Exception as e:
        print(f"Error extracting sheet ID from URL: {e}")
        return url


def get_google_sheets_urls_from_env():
    """Get Google Sheets URLs from environment file"""
    urls_string = os.getenv("GOOGLE_SHEETS_URLS", "")
    if not urls_string:
        return []

    # Split by comma and clean up URLs
    urls = [url.strip().split("#")[0] for url in urls_string.split(",") if url.strip()]
    return urls


def generate_email(row_data, prompt_template):
    """Generate email for a single row of data"""
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
        domain = extract_domain_from_url(website)

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
            [("system", prompt_template), ("user", user_prompt)]
        )

        # Generate the email
        chain = chat_prompt | llm | StrOutputParser()
        result = chain.invoke({})

        return result

    except Exception as e:
        print(f"Error generating email for {name}: {e}")
        return f"Error generating email: {str(e)}"


def process_google_sheet(sheet_id, sheet_name=None):
    """Process a Google Sheet and generate emails for approved rows"""

    # Setup Google Sheets client
    client = setup_google_sheets()
    if not client:
        return

    # Load email prompt
    email_prompt = load_email_prompt()
    if not email_prompt:
        print("Could not load email prompt")
        return

    try:
        # Open the spreadsheet
        spreadsheet = client.open_by_key(sheet_id)

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
            print(f"Available columns: {list(column_map.keys())}")

            # Get all records
            records = worksheet.get_all_records()

            if not records:
                print(f"No data found in worksheet {worksheet.title}")
                continue

            # Process each row
            processed_count = 0
            for idx, row in enumerate(
                records, start=2
            ):  # Start from row 2 (header is row 1)
                # Check if "Read For Body?" or "Ready For Body?" column is "Approved"
                read_for_body = (
                    row.get("Read For Body?", row.get("Ready For Body?", ""))
                    .strip()
                    .lower()
                )
                status = row.get("Status", "").strip().lower()

                if read_for_body == "approved" and status != "generated":
                    name = row.get("Name", "Unknown")
                    print(f"📧 Processing row {idx}: {name}")

                    # Generate email
                    email_content = generate_email(row, email_prompt)

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
                        status_col = column_map.get("Status")

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

                        # Update Subject column
                        if subject and subject_col:
                            subject_col_letter = col_num_to_letter(subject_col)
                            worksheet.update(f"{subject_col_letter}{idx}", subject)
                            print(f"  ✅ Updated subject: {subject[:50]}...")

                        # Update Status to "Generated"
                        if status_col:
                            status_col_letter = col_num_to_letter(status_col)
                            worksheet.update(f"{status_col_letter}{idx}", "Generated")
                            print(f"  ✅ Status updated to 'Generated'")

                        processed_count += 1

                    except Exception as e:
                        print(f"❌ Error updating row {idx}: {e}")

                    # Add delay to avoid API rate limits
                    time.sleep(3)

                elif status == "generated":
                    print(
                        f"⏭️  Row {idx} already processed: {row.get('Name', 'Unknown')}"
                    )

                elif read_for_body != "approved":
                    # Silently skip non-approved rows
                    pass

            print(
                f"\n📊 Completed worksheet '{worksheet.title}': {processed_count} emails generated"
            )

    except Exception as e:
        print(f"Error processing spreadsheet: {e}")
        print(
            f"Make sure the Google Sheets ID is correct and you have proper access permissions"
        )


def main():
    """Main function to run the email generation process"""

    print("🚀 Email Writer - Automated Outreach Email Generation")
    print("=" * 60)

    # Check for URLs in .env file first
    env_urls = get_google_sheets_urls_from_env()

    if env_urls:
        print(f"📋 Found {len(env_urls)} Google Sheets URL(s) in .env file:")
        for i, url in enumerate(env_urls, 1):
            sheet_id = extract_sheet_id_from_url(url)
            print(f"   {i}. {url} (ID: {sheet_id})")

        use_env = input("\n🤔 Use URLs from .env file? (y/n): ").strip().lower()

        if use_env == "y":
            # Process each URL from .env file
            for i, url in enumerate(env_urls, 1):
                sheet_id = extract_sheet_id_from_url(url)
                print(f"\n🔄 Processing sheet {i}/{len(env_urls)}: {sheet_id}")

                # Optional: Get specific sheet name
                sheet_name = input(
                    f"📝 Enter specific sheet name for sheet {i} (or press Enter for all sheets): "
                ).strip()
                sheet_name = sheet_name if sheet_name else None

                print(f"🔄 Starting email generation process for sheet {i}...")
                start_time = time.time()
                process_google_sheet(sheet_id, sheet_name)
                end_time = time.time()

                print(f"✅ Sheet {i} completed in {end_time - start_time:.1f} seconds")

            print(f"\n🎉 All sheets processed successfully!")
            return

    # Manual input if no .env URLs or user chooses manual input
    print("📋 Manual Google Sheets ID Entry")

    # Get Google Sheets ID or URL from user
    sheet_input = input("📋 Enter Google Sheets ID or URL: ").strip()

    if not sheet_input:
        print("❌ Please provide a valid Google Sheets ID or URL")
        return

    # Extract sheet ID if URL is provided
    sheet_id = extract_sheet_id_from_url(sheet_input)

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
    start_time = time.time()
    process_google_sheet(sheet_id, sheet_name)
    end_time = time.time()

    print(f"\n✅ Email generation completed!")
    print(f"⏱️  Total time: {end_time - start_time:.1f} seconds")
    print(f"\n💡 Next steps:")
    print(f"   1. Review generated emails in your Google Sheet")
    print(f"   2. Set 'SENT?' column to track sent emails")
    print(f"   3. Use the generated content for your outreach campaign")


if __name__ == "__main__":
    main()
