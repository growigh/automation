#!/usr/bin/env python3
"""
Email sending functionality
"""

import smtplib
import imaplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from datetime import datetime

from src.core.config import Config
from src.utils.email_utils import EmailUtils


class EmailSender:
    """Handles email sending operations"""
    
    def __init__(self, email_config: Dict[str, str]):
        self.email_address = email_config['email_address']
        self.email_password = email_config['email_password']
        self.smtp_server = email_config['smtp_server']
        self.smtp_port = email_config['smtp_port']
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
    
    def create_email_message(self, to_email: str, subject: str, body: str, name: str = "") -> MIMEMultipart:
        """Create email message with both text and HTML parts"""
        # Personalize body
        body = EmailUtils.personalize_email_body(body, name)
        
        # Get signatures
        text_signature, html_signature = Config.get_email_signature()
        
        # Convert body to HTML format
        html_body = EmailUtils.convert_text_to_html(body) + html_signature
        body_with_signature = body + text_signature
        
        # Create message with both text and HTML parts
        msg = MIMEMultipart("alternative")
        msg["From"] = f"Nikhil Nigam <{self.email_address}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Create text and HTML parts
        text_part = MIMEText(body_with_signature, "plain")
        html_part = MIMEText(html_body, "html")
        
        # Attach parts
        msg.attach(text_part)
        msg.attach(html_part)
        
        return msg
    
    def try_smtp_connection(self, server_host: str, port: int, connection_type: str) -> Optional[smtplib.SMTP]:
        """Try to connect to SMTP server with given configuration"""
        try:
            print(f"   🔄 Trying {server_host}:{port} ({connection_type})...")
            
            if connection_type == "SSL":
                server = smtplib.SMTP_SSL(server_host, port, timeout=Config.SMTP_TIMEOUT)
                print(f"   🔒 Using SSL connection to {server_host}:{port}")
            else:
                server = smtplib.SMTP(server_host, port, timeout=Config.SMTP_TIMEOUT)
                print(f"   🔐 Starting TLS connection to {server_host}:{port}...")
                server.starttls()
            
            print("   🔑 Logging in...")
            server.login(self.email_address, self.email_password)
            
            return server
            
        except Exception as smtp_error:
            print(f"   ❌ Failed with {server_host}:{port} - {smtp_error}")
            return None
    
    def send_email(self, to_email: str, subject: str, body: str, name: str = "") -> bool:
        """Send a single email"""
        try:
            print(f"📧 Sending email to: {to_email}")
            print(f"   Using SMTP: {self.smtp_server}:{self.smtp_port}")
            print("   📦 Creating message...")
            
            # Create message
            msg = self.create_email_message(to_email, subject, body, name)
            
            print("   🔌 Connecting to SMTP server...")
            
            # Try multiple SMTP configurations
            smtp_configs = [(self.smtp_server, self.smtp_port, "SSL" if self.smtp_port == 465 else "TLS")]
            smtp_configs.extend(Config.DEFAULT_SMTP_CONFIGS)
            
            server = None
            success = False
            
            for server_host, port, connection_type in smtp_configs:
                server = self.try_smtp_connection(server_host, port, connection_type)
                if server:
                    try:
                        print("   📤 Sending message...")
                        msg_string = msg.as_string()
                        server.sendmail(self.email_address, to_email, msg_string)
                        server.quit()
                        
                        print(f"   ✅ Successfully sent via {server_host}:{port}")
                        success = True
                        
                        # Save to Sent folder
                        self.save_to_sent_folder(msg_string)
                        break
                        
                    except Exception as send_error:
                        print(f"   ❌ Failed to send: {send_error}")
                        if server:
                            try:
                                server.quit()
                            except:
                                pass
                        continue
            
            if not success:
                raise Exception("All SMTP configurations failed")
            
            print(f"✅ Email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            return False
    
    def save_to_sent_folder(self, msg_string: str) -> bool:
        """Save sent email to the Sent folder using IMAP"""
        try:
            print("   📁 Saving to Sent folder...")
            
            # Connect to IMAP server
            imap_server = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap_server.login(self.email_address, self.email_password)
            
            # Try to find the Sent folder
            sent_folder = None
            for folder in Config.SENT_FOLDER_NAMES:
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
                result = True
            else:
                print("   ⚠️  Could not find Sent folder")
                result = False
            
            imap_server.close()
            imap_server.logout()
            return result
            
        except Exception as e:
            print(f"   ⚠️  Could not save to Sent folder: {e}")
            return False
    
    def print_config_info(self):
        """Print email configuration info"""
        print(f"🚀 Starting email automation at {datetime.now()}")
        print(f"📧 Using email: {self.email_address}")
        print(f"🔧 SMTP Server: {self.smtp_server}:{self.smtp_port}")
        print(f"🔑 Password: {'*' * len(self.email_password)}")
    
    def add_rate_limiting(self):
        """Add rate limiting between emails"""
        time.sleep(Config.EMAIL_SEND_DELAY)
