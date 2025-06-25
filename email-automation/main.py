#!/usr/bin/env python3
"""
Email Automation Script - save emails to draft and generate email bodies
"""

import os
import sys
from dotenv import load_dotenv

# Add src directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
sys.path.insert(0, src_dir)

from src.email_automation import EmailAutomation

# Load environment variables from the script's directory
env_file = os.path.join(script_dir, '.env')
load_dotenv(env_file)


def main():
    """Entry point of the application"""
    automation = EmailAutomation()
    automation.run()


if __name__ == "__main__":
    main()
