"""
Bu script YouTube OAuth token'ını yeniden oluşturur.
Çalıştırdıktan sonra tarayıcınızda Google hesabınızla giriş yapın ve izin verin.
Yeni token.json dosyası otomatik oluşacak (youtube.upload + youtube.force-ssl scope ile).
"""
import os
import sys

# Eski token'ı sil ki yeni scope'larla yeniden oluşturulsun
if os.path.exists("token.json"):
    print("Eski token.json siliniyor...")
    os.remove("token.json")
    print("Silindi.")

if not os.path.exists("client_secret.json"):
    print("HATA: client_secret.json bulunamadı!")
    print("Google Cloud Console > APIs & Services > Credentials > OAuth 2.0 Client IDs")
    print("'Download JSON' ile client_secret.json'i indirip bu klasöre kopyalayın.")
    sys.exit(1)

# uploader.py'deki scope'larla token yenile
from google_auth_oauthlib.flow import InstalledAppFlow

scopes = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

print("Tarayıcınızda Google OAuth ekranı açılacak...")
print("Hesabınızla giriş yapın ve TÜM izinleri verin (Upload + Thumbnail).\n")

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes)
creds = flow.run_local_server(port=0)

with open("token.json", "w") as token:
    token.write(creds.to_json())

print("\nYeni token.json başarıyla oluşturuldu!")
print("Artık thumbnail yükleme sorunu çözülmüş olmalı.")
print("\nGitHub Actions için bu token.json dosyasının İÇERİĞİNİ")
print("Settings > Secrets and variables > Actions > New repository secret")
print("YOUTUBE_TOKEN_JSON olarak ekleyin.")
