import numpy as np
from openai import OpenAI
import requests
import sqlite3
import yaml
from models.markov._train_markov_model import load_model, generate_text
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity



# Load config file
# This will pull API endpoints and the system prompt.
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


# Initialize the embedding model
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def vector_quotes(text : str) -> str:
    """
    Use the vector similarity between the user's speech (`text`) and
    quotes from a database to find a similar quote.

    Assumes a sqlite database with schema:
    | author | quote | embedding |

    NOTE: see `config.yaml` for the path to the embedding database

    Parameters
    ----------
    text : str
        Something said by a user.
    
    Returns
    -------
    str
        The response from the deepseek model.
    """
    # Embed the text
    text_embedding = EMBEDDING_MODEL.encode(text)

    # Connect to the database and get all the (quote, vector) tuples.
    conn = sqlite3.connect(config["embedding_database_path"])
    cursor = conn.cursor()

    # Fetch all quotes and embeddings
    cursor.execute("SELECT author, quote, embedding FROM quotes")
    rows = cursor.fetchall()

    # Process embeddings (stored as bytes in SQLite)
    authors = []
    quotes = []
    embeddings = []

    for author, quote, embedding_bytes in rows:
        authors.append(author)
        quotes.append(quote)

        # Convert blob back to numpy array
        embeddings.append(np.frombuffer(embedding_bytes, dtype=np.float32))
            
    # Convert to 2D array
    quote_embeddings = np.stack(embeddings)
    
    # Calculate similarities
    similarities = cosine_similarity([text_embedding], quote_embeddings)
    best_match_idx = np.argmax(similarities)
    best_quote = quotes[best_match_idx]
    
    return best_quote


def deepseek_model(text: str) -> str:
    """
    Use the deepseek LLM to produce a response related to
    the `text`.
    
    NOTE: see `config.yaml` for the system prompt.

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
    with open("deepseek_api_key.txt", "r") as f:
        deepseek_api_key = f.read().strip()


    client = OpenAI(api_key=deepseek_api_key,
                    base_url="https://api.deepseek.com")

    # Send request to the API.
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system",
             "content": config["system_prompt"]},
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
    response = requests.post(url=config["tiny_llama_api_url"],
                             json={"prompt": full_prompt},
                             headers={"Content-Type": "application/json"})

    # Check the server's response.
    if response.ok:

        return response.json()["reply"]

    else:
        print("Error:", response.status_code, response.text)

        return "Model offline!"


def random_markov_model(length : int,
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
    text = generate_text(loaded_model,
                         start_word=start_word,
                         length=length)

    return text


def jason_frontend(text : str) -> str:
    """
    Send the user input to Jason's frontend and get a haiku response
    """
    headers = {"Content-Type": "application/json"}
    data = {"message": text}

    try:
        response = requests.post(config["jason_url"], headers=headers, json=data)
        response.raise_for_status()
        print(response.json())
        result = response.json()

        if result and 'user_response' in result and 'content' in result['user_response']:
            return result['user_response']['content']
        else:
            return result
    
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to frontend")
        print("Make sure the Flask app is running (python app.py)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        return None


def get_response(text : str,
                 model : str) -> str:
    """
    Produces a text reply to a text input.

    Parameters
    ----------
    text : str
        The input text that the response is conditioned on.
    model : str
        Which model to use. Current models:
            - "echo"
                Repeats back the input text.
            - "random_markov"
                Random text from a trained markov model.
            - "tiny_llama"
                A small LLM

    Returns
    ------
    str
        The reply generated by the model.
    """
    if model == "echo":
        response = text

    if model == "random_markov":
        response = random_markov_model(length=30,
                                       start_word="the",
                                       model_path="models/markov/_random_poems_model.pkl")

    if model == "tiny_llama":
        response = tiny_llama_model(text=text)

    if model == "deepseek":
        response = deepseek_model(text)

    if model == "vector_quotes":
        response = vector_quotes(text)

    if model == "jason":
        response = jason_frontend(text)

    return response


if __name__ == '__main__':
    test = get_response("test", "jason")
    print(test)