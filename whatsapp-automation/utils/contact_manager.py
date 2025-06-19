import pandas as pd
import os
from config.config import COLUMN_NAME, CONTACTED_CSV
from utils.normalize_number import normalize_number

def load_all_contacts(folder_path):
    all_contacts = []
    unique_numbers = set()  # Set to track unique phone numbers
    duplicate_log = {}  # Track duplicate sources for debugging
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"❌ Error: Folder {folder_path} does not exist")
    
    # Get all CSV files from the folder
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"⚠️ No CSV files found in {folder_path}")
        return all_contacts
    
    # Track duplicate counts for reporting
    total_loaded = 0
    duplicates_filtered = 0
    
    for csv_file in csv_files:
        try:
            file_path = os.path.join(folder_path, csv_file)
            df = pd.read_csv(file_path)
            
            if COLUMN_NAME in df.columns:
                contacts = df.to_dict(orient='records')
                file_added = 0
                file_duplicates = 0
                
                # Filter unique contacts from this file
                for i, contact in enumerate(contacts):
                    number = str(contact[COLUMN_NAME])
                    normalized = normalize_number(number)
                    
                    if not normalized:
                        print(f"⚠️ Invalid number format: '{number}' in {csv_file}, row {i+2}")
                        file_duplicates += 1
                        continue
                        
                    if normalized not in unique_numbers:
                        unique_numbers.add(normalized)
                        all_contacts.append(contact)
                        file_added += 1
                    else:
                        # Debug info for duplicate
                        if normalized not in duplicate_log:
                            duplicate_log[normalized] = []
                        
                        # Log this occurrence
                        duplicate_log[normalized].append({
                            'file': csv_file,
                            'row': i+2,  # +2 accounts for header row and 0-indexing
                            'original': number
                        })
                        
                        file_duplicates += 1
                
                total_loaded += file_added
                duplicates_filtered += file_duplicates
                
                print(f"✅ Loaded {file_added} contacts from {csv_file} ({file_duplicates} duplicates filtered)")
            else:
                print(f"⚠️ Skipping {csv_file} - {COLUMN_NAME} column not found")
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")
    
    # Generate detailed duplicate report
    if duplicates_filtered > 0:
        print("\n🔍 === DUPLICATE NUMBERS DETAIL ===")
        for normalized, occurrences in duplicate_log.items():
            if len(occurrences) > 1:  # True duplicates (appear multiple times)
                print(f"\n📱 Normalized number: {normalized}")
                print(f"   Appeared {len(occurrences)} times in:")
                for i, occurrence in enumerate(occurrences):
                    status = "✅ KEPT" if i == 0 else "❌ FILTERED"
                    print(f"   {i+1}. {occurrence['file']}, row {occurrence['row']}, original: {occurrence['original']} {status}")
    
    print(f"\n📊 Total summary: {total_loaded} unique contacts loaded, {duplicates_filtered} duplicates filtered")
    
    # Save a report of all duplicates found
    if duplicates_filtered > 0:
        duplicate_report = []
        for normalized, occurrences in duplicate_log.items():
            for occurrence in occurrences:
                duplicate_report.append({
                    'normalized_number': normalized,
                    'file': occurrence['file'],
                    'row': occurrence['row'],
                    'original_number': occurrence['original']
                })
        
        if duplicate_report:
            report_df = pd.DataFrame(duplicate_report)
            report_path = os.path.join(folder_path, "duplicate_report.csv")
            report_df.to_csv(report_path, index=False)
            print(f"\n📑 Duplicate report saved to: {report_path}")
    
    return all_contacts

def load_contacted_numbers():
    try:
        contacted_df = pd.read_csv(CONTACTED_CSV)
        if COLUMN_NAME not in contacted_df.columns:
            raise ValueError(f"❌ Error: '{COLUMN_NAME}' column not found in {CONTACTED_CSV}")
        contacted_numbers = set(contacted_df[COLUMN_NAME].astype(str))
        print(f"📱 Loaded {len(contacted_numbers)} previously contacted numbers")
        return contacted_numbers
    except FileNotFoundError:
        # Create file with header if it doesn't exist
        pd.DataFrame(columns=[COLUMN_NAME]).to_csv(CONTACTED_CSV, index=False)
        print(f"📄 Created new {CONTACTED_CSV} file")
        return set()
    except pd.errors.EmptyDataError:
        # Add header to empty file
        pd.DataFrame(columns=[COLUMN_NAME]).to_csv(CONTACTED_CSV, index=False)
        print(f"📄 Added header to empty {CONTACTED_CSV} file")
        return set()
    except Exception as e:
        raise Exception(f"❌ Error reading {CONTACTED_CSV}: {str(e)}")

def safely_append_to_contacted(number):
    try:
        with open(CONTACTED_CSV, 'a', newline='') as f:
            writer = pd.DataFrame([{COLUMN_NAME: number}]).to_csv(f, header=False, index=False)
    except Exception as e:
        print(f"❌ Failed to update contacted list: {e}")
        raise

def remove_contacted_from_source_files(folder_path, contacted_numbers):
    """Remove contacted numbers from source CSV files"""
    if not contacted_numbers:
        return
    
    # Normalize all contacted numbers for comparison
    normalized_contacted = {normalize_number(num) for num in contacted_numbers if normalize_number(num)}
    
    if not normalized_contacted:
        return
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"❌ Error: Folder {folder_path} does not exist")
        return
    
    # Get all CSV files from the folder
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    
    total_removed = 0
    
    for csv_file in csv_files:
        try:
            file_path = os.path.join(folder_path, csv_file)
            df = pd.read_csv(file_path)
            
            if COLUMN_NAME in df.columns:
                original_count = len(df)
                
                # Create a mask for rows to keep (not contacted)
                mask = []
                for _, row in df.iterrows():
                    number = str(row[COLUMN_NAME])
                    normalized = normalize_number(number)
                    # Keep the row if it's not in contacted numbers
                    mask.append(normalized not in normalized_contacted)
                
                # Filter the dataframe
                df_filtered = df[mask]
                removed_count = original_count - len(df_filtered)
                
                if removed_count > 0:
                    # Save the filtered dataframe back to the file
                    df_filtered.to_csv(file_path, index=False)
                    total_removed += removed_count
                    print(f"🗑️ Removed {removed_count} contacted entries from {csv_file}")
                    
        except Exception as e:
            print(f"❌ Error processing {csv_file} for removal: {e}")
    
    if total_removed > 0:
        print(f"✅ Total {total_removed} contacted entries removed from source files")

def cleanup_all_contacted_from_sources(folder_path=None, contacted_csv=None):
    """Remove all previously contacted numbers from source CSV files"""
    if folder_path is None:
        from config.config import CSV_FOLDER
        folder_path = CSV_FOLDER
    
    if contacted_csv is None:
        from config.config import CONTACTED_CSV
        contacted_csv = CONTACTED_CSV
    
    try:
        # Load all contacted numbers
        contacted_numbers = load_contacted_numbers()
        
        if not contacted_numbers:
            print("📱 No contacted numbers found to remove")
            return
        
        print(f"🧹 Starting cleanup of {len(contacted_numbers)} contacted numbers from source files...")
        
        # Remove contacted numbers from source files
        remove_contacted_from_source_files(folder_path, contacted_numbers)
        
        print("✅ Cleanup completed!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")