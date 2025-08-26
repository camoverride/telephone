import logging
import multiprocessing
import numpy as np
from openai import OpenAI
import requests
import sqlite3
import time
import yaml
import asyncio
from googletrans import Translator
from models.markov._train_markov_model import load_model, generate_text
from utils import phone_picked_up, create_embedding



# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')


# Load config file
# This will pull API endpoints and the system prompt.
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


def prompt_similarity(
    text: str,
    dataset_path: str
) -> str:
    """
    Compares the input text to prompts in a dataset.
    Identifies the most similar prompt/reply pair and
    returns the path to the pre-computed reply.

    Parameters
    ----------
    text : str
        Something spoken by the user.
    dataset_path : str
        Path to a sqlite3 dataset with the schema:
            CREATE TABLE qa_pairs (
                question TEXT,
                question_embedding BLOB,
                answer TEXT,
                answer_embedding BLOB,
                path_to_answer_wav TEXT
            );

    Returns
    -------
    str
        Path to an existing pre-computed reply.
    """
    # Step 1: Create embedding for input text
    input_embedding = create_embedding(text)

    # Step 2: Connect to database
    conn = sqlite3.connect(dataset_path)
    cursor = conn.cursor()

    # Step 3: Load all question embeddings and corresponding paths
    cursor.execute("SELECT question_embedding, path_to_answer_wav FROM qa_pairs")
    rows = cursor.fetchall()

    best_similarity = -1
    best_path = None

    for row in rows:
        blob = row[0]
        path = row[1]

        # Step 4: Deserialize DB-stored embedding
        stored_embedding = np.frombuffer(blob, dtype=np.float32)

        # Step 5: Cosine similarity
        dot_product = np.dot(input_embedding, stored_embedding)
        norm_product = np.linalg.norm(input_embedding) * np.linalg.norm(stored_embedding)
        similarity = dot_product / norm_product if norm_product != 0 else -1

        # Step 6: Track best match
        if similarity > best_similarity:
            best_similarity = similarity
            best_path = path

    conn.close()

    if best_path is None:
        raise ValueError("No embeddings found in database.")

    return best_path


async def translate(
    text : str,
    language : str) -> str:
    """
    Translates text from English into a target language.

    Parameters
    ----------
    text : str
        Some input text.
    language : str
        The desired output language: "fr", "zh-cn", etc.

    Returns
    -------
    str
        The text, translated.
    """
    translator = Translator()
    result = await translator.translate(text, dest=language)
    
    return result.text


def deepseek_model(
    text: str,
    system_prompt : str) -> str | None:
    """
    Use the deepseek LLM to produce a response related to the text.

    NOTE: temperature is hard-coded to 1.5, for poetry.
    See: https://api-docs.deepseek.com/quick_start/parameter_settings

    Parameters
    ----------
    text : str
        Something said by a user.
    
    Returns
    -------
    str
        The response from the deepseek model.
    """
    # Locally saved API key.
    with open("deepseek_api_key.txt", "r") as f:
        deepseek_api_key = f.read().strip()

    # Access the client.
    client = OpenAI(
        api_key=deepseek_api_key,
        base_url="https://api.deepseek.com")

    # Send request to the API.
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system",
             "content": system_prompt},
            {"role": "user",
             "content": text},
        ],
        stream=False,
        temperature=1.5
    )

    return response.choices[0].message.content


def tiny_llama_model(text: str) -> str:
    """
    Use the tiny-llama LLM to produce a response related to
    the `text`.
    
    NOTE: see `config.yaml` for the system prompt and API endpoint.

    Parameters
    ----------
    text : str
        Something said by a user.
    
    Returns
    -------
    str
        The response from the tiny-llama model.
    """
    # NOTE: there might be a better way to format the system prompt.
    full_prompt = f"Human: {config['system_prompt']} {text} ### Assistant:"

    # Hit the API endpoint.
    response = requests.post(
        url=config["tiny_llama_api_url"],
        json={"prompt": full_prompt},
        headers={"Content-Type": "application/json"})

    # Check the server's response.
    if response.ok:

        return response.json()["reply"]

    else:
        logging.warning(
            "Error:",
            response.status_code,
            response.text)

        return "Model offline!"


def random_markov_model(
    length : int,
    start_word : str,
    model_path : str) -> str:
    """
    Uses a random markov model trained off some poetry.

    NOTE: model output is not conditioned off user input.

    Parameters
    ----------
    length : int
        How many words should be in the output.
    start_word : str
        The first word in the response.
        NOTE: this word must belong to the vocabulary.
    model_path : str
        Path to the trained model.
    
    Returns
    -------
    str
        Words in a string.
    """
    # Load model
    loaded_model = load_model(model_path)

    # Generate and print text
    text = generate_text(
        loaded_model,
        start_word=start_word,
        length=length)

    return text


# def get_response(
#     text : str,
#     model : str,
#     language : str) -> str | None:
#     """
#     Produces a text reply to a text input.

#     Parameters
#     ----------
#     text : str
#         The input text that the response is conditioned on.
#     model : str
#         Which model to use. Current models:
#             - "echo"
#                 Repeats back the input text.
#             - "random_markov"
#                 Random text from a trained markov model.
#             - "tiny_llama"
#                 A small LLM
#             - "jeff"
#                 Pre-recorded Bezos sounds.
#     language : str | None
#         Which language to translate to, if any.

#     Returns
#     ------
#     str
#         The reply generated by the model.
#     """
#     if model == "echo":
#         response = text

#     elif model == "translate":
#         response = asyncio.run(translate(text=text, language=language))


#     if model == "random_markov":
#         response = random_markov_model(
#             length=30,
#             start_word="the",
#             model_path="models/markov/_random_poems_model.pkl")

#     if model == "tiny_llama":
#         response = tiny_llama_model(text=text)

#     if model == "deepseek":
#         response = deepseek_model(
#             text=text,
#             system_prompt=config["system_prompt"])
        
#     if model == "jeff":
#         response = prompt_similarity(
#             text=text,
#             dataset_path="data/qa_pairs.db")

#     return str(response)


def _get_response_worker(
    text: str,
    model: str,
    result_queue: multiprocessing.Queue,
    language : str):
    try:
        if model == "echo":
            response = text

        elif model == "translate":
            response = asyncio.run(translate(text=text, language=language))

        elif model == "random_markov":
            response = random_markov_model(
                length=30,
                start_word="the",
                model_path="models/markov/_random_poems_model.pkl")

        elif model == "tiny_llama":
            response = tiny_llama_model(text=text)

        elif model == "deepseek":
            response = deepseek_model(
                text=text,
                system_prompt=config["system_prompt"])

        if model == "jeff":
            response = prompt_similarity(
                text=text,
                dataset_path="data/qa_pairs.db")

        else:
            response = f"[Unknown model: {model}]"

        result_queue.put(response)

    except Exception as e:
        print(e)
        result_queue.put(None)


def killable_get_response(
    text: str, 
    model: str,
    language) -> str | None:

    result_queue = multiprocessing.Queue()
    proc = multiprocessing.Process(
        target=_get_response_worker,
        args=(text, model, result_queue, language))
    proc.start()

    try:
        while proc.is_alive():
            if not phone_picked_up():
                proc.terminate()
                proc.join()
                return None
            time.sleep(0.1)

        if not result_queue.empty():
            return result_queue.get()

        return None

    except KeyboardInterrupt:
        proc.terminate()
        proc.join()
        return None
