import sqlite3
import pandas as pd
import numpy as np
from typing import List, Tuple, Any
import torch
import os
import re
from TTS.api import TTS
from sentence_transformers import SentenceTransformer



# Get device
device = "cuda" if torch.cuda.is_available() else "cpu"

# List available 🐸TTS models
print(TTS().list_models())

# Init TTS
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)


# Load the model once at module level for efficiency
_embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


def create_embedding(text: str) -> np.ndarray:
    """
    Create a sentence embedding from text using SentenceTransformer.

    Parameters
    ----------
    text : str
        Input text to embed.

    Returns
    -------
    np.ndarray
        Vector embedding of the input text.
    """
    embedding = _embedding_model.encode(text)

    return embedding  # type: ignore


def read_spreadsheet(path: str) -> pd.DataFrame:
    """
    Read the spreadsheet file into a DataFrame.

    Parameters
    ----------
    path : str
        Path to the .xlsx spreadsheet.

    Returns
    -------
    pd.DataFrame
        DataFrame containing 'question' and 'answer' columns.
    """
    df = pd.read_excel(path)
    if 'question' not in df.columns or 'answer' not in df.columns:
        raise ValueError("Spreadsheet must have 'question' and 'answer' columns")
    return df[['question', 'answer']]


def create_database(db_path: str) -> sqlite3.Connection:
    """
    Create a SQLite database and prepare the table.

    Parameters
    ----------
    db_path : str
        File path for the new SQLite database.

    Returns
    -------
    sqlite3.Connection
        Connection object to the SQLite database.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS qa_pairs (
            question TEXT,
            question_embedding BLOB,
            answer TEXT,
            answer_embedding BLOB,
            path_to_answer_wav TEXT
        )
    ''')
    conn.commit()
    return conn


def serialize_embedding(embedding: np.ndarray) -> bytes:
    """
    Serialize a numpy array embedding to bytes for SQLite storage.

    Parameters
    ----------
    embedding : np.ndarray
        The embedding vector.

    Returns
    -------
    bytes
        Serialized bytes representation.
    """
    return embedding.tobytes()


def text_to_speech(
    text: str,
    save_dir: str) -> str:
    """
    Performs TTS on a text string and saves the WAV file in save_dir.

    Parameters
    ----------
    text : str
        The input text to synthesize.
    save_dir : str
        Directory path where the WAV file will be saved.

    Returns
    -------
    str
        Full path to the saved WAV file.
    """

    # Sanitize text to create a safe filename (remove non-alphanumeric chars, spaces → _)
    safe_text = re.sub(r'\W+', '_', text.strip())[:50]  # limit length to 50 chars
    filename = f"{safe_text}.wav"
    full_path_to_file = os.path.join(save_dir, filename)

    # Ensure save directory exists
    os.makedirs(save_dir, exist_ok=True)

    # Call TTS function (assuming tts is already imported and configured)
    tts.tts_to_file(
        text=text,
        speaker_wav="jeff_90s_mono_16k.wav",
        language="en",
        file_path=full_path_to_file)

    return full_path_to_file


def process_and_store(
    df: pd.DataFrame,
    db_conn: sqlite3.Connection,
    save_dir : str) -> None:
    """
    Process each row in DataFrame, create embeddings, run tts, and store in DB.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'question' and 'answer' columns.
    db_conn : sqlite3.Connection
        Open SQLite database connection.
    save_dir : str
        Where audio files are saved.
    """
    cursor = db_conn.cursor()

    for idx, row in df.iterrows():
        try:
            question = row['question']
            answer = row['answer']

            question_emb = create_embedding(question)
            answer_emb = create_embedding(answer)
            wav_path = text_to_speech(answer, save_dir=save_dir)

            cursor.execute('''
                INSERT INTO qa_pairs
                (question, question_embedding, answer, answer_embedding, path_to_answer_wav)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                question,
                serialize_embedding(question_emb),
                answer,
                serialize_embedding(answer_emb),
                wav_path
            ))

            # 🔽 Commit after every successful row
            db_conn.commit()

            print(f"[✓] Row {idx + 1} inserted successfully")

        except Exception as e:
            print(f"[!] Error processing row {idx + 1}: {e}")



# Example usage
if __name__ == "__main__":
    # Replace with your actual paths and tts function
    spreadsheet_path = 'data/questions_answers.xlsx'
    database_path = 'data/qa_pairs.db'

    df = read_spreadsheet(spreadsheet_path)
    conn = create_database(database_path)
    process_and_store(df, conn, save_dir="data/wavs")
    conn.close()
