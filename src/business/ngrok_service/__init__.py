import os
from pyngrok import ngrok

from dotenv import load_dotenv
load_dotenv()


def connect_tunnel(
    auth_token=None,
    address=8000,
    protocol="http",
    endpoint=None
):
    if auth_token is None or auth_token == '':
        auth_token = os.getenv("NGROK_AUTHTOKEN")
    if endpoint is None or endpoint == '':
        endpoint = os.getenv("NGROK_ENDPOINT")
    ngrok.set_auth_token(auth_token)
    tunnel = ngrok.connect(address, protocol, domain=endpoint)
    print("Public URL:", tunnel.public_url)