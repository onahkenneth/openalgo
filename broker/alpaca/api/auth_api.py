import json
import os

from utils.httpx_client import get_httpx_client

# Alpaca Auth API endpoints
AUTH_BASE_URL = "https://authx.alpaca.markets/v1/oauth2/token"


def authenticate_broker(data):
    """
    Authenticate with the broker and return the auth token.
    """
    api_key = os.getenv("BROKER_API_KEY")
    api_secret = os.getenv("BROKER_API_SECRET")
    endpoint = os.getenv("BROKER_ENDPOINT", "https://paper-api.alpaca.markets/v2")

    try:
        # Get the shared httpx client
        client = get_httpx_client()
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        }
        payload = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": api_secret,
        }
        response = client.post(
            endpoint,
            headers=headers,
            data=payload,
        )

        # Add status attribute for compatibility with the existing codebase
        response.status = response.status_code

        data = response.text
        data_dict = json.loads(data)

        if "access_token" in data_dict:
            # Return both JWT token and feed token if available (None if not)
            auth_token = data_dict["access_token"]
            return auth_token, None
        else:
            return (
                None,
                data_dict.get("message", "Authentication failed. Please try again."),
            )
    except Exception as e:
        return None, str(e)


def get_auth_token():
    pass
