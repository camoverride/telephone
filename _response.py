from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import asyncio
from googletrans import Translator
import logging
import numpy as np
from openai import OpenAI
import requests
import sqlite3
from typing import Optional
import yaml
from utils import create_embedding, HealthCheckAPI
from models.markov._train_markov_model import load_model, generate_text



# Initialize Flask application and RESTful API.
app = Flask(__name__)
api = Api(app)


# Set up logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Print logs to the console.
        logging.StreamHandler(),
        # Write logs to a file.
        logging.FileHandler("server.log")])
logger = logging.getLogger(__name__)


# Load config file.
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


# Load Markov model.
MARKOV_MODEL = load_model("models/markov/_random_poems_model.pkl")

# Deepseek API key. Git ignored.
DEEPSEEK_API_KEY_PATH = "deepseek_api_key.txt"

# Question answer database for "jeff" model.
QA_DATABASE_PATH = "data/qa_pairs.db"



def prompt_similarity(
    text: str,
    dataset_path: str) -> str:
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
    # Create embedding for input text.
    input_embedding = create_embedding(text)

    # Connect to database.
    conn = sqlite3.connect(dataset_path)
    cursor = conn.cursor()

    # Load all question embeddings and corresponding paths.
    cursor.execute("SELECT question_embedding, path_to_answer_wav FROM qa_pairs")
    rows = cursor.fetchall()

    best_similarity = -1
    best_path = None

    for row in rows:
        blob = row[0]
        path = row[1]

        # Deserialize database-stored embedding.
        stored_embedding = np.frombuffer(blob, dtype=np.float32)

        # Calculate cosine similarity
        dot_product = np.dot(input_embedding, stored_embedding)
        norm_product = np.linalg.norm(input_embedding) * np.linalg.norm(stored_embedding)
        similarity = dot_product / norm_product if norm_product != 0 else -1

        # Track best match.
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
    system_prompt : str) -> Optional[str]:
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
    with open(DEEPSEEK_API_KEY_PATH, "r") as f:
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
        temperature=1.5)

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
    start_word : str) -> str:
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

    Returns
    -------
    str
        Words in a string.
    """
    # Generate and print text
    text = generate_text(
        MARKOV_MODEL,
        start_word=start_word,
        length=length)

    return text


def get_response(
    text : str,
    model : str) -> Optional[str]:
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
            - "translate"
                Translates the text from English into a target language.
            - "random_markov"
                Random text from a trained markov model.
            - "tiny_llama"
                A small LLM hosted on a custom server.
            - "deepseek"
                A call to the deepseek API.
            - "jeff"
                Pre-recorded Bezos sounds.

    Returns
    ------
    str
        The reply generated by the model.
    """
    if model == "echo":
        response = text
        return response

    if model == "translate":
        try:
            response = asyncio.run(
                translate(text=text,
                language=config["text_to_speech_language"]))
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to google translate API failed: {e}")

    if model == "random_markov":
        response = random_markov_model(
            length=30,
            start_word="the")
        return response

    if model == "tiny_llama":
        try:
            response = tiny_llama_model(text=text)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to tiny-llama API failed: {e}")

    if model == "deepseek":
        try:
            response = deepseek_model(
                        text=text,
                        system_prompt=config["system_prompt"])
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to deepseek API failed: {e}")

    if model == "jeff":
        response = prompt_similarity(
            text=text,
            dataset_path=QA_DATABASE_PATH)
        return response

    return None


class TextResponseAPI(Resource):
    """
    API Resource to handle text-based responses from multiple models.
    """

    def post(self):
        """
        Handle POST request to generate a response from a specified model.

        Expected JSON body:
        {
            "text": "string",  # The text input to the model
            "model": "string"  # The model to use (e.g., "translate", "tiny_llama", "deepseek")
        }

        Returns:
        -------
        JSON:
            - status: "success" or "error"
            - response: The model-generated response
            - message: Error message (if any failure occurs)
        """
        try:
            # Parse incoming JSON request
            data = request.get_json()

            # Get parameters
            text = data.get("text")
            model = data.get("model")

            # Validate required fields
            if not text:
                return jsonify({
                    "status": "error",
                    "message": "'text' parameter is required."
                }), 400

            if not model:
                return jsonify({
                    "status": "error",
                    "message": "'model' parameter is required."
                }), 400

            # Generate the response from the specified model
            response = get_response(text, model)

            if response is None:
                return jsonify({
                    "status": "error",
                    "message": "Invalid model or error generating response."
                }), 400

            return jsonify({
                "status": "success",
                "response": response
            })

        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
            return jsonify({
                "status": "error",
                "message": str(ve)
            }), 400

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return jsonify({
                "status": "error",
                "message": "An unexpected error occurred."
            }), 500


# Add the resources to the Flask app.
api.add_resource(TextResponseAPI, "/response")
api.add_resource(HealthCheckAPI, "/health")



if __name__ == "__main__":

    # Run the Response server.
    app.run(
        host="0.0.0.0",
        port=8013,
        debug=True)
