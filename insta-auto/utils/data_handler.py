import pandas as pd
from config.settings import USERNAMES_FILE, MESSAGED_FILE, logger

def load_usernames():
    """Load usernames from CSV and filter out already messaged users"""
    try:
        df = pd.read_csv(USERNAMES_FILE)
        usernames = df["username"].tolist()
        
        try:
            messaged_df = pd.read_csv(MESSAGED_FILE)
            messaged_users = set(messaged_df["username"].tolist())
            
            # Add logging for skipped usernames
            skipped_users = [u for u in usernames if u in messaged_users]
            if skipped_users:
                logger.info("\n⏩ Skipping already messaged users:")
                for user in skipped_users:
                    logger.info(f"⏩ Skipped: {user}")
            
            # Filter out messaged users
            usernames = [u for u in usernames if u not in messaged_users]
            logger.info(f"📝 Total new users to message: {len(usernames)}")
            
        except FileNotFoundError:
            logger.info(f"{MESSAGED_FILE} not found, processing all usernames")
        
        return usernames
    except Exception as e:
        logger.error(f"Error loading usernames: {str(e)}")
        raise

def record_messaged_user(username, timestamp):
    """Record successfully messaged users"""
    try:
        with open(MESSAGED_FILE, "a") as f:
            f.write(f"{username},{timestamp}\n")
    except Exception as e:
        logger.error(f"Error recording messaged user: {str(e)}")

def remove_username_from_file(username):
    """Remove a username from file after successful message"""
    try:
        # Read the CSV file
        df = pd.read_csv(USERNAMES_FILE)
        
        # Remove the username
        df = df[df['username'] != username]
        
        # Save back to CSV
        df.to_csv(USERNAMES_FILE, index=False)
        logger.info(f"✅ Removed {username} from {USERNAMES_FILE}")
    except Exception as e:
        logger.error(f"❌ Error removing username from file: {str(e)}")
