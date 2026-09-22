import os, requests

from dotenv import load_dotenv
load_dotenv()


def test_ngrok_tunnel():

    url = os.getenv("upstox_connector.ngrok_end_point")
    if url is None or url == '':
        url = os.getenv("NGROK_ENDPOINT")

    url = f'https://{url}/latest/upstox/postback'
    print("HAHAHAH", url)

    payload = {
        "event": "test",
        "data": {"message": "hello"}
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", 'api_version': 'v1'}
