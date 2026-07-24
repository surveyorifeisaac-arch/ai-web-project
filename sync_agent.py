import sqlite3
import requests
import json

# Paste your actual Google Web App URL between these quotes:
GOOGLE_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxGNnfbbdUVMBNG995-T-LRZpWJEYywFkkf0hqWu2wNk2rusYOSof7vV_90BY7J15h4vg/exec"

def sync_pending_results():
    # 1. Connect to our local SQLite data vault
    conn = sqlite3.connect('exam_vault.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 2. Extract only the scores that are marked 'PENDING'
    cursor.execute("SELECT * FROM results WHERE sync_status = 'PENDING'")
    pending_records = cursor.fetchall()
    
    if not pending_records:
        print("Sync Status: All local exam results are already up-to-date on the cloud!")
        conn.close()
        return

    print(f"Found {len(pending_records)} pending result(s). Initiating cloud synchronization...")

    # 3. Loop through each unsynced record and stream it to Google
    for record in pending_records:
        payload = {
            "student_id": record["student_id"],
            "student_name": record["student_name"],
            "score": record["score"],
            "total_questions": record["total_questions"]
        }
        
        try:
            # Dispatch HTTP POST request to your Google API endpoint
            response = requests.post(GOOGLE_WEB_APP_URL, data=json.dumps(payload))
            
            # Check if Google returned a clean success code
            if response.status_code == 200 and "success" in response.text.lower():
                # Update this specific student's record from PENDING to SYNCED
                cursor.execute(
                    "UPDATE results SET sync_status = 'SYNCED' WHERE id = ?", 
                    (record["id"],)
                )
                print(f"-> Successfully synchronized score for {record['student_name']}")
            else:
                print(f"X Server rejected packet for record ID {record['id']}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"X Network Error: Connection to Google failed. Check your internet connectivity. Details: {e}")
            break # Exit the loop if there's no internet connection at all

    # Commit the changes to update our SQLite database file
    conn.commit()
    conn.close()
    print("Synchronization sequence completed.")

if __name__ == "__main__":
    sync_pending_results()