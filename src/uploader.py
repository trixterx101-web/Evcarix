import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

class YouTubeUploader:
    def __init__(self, client_secrets_file):
        # youtube.force-ssl is REQUIRED for thumbnails().set()
        self.scopes = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
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

    def upload_video(self, file_path, title, description, tags, category_id="2"):
        """Videoyu YouTube'a yükler.
        Category 2 = Autos & Vehicles (EV içeriği için en uygun)
        """
        # #Shorts etiketini ekle — YouTube algoritması için kritik
        if "#Shorts" not in title and len(title) < 90:
            shorts_title = title  # başlığa #Shorts eklemiyoruz, açıklamaya ekliyoruz
        else:
            shorts_title = title[:97]
        
        # Tags listesine Shorts ekle
        final_tags = list(tags) if tags else []
        for must_have in ["Shorts", "EVShorts", "ElectricCarShorts"]:
            if must_have not in final_tags:
                final_tags.append(must_have)
        # YouTube tag limiti: 500 karakter
        tag_str = ",".join(final_tags)
        if len(tag_str) > 500:
            final_tags = final_tags[:15]  # sadece ilk 15 etiketi al

        body = {
            "snippet": {
                "title": shorts_title,
                "description": description,
                "tags": final_tags,
                "categoryId": category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
                "madeForKids": False
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

    def set_thumbnail(self, video_id, thumbnail_path):
        """Video için kapak görselini yükler."""
        if not os.path.exists(thumbnail_path):
            print(f"Hata: Thumbnail dosyası bulunamadı: {thumbnail_path}")
            return
        
        try:
            print(f"Thumbnail yükleniyor: {thumbnail_path}...")
            request = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            )
            request.execute()
            print("Thumbnail başarıyla güncellendi!")
        except Exception as e:
            print(f"Thumbnail yükleme hatası: {e}")

if __name__ == "__main__":
    # uploader = YouTubeUploader("client_secret.json")
    # uploader.upload_video("output/test.mp4", "Test Başlık", "Test Açıklama", ["ev", "car"])
    pass
