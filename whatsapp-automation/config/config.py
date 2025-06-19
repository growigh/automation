import os

# Change the BASE_DIR to point to whatsapp-automation root instead of config folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
folder = "data"
contacted_csv = "contacted.csv"

# MESSAGE = """test"""
MESSAGE = """
Hi, I'm Ayush Kumar, Co-Founder of Growigh

We just don't create websites that look great;
we create experiences that your user will 
remember about your brand.
    
Not here to sell, just here to connect, vibe, 
and share a few things that could make your 
website experience more awesome.

*Check out our portfolio: Growigh.com*
"""

CSV_FOLDER = os.path.join(BASE_DIR, folder)
CONTACTED_CSV = os.path.join(BASE_DIR, contacted_csv)
COLUMN_NAME = "phone number"  # Column name in CSV files for phone numbers
