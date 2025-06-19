import os
from core.message_sender import WhatsAppMessageSender
from utils.contact_manager import cleanup_all_contacted_from_sources

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("WhatsApp Automation Tool")
    print("=" * 25)
    print("1. Start WhatsApp automation")
    print("2. Cleanup contacted numbers from source files")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == '1':
        print("\nStarting WhatsApp automation...\n")
        sender = WhatsAppMessageSender()
        sender.run()
    elif choice == '2':
        print("\nCleaning up contacted numbers from source files...")
        response = input("This will remove all contacted numbers from your source CSV files.\nDo you want to continue? (y/N): ")
        if response.lower() in ['y', 'yes']:
            cleanup_all_contacted_from_sources()
        else:
            print("❌ Cleanup cancelled.")
    elif choice == '3':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()