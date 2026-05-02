# Evcarix Auto-Studio — Çalışma Mantığı

## 📋 Genel Bakış

Evcarix, YouTube Shorts formatında otomatik EV (Electric Vehicle) içerik üreten bir otomasyon sistemidir. Sistem, konu planlamasından video üretime kadar tüm süreci tamamen otomatize eder.

---

## 🔄 Ana İş Akışı

### 1. Başlangıç (`main.py`)

```
┌─────────────────────────────────────────────────────────┐
│  1. Ortam değişkenlerini yükle (.env)                    │
│  2. YouTube API kimlik dosyalarını oluştur (secrets)    │
│  3. Orchestrator'ı başlat                               │
│  4. run_daily_shorts_workflow() çalıştır                │
└─────────────────────────────────────────────────────────┘
```

---

## 🧠 2. Planlama Aşaması (`brain.py`)

### 2.1 YouTube Trend Tetikleyici (ÖNCELİKLI)

```
┌─────────────────────────────────────────────────────────┐
│  TrendEngine.trigger_from_youtube_trend(hours_back=48)  │
│  └─ Son 48 saatteki EV Short'larını ara                 │
│  └─ Kullanılmamış bir trend seç                         │
│  └─ Orijinal script üret (10 LLM fallback)              │
│  └─ Trend varsa → TREND MOD AKTİF                       │
└─────────────────────────────────────────────────────────┘
```

**Eğer trend bulunursa:**
- Başlık, konu, script, description, tags trend'ten ilham alınarak üretilir
- Görüntü/ses KOPYALANMAZ, tamamen orijinal içerik üretilir
- SEO metadata eklenir
- Plan kaydedilir (`daily_plan.json`)

### 2.2 Normal Konu Havuzu (FALLBACK)

```
┌─────────────────────────────────────────────────────────┐
│  _TOPIC_POOL'dan konu seç (67 konu, 9 kategori)        │
│  └─ Daha önce kullanılmayan konu                        │
│  └─ Her kategoriden çeşitlilik sağla                    │
│  └─ Hepsi kullanıldıysa en eski konuları tekrar kullan  │
└─────────────────────────────────────────────────────────┘
```

**Kategoriler:**
1. battery_science (8 konu)
2. range_tests (8 konu)
3. charging (8 konu)
4. cost_ownership (8 konu)
5. comparisons (7 konu)
6. market_data (7 konu)
7. infrastructure (7 konu)
8. education (7 konu)
9. interactive_tools (7 konu)

**TOPLAM: 67 Konu**

---

## ✍️ 3. İçerik Üretimi (`writer.py`)

### 3.1 Çoklu LLM Fallback (10 LLM)

```
┌─────────────────────────────────────────────────────────┐
│  1. Gemini (3 API key) → 429/RESOURCE_EXHAUSTED → Groq  │
│  2. Groq (3 API key, Llama3-70B) → Hata → OpenRouter    │
│  3. OpenRouter → Hata → Mistral                          │
│  4. Mistral → Hata → Together AI                        │
│  5. Together AI → Hata → DeepSeek                       │
│  6. DeepSeek → Hata → Anthropic Claude                  │
│  7. Anthropic Claude → Hata → OpenAI GPT-4              │
│  8. OpenAI GPT-4 → Hata → Cohere                        │
│  9. Cohere → Hata → HuggingFace                         │
│  10. HuggingFace → Hata → Fallback template             │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Üretilen İçerikler

- **Başlık**: Viral YouTube Shorts başlığı (emoji set, hook style)
- **Script**: 25-50 saniye konuşma metni (American English, global örnekler)
- **Description**: SEO optimize edilmiş açıklama
- **Tags**: YouTube SEO etiketleri

---

## 🎬 4. Video Üretimi (`media_engine.py`)

### 4.1 AI Video Üretimi (ÖNCELİKLI)

```
┌─────────────────────────────────────────────────────────┐
│  generate_ai_video_clips()                              │
│  └─ Stability AI (Stable Video Diffusion)               │
│  └─ Replicate (ZeroScope V2)                            │
│  └─ Kling AI (Kling Video)                              │
│  └─ API key yoksa → Stok videoya geç                    │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Stok Video İndirme (FALLBACK)

```
┌─────────────────────────────────────────────────────────┐
│  download_stock_videos(count=5-10)                      │
│  └─ Pexels API (öncelikli)                              │
│  └─ Pixabay API                                         │
│  └─ OEM Press Kit (Tesla, Lucid, Waymo)                 │
│  └─ NASA/DOE Public Videos                              │
│  └─ Kullanılan klip hash'leriyle filtrele               │
│  └─ Konu anahtar kelimeleriyle alakalı sorgular         │
└─────────────────────────────────────────────────────────┘
```

### 4.3 Stok Biterse Fallback

```
┌─────────────────────────────────────────────────────────┐
│  Stok videolar tükendiğinde:                            │
│  1. AI video üret (API key varsa)                       │
│  2. Yine yetersizse hash'leri temizle                   │
│  3. Klipleri tekrar kullan (başşa dön)                   │
└─────────────────────────────────────────────────────────┘
```

### 4.4 Kullanılan Klip Takibi

- `_used_clips` set'i ile kullanılan klipler takip edilir
- Hash tabanlı tekrar önleme
- `used_clips.json` dosyasına kaydetme
- Stok biterse hash temizleme ve tekrar kullanım

---

## 🗣️ 5. Seslendirme (`voice_engine.py`)

```
┌─────────────────────────────────────────────────────────┐
│  Edge-TTS kullanarak seslendirme                        │
│  └─ Kadın ses: en-US-AriaNeural                        │
│  └─ Erkek ses: en-US-AndrewNeural                      │
│  └─ Kelime zamanlaması (word timings) çıkarma          │
│  └─ Audio dosyası: assets/voice_[timestamp].mp3        │
└─────────────────────────────────────────────────────────┘
```

---

## 🎞️ 6. Video Montajı (`editor.py`)

### 6.1 Video Süresi

- **Random 25-50 saniye aralığında**
- Audio süresi hedeften kısaysa loop ile uzat (`afx.audio_loop`)
- Audio süresi hedeften uzunsa kırp

### 6.2 Video İşleme

```
┌─────────────────────────────────────────────────────────┐
│  1. Video klipleri 9:16 aspect ratio'a çevir            │
│  2. 1080x1920 çözünürlüğe resize                       │
│  3. Klipleri concatenate et                             │
│  4. Video süresi < target → loop ile uzat              │
│  5. Video süresi > target → kırp                       │
│  6. Audio'u video'ya set et                            │
│  7. Subtitle'ları overlay et (word_timings ile)        │
│  8. FFmpeg ile video export (libx264, 30fps)           │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Version-Safe Loop Implementasyonu

MoviePy v1.0.3 uyumluluğu için:
- Video loop: `video_loop()` + fallback concatenation
- Audio loop: `audio_loop()` + fallback concatenation

---

## 📤 7. YouTube Yükleme (`uploader.py`)

```
┌─────────────────────────────────────────────────────────┐
│  1. YouTube API ile authenticate (OAuth2)               │
│  2. Video yükle (YouTube Shorts format)                │
│  3. Başlık, description, tags set et                   │
│  4. Thumbnail yükle (varsa)                            │
│  5. Video ID döndür                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 📅 8. Schedule (GitHub Actions)

### 8.1 Daily Video Workflow

```
┌─────────────────────────────────────────────────────────┐
│  TR 10:00 (UTC 07:00) → TREND mod                       │
│  └─ YouTube trend'inden ilham al                        │
│  └─ CONTENT_MODE=trend                                  │
│  └─ UPLOAD_SLOT=morning                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  TR 16:00 (UTC 13:00) → AUTO mod                       │
│  └─ Normal konu havuzundan seçim                       │
│  └─ CONTENT_MODE=auto                                   │
│  └─ UPLOAD_SLOT=evening                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 9. Hata Yönetimi ve Fallback

### 9.1 LLM Fallback
- 10 farklı LLM API'si sırayla denenir
- Kota aşıldığında otomatik sonraki LLM'e geçiş
- Tüm LLM'ler başarısız olursa fallback template

### 9.2 Video Kaynak Fallback
1. AI video (öncelikli)
2. Pexels (stok)
3. Pixabay (stok)
4. OEM Press Kit
5. NASA/DOE Public
6. Stok biterse → AI video + tekrar kullanım

### 9.3 Audio/Video Loop Fallback
- MoviePy v2.x uyumluluğu için version-safe implementasyon
- `audio_loop()` / `video_loop()` + manual concatenation fallback

---

## 📊 10. Veri Kalıcılığı

### 10.1 Dosyalar

- `daily_plan.json` - Günlük plan
- `content_history.json` - Konu kullanım geçmişi
- `used_clips.json` - Kullanılan video klipleri
- `token.json` - YouTube OAuth token
- `client_secret.json` - YouTube API credentials

### 10.2 Assets

- `assets/voice_[timestamp].mp3` - Seslendirme dosyaları
- `assets/coverr_*/` - İndirilen videolar
- `thumbnails/` - Video thumbnail'ları

---

## 🎯 11. Ana Özellikler

### 11.1 YouTube Trend Entegrasyonu
- Son 48 saatteki EV Short'ları tarama
- Trend'ten ilham alarak orijinal içerik üretme
- Görüntü/ses kopyalamama (telif ihlali önleme)

### 11.2 Kliplerin Tekrar Kullanımı Önleme
- Hash tabanlı takip sistemi
- Stok biterse hash temizleme ve tekrar kullanım
- Her çalışmada kullanılan klipleri kaydetme

### 11.3 Video Süresi Kontrolü
- Random 25-50 saniye aralığında
- YouTube Shorts için optimize edilmiş

### 11.4 Video Alakalılığı
- Konu başlığından anahtar kelime çıkarma
- Kategori bazlı sorgular + konu anahtar kelimeleri
- Daha alakalı video seçimi

---

## 🚀 12. Performans Optimizasyonları

- Kliplerin kullanım geçmişi ile filtreleme
- AI video üretimi için early exit (API key yoksa)
- Çoklu LLM fallback ile hızlı failover
- Video kaynakları için öncelik sırası

---

## 📝 13. Yapılandırma

### 13.1 Ortam Değişkenleri (.env)

- **LLM API Key'leri**: GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, vb.
- **Video API Key'leri**: PEXELS_API_KEY, PIXABAY_API_KEY
- **AI Video API Key'leri**: STABILITY_API_KEY, REPLICATE_API_TOKEN, KLING_ACCESS_KEY
- **YouTube API Key'leri**: YOUTUBE_API_KEY, YOUTUBE_CLIENT_SECRET_FILE
- **Sistem Ayarları**: CONTENT_MODE, UPLOAD_SLOT, YOUTUBE_REGION

### 13.2 Requirements

- `moviepy==1.0.3` - Video işleme
- `edge-tts` - Seslendirme
- `google-genai` - Gemini LLM
- `groq` - Groq LLM
- `requests` - API istekleri
- `python-dotenv` - Ortam değişkenleri

---

## 🎨 14. Video Stili

- **Format**: 9:16 (YouTube Shorts)
- **Çözünürlük**: 1080x1920
- **FPS**: 30
- **Codec**: libx264
- **Ses**: Stereo (2 kanal)
- **Subtitle**: Kelime zamanlaması ile senkronize

---

## 🔐 15. Güvenlik

- API key'ler `.env` dosyasında saklanır (gitignore'da)
- GitHub Secrets ile production ortamında güvenli
- YouTube OAuth2 ile güvenli yükleme
- Kullanılan kliplerin hash tabanlı takibi

---

## 📈 16. Gelecek Geliştirmeler

- Lip-sync modu (Wav2Lip)
- Daha fazla AI video sağlayıcısı
- Gelişmiş trend analitiği
- A/B test sistemi
- Video performans analitiği

---

## 📞 17. Destek ve Sorun Giderme

### 17.1 Yaygın Hatalar

- **Audio loop hatası**: MoviePy version-safe implementasyon ile çözüldü
- **NameError json**: Import eklendi
- **Klipler alakasız**: Konu anahtar kelime çıkarma eklendi
- **Stok videolar bitiyor**: AI video + tekrar kullanım fallback eklendi

### 17.5 Loglar

- Her aşamada detaylı log çıktısı
- Hata durumunda fallback mekanizmaları
- YouTube trend taraması logları

---

## 🎯 Sonuç

Evcarix, tamamen otomatik bir EV içerik üretim sistemidir. YouTube trend'inden ilham alarak veya normal konu havuzundan seçerek, çoklu LLM fallback ile içerik üretir, AI veya stok videolarla görselleştirir, seslendirir ve YouTube'a yükler. Sistem, hata yönetimi ve fallback mekanizmaları ile güvenilir çalışır.
