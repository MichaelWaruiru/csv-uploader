import os
import mysql.connector
import pandas as pd
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from tqdm import tqdm # For progress bar
import shutil
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Database configurations
DB_CONFIG = {
  "host": os.getenv("DB_HOST"),
  "user": os.getenv("DB_USER"),
  "password": os.getenv("DB_PASSWORD"),
  "database": os.getenv("DB_NAME"),
  "pool_name": os.getenv("DB_POOL_NAME"),
  "pool_size": int(os.getenv("DB_POOL_SIZE"))
}

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Ensure folder exists

connection_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)

ALLOWED_PATTERN = re.compile(r'^[a-zA-Z0-9,.\s@_-]+$')

def sanitize_data(df):
  """Sanitizes and validates data"""
  sanitized_rows = []
  
  for _, row in df.iterrows():
    sanitized_row = []
    for cell in row:
      cell = str(cell).strip()
      if not ALLOWED_PATTERN.match(cell):
        return None
      sanitized_row.append(cell)
    sanitized_rows.append(sanitized_row)
    
  return sanitized_rows


def insert_into_mysql(data):
  """Inserts sanitized data into MySQL with a progress bar"""
  try:
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS users (
                     id INT PRIMARY KEY AUTO_INCREMENT,
                     name VARCHAR(100),
                     email VARCHAR(100),
                     age INT
                     )
                    """)
    insert_query = "INSERT INTO users (name, email, age) VALUES (%s, %s, %s)"
    
    for row in tqdm(data, desc="Inserting into Database", unit="rows"):
      cursor.execute(insert_query, row)
      
    connection.commit()
    return cursor.rowcount
  
  except mysql.connector.Error as err:
    return f"MySQL Error: {err}"
  finally:
    cursor.close()
    connection.close()
    
  
def upload_csv():
  """Handles file selection, validation, saving, and database insertion"""
  file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
  
  if not file_path:
    messagebox.showwarning("No file selected", "Please select a CSV file.")
    return
  
  if not file_path.endswith(".csv"):
    messagebox.showerror("Invalid file", "Only CSV files are allowed.")
    return
  
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  filename = os.path.basename(file_path)
  saved_file_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}_{filename}")
  shutil.copy(file_path, saved_file_path)
  
  messagebox.showinfo("File saved", f"File saved at: {saved_file_path}")
  
  try:
    df = pd.read_csv(saved_file_path, dtype=str) # Read all columns
  except Exception as e:
    messagebox.showerror("CSV read error", f"Error reading CSV: {e}")
    return
    
  sanitized_data = sanitize_data(df)
  if sanitized_data is None:
    messagebox.showerror("Validation failed", "CSV contains invalid or malicious data.")
    return
  
  result = insert_into_mysql(sanitized_data)
  if isinstance(result, int):
    messagebox.showinfo("Success", f"Inserted {result} records into MySQL.")
  else:
    messagebox.showerror("Database error", result)
      
      
root = tk.Tk()
root.title("Secure CSV Uploader")
root.geometry("400x250")

label = tk.Label(root, text="Upload and Securely Store CSV Files", font=("Arial", 12))
label.pack(pady=10)

upload_button = tk.Button(root, text="Select CSV file", command=upload_csv, font=("Arial", 10), bg="lightblue")
upload_button.pack(pady=10)

exit_button = tk.Button(root, text="Exit", command=root.quit, font=("Arial", 10), bg="red", fg="white")
exit_button.pack(pady=10)

root.mainloop()