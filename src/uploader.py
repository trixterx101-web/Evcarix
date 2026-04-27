import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

class YouTubeUploader:
    def __init__(self, client_secrets_file):
        self.scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        self.client_secrets_file = client_secrets_file
        self.youtube = self.get_authenticated_service()

    def get_authenticated_service(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        
        creds = None
        token_file = "token.json"
        
        # token.json dosyası varsa yükle
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.scopes)
        
        # Eğer geçerli kimlik bilgisi yoksa veya süresi dolmuşsa yenile/oluştur
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # CI/CD ortamında bu aşamaya gelmemeli, token.json önceden hazırlanmalı
                if os.getenv("CI"):
                    raise Exception("GitHub Actions ortamında geçerli token.json bulunamadı!")
                
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.scopes)
                creds = flow.run_local_server(port=0)
            
            # Gelecek kullanım için sakla
            with open(token_file, "w") as token:
                token.write(creds.to_json())
        
        return build("youtube", "v3", credentials=creds)

    def upload_video(self, file_path, title, description, tags, category_id="28"):
        """Videoyu YouTube'a yükler (28: Science & Technology)."""
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": "public", # Veya 'unlisted' / 'private'
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Yükleniyor: %{int(status.progress() * 100)}")
        
        print(f"Yükleme Tamamlandı! Video ID: {response['id']}")
        return response['id']

if __name__ == "__main__":
    # uploader = YouTubeUploader("client_secret.json")
    # uploader.upload_video("output/test.mp4", "Test Başlık", "Test Açıklama", ["ev", "car"])
    pass
