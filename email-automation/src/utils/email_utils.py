#!/usr/bin/env python3
"""
Utility functions for email automation
"""

import re
from urllib.parse import urlparse


class EmailUtils:
    """Utility functions for email operations"""
    
    @staticmethod
    def extract_domain_from_url(url: str) -> str:
        """Extract domain from URL"""
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            domain = urlparse(url).netloc
            return domain.replace("www.", "") if domain else url
        except:
            return url
    
    @staticmethod
    def extract_sheet_id_from_url(url: str) -> str:
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
    
    @staticmethod
    def convert_text_to_html(text: str) -> str:
        """Convert text with markdown-style formatting to HTML"""
        if not text:
            return ""
        
        # Add proper paragraph styling with tighter spacing
        html_text = f'<div style="font-family: Helvetica Neue, sans-serif; font-size: 14px; line-height: 1.4; color: #333;">{text}</div>'
        return html_text
    
    @staticmethod
    def personalize_email_body(body: str, name: str) -> str:
        """Personalize email body by replacing placeholders"""
        if name and "[Name]" in body:
            body = body.replace("[Name]", name)
        return body
    
    @staticmethod
    def parse_email_content(email_content: str) -> tuple[str, str]:
        """Parse generated email content to extract subject and body"""
        # Extract subject using multiple patterns
        subject_match = re.search(
            r"Subject:\s*(.+?)(?:\n|$)", email_content, re.IGNORECASE
        )
        
        # If first pattern doesn't match, try pattern for subject on next line
        if not subject_match:
            subject_match = re.search(
                r"Subject:\s*\n\s*(.+?)(?:\n|$)", email_content, re.IGNORECASE
            )
        
        subject = subject_match.group(1).strip() if subject_match else ""
        
        # Remove subject line from body (handle both patterns)
        body = re.sub(
            r"Subject:\s*(.+?)(?:\n|$)",
            "",
            email_content,
            flags=re.IGNORECASE,
        )
        body = re.sub(
            r"Subject:\s*\n\s*(.+?)(?:\n|$)",
            "",
            body,
            flags=re.IGNORECASE,
        )
        
        # Remove "Email Body:" label if present
        body = re.sub(
            r"Email\s+Body:\s*\n?",
            "",
            body,
            flags=re.IGNORECASE,
        ).strip()
        
        return subject, body
    
    @staticmethod
    def col_num_to_letter(col_num: int) -> str:
        """Convert column number to letter (e.g., 1 -> A, 27 -> AA)"""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + ord("A")) + result
            col_num //= 26
        return result
    
    @staticmethod
    def should_send_email(record: dict) -> tuple[bool, list]:
        """Check if email should be sent based on record data"""
        status = str(record.get("Status", "")).strip().lower()
        is_sent = str(record.get("SENT?", "")).strip().lower()
        email = str(record.get("Email", "")).strip()
        subject = str(record.get("Subject", "")).strip()
        body = str(record.get("Body", "")).strip()
        
        # Check if approved and not already sent
        if status != "approved":
            return False, ["Not approved"]
        
        if is_sent in ["true", "yes", "1"]:
            return False, ["Already sent"]
        
        # Check required fields
        missing = []
        if not email:
            missing.append("Email")
        if not subject:
            missing.append("Subject")
        if not body:
            missing.append("Body")
        
        return len(missing) == 0, missing
