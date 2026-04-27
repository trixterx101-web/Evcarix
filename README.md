# ⚡ Evcarix Auto-Studio

Bu proje, "Evcarix" YouTube kanalı için %100 otomatik, AI tabanlı ve **sıfır maliyetli** içerik üretim sistemidir.

## 🚀 Özellikler
- **Trend Takibi:** Elektrikli araç dünyasındaki en son haberleri otomatik tarar.
- **AI Senaryo:** Google Gemini API ile profesyonel senaryolar yazar.
- **Gerçekçi Ses:** Microsoft Edge-TTS ile insan kalitesinde seslendirme yapar.
- **Otomatik Montaj:** MoviePy ile görüntü, ses ve altyazıları birleştirir.
- **YouTube Entegrasyonu:** Hazır videoları otomatik olarak kanala yükler.
- **Haftalık Takvim:** Belirlediğiniz günlere göre farklı formatlarda (Shorts/Long) üretim yapar.

## 🤖 Automation (GitHub Actions)

This project is set up to run automatically every day using GitHub Actions.

### Required GitHub Secrets:
1. `GEMINI_API_KEY`: Google Gemini API Key.
2. `GROQ_API_KEY`: Groq API Key.
3. `PEXELS_API_KEY`: Pexels API Key.
4. `YOUTUBE_CLIENT_SECRET_JSON`: The content of your `client_secret.json`.
5. `YOUTUBE_TOKEN_JSON`: The content of your `token.json` (generated after the first local run).

### How it works:
- The workflow runs daily at 09:00 UTC.
- It uses `src/setup_secrets.py` to recreate the necessary JSON files from Secrets.
- It executes `main.py` which handles the entire pipeline.

## 🛠️ Kurulum

1. **Python Yükleyin:** Bilgisayarınızda Python 3.10 veya üstü yüklü olmalıdır.
2. **Kütüphaneleri Kurun:**
   ```bash
   pip install -r requirements.txt
   ```
3. **API Anahtarlarını Ayarlayın:**
   `.env.example` dosyasının adını `.env` olarak değiştirin ve aşağıdaki anahtarları girin:
    - `GEMINI_API_KEY`: [Google AI Studio](https://aistudio.google.com/)'dan ücretsiz alın.
    - `PEXELS_API_KEY`: [Pexels Developer](https://www.pexels.com/api/)'dan ücretsiz alın.
    - `GROQ_API_KEY`: [Groq Console](https://console.groq.com/)'dan ücretsiz alın (Opsiyonel).
    - `client_secret.json`: [Google Cloud Console](https://console.cloud.google.com/)'dan YouTube Data API v3 projesi oluşturup indirin.

4. **ImageMagick (Altyazı için):**
   Altyazıların görünebilmesi için [ImageMagick](https://imagemagick.org/script/download.php) yüklü olmalıdır.

## 📅 Çalıştırma
Sistemi başlatmak için:
```bash
python main.py
```

## 📈 İçerik Stratejisi
Sistem her gün çalıştığında otomatik olarak şu plana uyar:
- **Pzt-Cmt:** Shorts (Dikey, 45-60 sn)
- **Pazar:** Uzun Video (Yatay, 6-8 dk)

---
**Not:** Bu sistem %0 maliyet prensibiyle tasarlanmıştır. Tüm kullanılan API'lerin ücretsiz katmanları mevcuttur.
