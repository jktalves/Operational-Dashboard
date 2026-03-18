import os
import jwt
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(".env.example")


def mask_token(token: str, prefix: int = 12, suffix: int = 8) -> str:
	if not token or len(token) <= (prefix + suffix):
		return token
	return f"{token[:prefix]}...{token[-suffix:]}"


# Carregar variáveis de ambiente (exemplo seguro)
SF_LOGIN_URL = os.getenv("SF_LOGIN_URL", "https://login.salesforce.com")
SF_CONSUMER_KEY = os.getenv("SF_CONSUMER_KEY", "FAKE_KEY_FOR_TEST")
SF_CONSUMER_SECRET = os.getenv("SF_CONSUMER_SECRET", "FAKE_SECRET_FOR_TEST")
SF_USERNAME = os.getenv("SF_USERNAME", "usuario@exemplo.com")
SF_PRIVATE_KEY_PATH = os.getenv("SF_PRIVATE_KEY_PATH", "./certs/server.key")

token_url = f"{SF_LOGIN_URL}/services/oauth2/token"

with open(SF_PRIVATE_KEY_PATH, "r") as key_file:
	private_key = key_file.read()

payload = {
	"iss": SF_CONSUMER_KEY,
	"sub": SF_USERNAME,
	"aud": SF_LOGIN_URL,
	"exp": datetime.now(timezone.utc) + timedelta(minutes=3)
}

jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

response = requests.post(
	token_url,
	data={
		"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
		"assertion": jwt_token,
		"client_id": SF_CONSUMER_KEY,
		"client_secret": SF_CONSUMER_SECRET
	}
)

print("Status:", response.status_code)
response_data = response.json()
if "access_token" in response_data:
	response_data["access_token"] = mask_token(response_data["access_token"])
print("Response:", response_data)
