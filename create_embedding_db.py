import sqlite3
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer



# Initialize the embedding model
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def create_embedding_database(excel_path: str,
                              db_path: str) -> str:
    """
    Create a SQLite database with embedded quotes from an Excel file.

    Parameters
    ----------
    excel_path : str
        Path to the input Excel file (.xlsx)
    db_path:
        Path to the output SQLite database (.db)

    Returns
    -------
    str
        Path to a db with a single table named `quotes` and schema:
        | author | quote | embedding |
    """
    # Read the Excel file
    df = pd.read_excel(excel_path)
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quotes (
        author TEXT,
        quote TEXT,
        embedding BLOB
    )
    """)
    
    # Process each quote
    for index, row in df.iterrows():
        author = row["author"]
        quote = row["quote"]
        
        # Generate embedding (convert to float32 for smaller storage)
        embedding = EMBEDDING_MODEL.encode(quote).astype(np.float32)
        
        # Store in database (convert numpy array to bytes)
        cursor.execute(
            "INSERT INTO quotes (author, quote, embedding) VALUES (?, ?, ?)",
            (author, quote, embedding.tobytes())
        )
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print(f"Successfully created database at {db_path} with {len(df)} quotes.")



if __name__ == "__main__":

    create_embedding_database(
        excel_path="quotes.xlsx",
        db_path="quotes.db"
    )
