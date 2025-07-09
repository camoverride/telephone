import requests
import yaml



# Load config file
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


def print_text(text : str,
               printer_api: str) -> None:
    """
    Sends some text to a thermal printer to be printed out.

    Parameters
    ----------
    text : str
        Some text to be printed
    printer_api : str
        The endpoint.

    Returns
    -------
    None
        Prints text.
    """
    print(f"Printing this: {text}")
    data = {"text": text}

    response = requests.post(printer_api, json=data)

    print(response.json())


if __name__ == "__main__":

    text = """
    Hot dough, cheese melts bright
    Tomato kisses, crisp crust sings
    Joy in every slice
    """
    print_text(text=text, printer_api=config["printer_server_url"])
