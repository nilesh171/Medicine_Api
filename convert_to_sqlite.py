import pandas as pd
import sqlite3

# Load the CSV
csv_file = 'A_Z_medicines_dataset_of_India.csv'  # Update if your CSV has a different name
try:
    df = pd.read_csv(csv_file)
    print("CSV loaded successfully")
except Exception as e:
    print(f"Error loading CSV: {e}")
    exit(1)

# Rename price column for consistency
df = df.rename(columns={'price(₹)': 'price'})

# Add name_lower column
df['name_lower'] = df['name'].str.lower()

# Create SQLite database
db_file = 'medicines.db'
conn = sqlite3.connect(db_file)

# Convert CSV to SQLite table
df.to_sql('medicines', conn, if_exists='replace', index=False)
print(f"Converted {csv_file} to {db_file}")

# Verify the data
df_sql = pd.read_sql('SELECT * FROM medicines LIMIT 5', conn)
print("Sample data from SQLite:")
print(df_sql)

# Close connection
conn.close()