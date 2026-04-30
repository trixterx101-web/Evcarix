import os
import time
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
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

    def upload_video(self, file_path, title, description, tags, category_id="2", max_retries=3):
        """Videoyu YouTube'a yükler.
        Category 2 = Autos & Vehicles (EV içeriği için en uygun)
        503/500 transient sunucu hatalarında exponential backoff ile retry yapar.
        """
        from googleapiclient.errors import ResumableUploadError
        # #Shorts etiketini ekle — YouTube algoritması için kritik
        if "#Shorts" not in title and len(title) < 90:
            shorts_title = title  # başlığa #Shorts eklemiyoruz, açıklamaya ekliyoruz
        else:
            shorts_title = title[:97]
        
        # Tags listesine Shorts ekle ve validasyon yap
        final_tags = list(tags) if tags else []
        for must_have in ["shorts", "ev", "electric vehicle"]:
            if must_have not in final_tags:
                final_tags.append(must_have)

        # YouTube tag validasyon: geçersiz karakterleri temizle
        valid_tags = []
        for tag in final_tags:
            # Hashtag ve özel karakterleri kaldır
            tag = str(tag).replace("#", "").replace(",", "").strip()
            # Sadece harf, sayı, boşluk ve tire izin ver
            tag = ''.join(c for c in tag if c.isalnum() or c in (' ', '-')).strip()
            # Küçük harfe çevir (YouTube case-insensitive)
            tag = tag.lower()
            # Minimum 2 karakter, maksimum 30 karakter
            if len(tag) >= 2 and len(tag) <= 30:
                valid_tags.append(tag)

        # Tekrarları kaldır
        final_tags = list(dict.fromkeys(valid_tags))

        # YouTube tag limiti: 500 karakter
        tag_str = ",".join(final_tags)
        if len(tag_str) > 500:
            final_tags = final_tags[:15]

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

        for attempt in range(1, max_retries + 1):
            try:
                print(f"Video yükleniyor (deneme {attempt}/{max_retries}): {file_path}...")
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
            except (HttpError, ResumableUploadError) as e:
                err_str = str(e)
                if "503" in err_str or "500" in err_str or "Service Unavailable" in err_str:
                    if attempt < max_retries:
                        wait = 30 * (2 ** (attempt - 1))
                        print(f"YouTube 503/500 hatası, {wait}s sonra tekrar deneniyor...")
                        time.sleep(wait)
                    else:
                        raise
                else:
                    raise

    def set_thumbnail(self, video_id, thumbnail_path, max_retries=4):
        """Video için kapak görselini yükler — YouTube processing süresi için exponential backoff retry."""
        if not os.path.exists(thumbnail_path):
            print(f"Hata: Thumbnail dosyası bulunamadı: {thumbnail_path}")
            return False

        for attempt in range(1, max_retries + 1):
            try:
                print(f"Thumbnail yükleniyor (deneme {attempt}/{max_retries}): {thumbnail_path}...")
                request = self.youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                )
                request.execute()
                print("Thumbnail başarıyla güncellendi!")
                return True
            except HttpError as e:
                status = e.resp.status
                error_details = e._get_reason() if hasattr(e, '_get_reason') else str(e)
                print(f"Thumbnail yükleme hatası HTTP {status}: {error_details}")
                if status == 403 and "insufficientPermissions" in str(e):
                    print("  -> youtube.force-ssl scope eksik olabilir. Token'i yenileyin.")
                    print("  -> refresh_token.py calistirip yeni token.json uretin.")
                    return False
                # 400 Bad Request = video henuz islenmemis olabilir
                if status == 400:
                    print("  -> Video henuz YouTube tarafindan islenmemis olabilir.")
                if attempt < max_retries:
                    # Exponential backoff: 30, 60, 120, 240 saniye
                    wait = 30 * (2 ** (attempt - 1))
                    print(f"  -> {wait} saniye sonra tekrar deneniyor...")
                    time.sleep(wait)
                else:
                    print("  -> Tüm denemeler başarısız. Thumbnail yüklenemedi.")
            except Exception as e:
                print(f"Thumbnail yükleme hatası (deneme {attempt}): {e}")
                if attempt < max_retries:
                    wait = 30 * (2 ** (attempt - 1))
                    print(f"  -> {wait} saniye sonra tekrar deneniyor...")
                    time.sleep(wait)
        return False

if __name__ == "__main__":
    # uploader = YouTubeUploader("client_secret.json")
    # uploader.upload_video("output/test.mp4", "Test Başlık", "Test Açıklama", ["ev", "car"])
    pass
