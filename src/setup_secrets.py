import os
import json

def setup_secrets():
    # client_secret.json oluştur
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
    if client_secret:
        with open("client_secret.json", "w") as f:
            f.write(client_secret)
        print("client_secret.json oluşturuldu.")

    # token.json oluştur
    youtube_token = os.getenv("YOUTUBE_TOKEN_JSON")
    if youtube_token:
        with open("token.json", "w") as f:
            f.write(youtube_token)
        print("token.json oluşturuldu.")

if __name__ == "__main__":
    setup_secrets()
