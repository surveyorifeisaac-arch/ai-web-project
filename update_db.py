import sqlite3

def upgrade_database():
    conn = sqlite3.connect('exam_vault.db')
    cursor = conn.cursor()
    
    try:
        # Safely add the diagram_file column if it doesn't already exist
        cursor.execute("ALTER TABLE questions ADD COLUMN diagram_file TEXT")
        conn.commit()
        print("Database successfully upgraded with 'diagram_file' support!")
    except sqlite3.OperationalError:
        print("Database already has 'diagram_file' support. Skipping...")
        
    conn.close()

if __name__ == "__main__":
    upgrade_database()