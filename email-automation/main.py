#!/usr/bin/env python3
"""
Email Automation Script - Send emails and generate email bodies
"""

import os
from dotenv import load_dotenv
from email_automation_class import EmailAutomation

# Load environment variables from the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(script_dir, '.env')
load_dotenv(env_file)


def main():
    """Entry point of the application"""
    automation = EmailAutomation()
    automation.run()


if __name__ == "__main__":
    main()
