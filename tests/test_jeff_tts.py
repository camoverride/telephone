import requests
import os
import yaml



# Load config file.
with open("../config.yaml", "r") as f:
    config = yaml.safe_load(f)


def jeff_model(text: str, server_url: str, output_audio_path: str) -> str:
    payload = {"text": text}
    headers = {"Content-Type": "application/json"}

    response = requests.post(server_url, json=payload, headers=headers)

    if response.status_code == 200:
        # Save response.content directly to file
        os.makedirs(os.path.dirname(output_audio_path) or '.', exist_ok=True)
        with open(output_audio_path, 'wb') as f:
            f.write(response.content)
        return output_audio_path
    else:
        raise RuntimeError(f"Server returned error {response.status_code}: {response.text}")



if __name__ == "__main__":
    jeff_model(
        text="hello I am Jeff baby!",
        server_url=config["jeff_tts_model_url"],
        output_audio_path="__jeff_test.wav")
