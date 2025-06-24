#!/usr/bin/env python3
"""
Configuration management for email automation
"""

import os
from typing import List


class Config:
    """Configuration settings for email automation"""
    
    # Google Sheets Configuration
    GOOGLE_SHEETS_SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    
    # Email Configuration
    DEFAULT_SMTP_CONFIGS = [
        ("smtpout.secureserver.net", 465, "SSL"),
        ("smtpout.secureserver.net", 587, "TLS"),
        ("smtpout.secureserver.net", 25, "TLS"),
        ("smtp.secureserver.net", 465, "SSL"),
        ("smtp.secureserver.net", 587, "TLS")
    ]
    
    # IMAP Configuration
    DEFAULT_IMAP_SERVER = "imap.secureserver.net"
    DEFAULT_IMAP_PORT = 993
    
    # Sent folder names to try
    SENT_FOLDER_NAMES = ['Sent', 'Sent Items', 'INBOX.Sent']
    
    # Required columns
    REQUIRED_GENERATION_COLUMNS = ["Read For Body?", "Name", "Company", "Website", "Body", "Subject", "SENT?"]
    
    # Status values
    APPROVED_STATUS = "approved"
    SENT_VALUES = ["true", "yes", "1", "TRUE"]
    
    # AI Configuration
    AI_MODEL = "gemini-2.5-flash"
    AI_TEMPERATURE = 0
    AI_MAX_RETRIES = 2
    
    # Rate limiting
    EMAIL_SEND_DELAY = 2  # seconds
    API_CALL_DELAY = 3    # seconds
    
    # SMTP Configuration
    SMTP_TIMEOUT = 30     # seconds
    
    @staticmethod
    def get_service_account_file() -> str:
        """Get service account file path"""
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "key.json")
        
        if not os.path.exists(service_account_file):
            # Try relative to the project root (two levels up from src/core)
            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            service_account_file = os.path.join(script_dir, service_account_file)
        
        return service_account_file
    
    @staticmethod
    def get_prompt_file_paths() -> List[str]:
        """Get potential prompt file paths"""
        # Get project root directory (two levels up from src/core)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return [
            os.path.join(project_root, "prompt.txt"),
            os.path.join(project_root, "..", "email-body", "prompt.txt"),
            "prompt.txt"  # Fallback to current directory
        ]
    
    @staticmethod
    def get_email_signature() -> tuple[str, str]:
        """Get email signature for text and HTML"""
        text_signature = """
Best Regards,
Nikhil Nigam
IIT Kanpur
Growigh.com"""
        
        html_signature = """<br>
Best Regards,<br>
Nikhil Nigam<br>
IIT Kanpur<br>
<a href="https://Growigh.com">Growigh.com</a>"""
        
        return text_signature, html_signature
    
    @staticmethod
    def get_sheets_urls() -> List[str]:
        """Get Google Sheets URLs from environment"""
        urls = os.getenv("GOOGLE_SHEETS_URLS", "").split(",")
        return [url.strip() for url in urls if url.strip()]
    
    @staticmethod
    def get_email_config() -> dict:
        """Get email configuration from environment"""
        return {
            'email_address': os.getenv("EMAIL_ADDRESS"),
            'email_password': os.getenv("EMAIL_PASSWORD"),
            'smtp_server': os.getenv("SMTP_SERVER", "smtp.godaddy.com"),
            'smtp_port': int(os.getenv("SMTP_PORT", 587)),
            'imap_server': os.getenv("IMAP_SERVER", Config.DEFAULT_IMAP_SERVER),
            'imap_port': int(os.getenv("IMAP_PORT", Config.DEFAULT_IMAP_PORT))
        }
