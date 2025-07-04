#!/usr/bin/env python3
"""
AI-powered email generation functionality
"""

import os
import getpass
import time
from typing import Dict

from src.core.config import Config
from src.utils.email_utils import EmailUtils

# Import AI components with fallback
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_google_genai import ChatGoogleGenerativeAI
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class EmailGenerator:
    """Handles AI-powered email generation"""
    
    def __init__(self):
        self.llm = None
        self.email_prompt = None
    
    def is_ai_available(self) -> bool:
        """Check if AI dependencies are available"""
        return AI_AVAILABLE
    
    def initialize_llm(self) -> bool:
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
                model=Config.AI_MODEL,
                temperature=Config.AI_TEMPERATURE,
                max_tokens=None,
                timeout=None,
                max_retries=Config.AI_MAX_RETRIES,
                google_api_key=api_key,
            )
            print("✅ AI model initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AI model: {e}")
            return False
    
    def load_email_prompt(self) -> bool:
        """Load the email prompt template"""
        try:
            prompt_files = Config.get_prompt_file_paths()
            
            for prompt_file in prompt_files:
                if os.path.exists(prompt_file):
                    with open(prompt_file, "r") as f:
                        self.email_prompt = f.read()
                        print(f"✅ Loaded email prompt from {prompt_file}")
                        return True
            
            # Error if prompt.txt not found
            print("❌ ERROR: prompt.txt file not found!")
            print("   Searched in the following locations:")
            for prompt_file in prompt_files:
                print(f"     - {prompt_file}")
            print("   Please create a prompt.txt file with your email template.")
            return False
            
        except Exception as e:
            print(f"❌ Error loading prompt: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Check if generator is ready to use"""
        return self.llm is not None and self.email_prompt is not None
    
    def extract_row_data(self, row_data: Dict) -> Dict[str, str]:
        """Extract relevant information from row data"""
        data = {
            'name': row_data.get("Name", ""),
            'title': row_data.get("Title", ""),
            'company': row_data.get("Company", ""),
            'website': row_data.get("Website", ""),
            'issues': row_data.get("ISSUES", ""),
            'keywords': row_data.get("Keywords", "")
        }
        
        # Add domain
        if data['website']:
            data['domain'] = EmailUtils.extract_domain_from_url(data['website'])
        else:
            data['domain'] = ""
        
        return data
    
    def validate_essential_data(self, data: Dict[str, str]) -> bool:
        """Validate if essential data is present"""
        # Only require company and website - name is optional (will use "Hi," if missing)
        return bool(data['company'] and data['website'])
    
    def create_user_prompt(self, data: Dict[str, str]) -> str:
        """Create user prompt with extracted data"""
        # Use "Hi," if name is not present, otherwise use the name
        greeting_name = data['name'] if data['name'].strip() else "Hi,"
        
        return f"""
Generate an outreach email with the following details:

Recipient Name: {greeting_name}
Title: {data['title']}
Company: {data['company']}
Website: {data['website']}
Domain: {data['domain']}
Issues: {data['issues']}
Keywords/Services: {data['keywords']}

Follow the template format and guidelines provided in the system prompt.
IMPORTANT: If Recipient Name is "Hi,", start the email body with "Hi," instead of trying to personalize with a specific name. Use "Hi," as the greeting in the email body itself.
"""
    
    def generate_email_content(self, row_data: Dict) -> str:
        """Generate email content for a single row of data"""
        if not self.is_ready():
            return "Error: AI model not initialized"
        
        try:
            # Extract relevant information from the row
            data = self.extract_row_data(row_data)
            
            # Validate essential data
            if not self.validate_essential_data(data):
                return "Error: Missing essential data (Name, Company, or Website)"
            
            # Create the user prompt with the data
            user_prompt = self.create_user_prompt(data)
            
            # Create the complete prompt
            chat_prompt = ChatPromptTemplate(
                [("system", self.email_prompt), ("user", user_prompt)]
            )
            
            # Generate the email
            chain = chat_prompt | self.llm | StrOutputParser()
            result = chain.invoke({})
            
            return result
            
        except Exception as e:
            name = row_data.get("Name", "Unknown")
            print(f"Error generating email for {name}: {e}")
            return f"Error generating email: {str(e)}"
    
    def update_worksheet_with_content(self, worksheet, row_idx: int, column_map: Dict[str, int], 
                                    subject: str, body: str) -> bool:
        """Update worksheet with generated content"""
        try:
            body_col = column_map.get("Body")
            subject_col = column_map.get("Subject")
            
            # Validate required columns exist
            if not body_col:
                print(f"❌ ERROR: 'Body' column not found in worksheet '{worksheet.title}'")
                return False
            
            if not subject_col:
                print(f"❌ ERROR: 'Subject' column not found in worksheet '{worksheet.title}'")
                return False
            
            # Update Body column
            if body and body_col:
                body_col_letter = EmailUtils.col_num_to_letter(body_col)
                worksheet.update(f"{body_col_letter}{row_idx}", body)
                print(f"  ✅ Updated body ({len(body)} characters)")
            else:
                print(f"  ⚠️  Warning: No body content generated for row {row_idx}")
            
            # Update Subject column
            if subject and subject_col:
                subject_col_letter = EmailUtils.col_num_to_letter(subject_col)
                worksheet.update(f"{subject_col_letter}{row_idx}", subject)
                print(f"  ✅ Updated subject: {subject[:50]}...")
            else:
                print(f"  ⚠️  Warning: No subject content generated for row {row_idx}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating row {row_idx}: {e}")
            return False
    
    def add_api_delay(self):
        """Add delay to avoid API rate limits"""
        time.sleep(Config.API_CALL_DELAY)
