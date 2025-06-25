#!/usr/bin/env python3
"""
Email draft management functionality
"""

import imaplib
import time
from email.mime.text import MIMEText
from typing import Dict
from datetime import datetime

from src.core.config import Config
from src.utils.email_utils import EmailUtils


class EmailDraftManager:
    """Handles email draft operations"""
    
    def __init__(self, email_config: Dict[str, str]):
        self.email_address = email_config['email_address']
        self.email_password = email_config['email_password']
        self.imap_server = email_config['imap_server']
        self.imap_port = email_config['imap_port']
    
    def validate_config(self) -> bool:
        """Validate email configuration"""
        if not self.email_address or not self.email_password:
            print("❌ Email credentials not found in .env file")
            print("   Please check your .env file contains:")
            print("   EMAIL_ADDRESS=your-email@domain.com")
            print("   EMAIL_PASSWORD=your-password")
            return False
        return True
    
    def create_email_message(self, to_email: str, subject: str, body: str, name: str = "") -> MIMEText:
        """Create email message with plain text only"""
        # Personalize body
        body = EmailUtils.personalize_email_body(body, name)
        
        # Get signatures
        text_signature, _ = Config.get_email_signature()
        
        # Use only plain text formatting
        body_with_signature = body + text_signature
        
        # Create message with plain text only
        msg = MIMEText(body_with_signature, "plain")
        msg["From"] = f"Nikhil Nigam <{self.email_address}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        return msg
    
    def save_email_to_drafts(self, to_email: str, subject: str, body: str, name: str = "") -> bool:
        """Save email to drafts folder"""
        try:
            print(f"📧 Creating draft for: {to_email}")
            print("   📦 Creating message...")
            
            # Create message
            msg = self.create_email_message(to_email, subject, body, name)
            
            print("   � Saving to Drafts folder...")
            
            # Save to Drafts folder
            success = self.save_to_drafts_folder(msg.as_string())
            
            if success:
                print(f"✅ Draft saved for {to_email}")
                return True
            else:
                raise Exception("Failed to save to drafts")
            
        except Exception as e:
            print(f"❌ Failed to save draft for {to_email}: {e}")
            return False
    
    def save_to_drafts_folder(self, msg_string: str) -> bool:
        """Save email to the Drafts folder using IMAP"""
        try:
            print("   📁 Connecting to IMAP server...")
            
            # Connect to IMAP server
            imap_server = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap_server.login(self.email_address, self.email_password)
            
            # Try to find the Drafts folder
            drafts_folder = None
            for folder in Config.DRAFT_FOLDER_NAMES:
                try:
                    imap_server.select(folder)
                    drafts_folder = folder
                    break
                except:
                    continue
            
            if drafts_folder:
                # Append the message to the Drafts folder
                imap_server.append(drafts_folder, '\\Draft', None, msg_string.encode('utf-8'))
                print(f"   ✅ Email saved to {drafts_folder} folder")
                result = True
            else:
                print("   ⚠️  Could not find Drafts folder")
                result = False
            
            imap_server.close()
            imap_server.logout()
            return result
            
        except Exception as e:
            print(f"   ⚠️  Could not save to Drafts folder: {e}")
            return False

    def print_config_info(self):
        """Print email configuration info"""
        print(f"🚀 Starting email automation at {datetime.now()}")
        print(f"📧 Using email: {self.email_address}")
        print(f"🔧 IMAP Server: {self.imap_server}:{self.imap_port}")
        print(f"🔑 Password: {'*' * len(self.email_password)}")
        print("📁 Mode: Saving to Drafts (not sending)")