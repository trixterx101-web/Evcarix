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

---

## 📺 18. Haftalık Uzun Video (Weekly Long-Form)

### 18.1 Schedule

- **Zaman**: Her Pazar 11:00 Türkiye saati (08:00 UTC)
- **GitHub Actions**: `cron: '0 8 * * 0'`
- **Upload Slot**: `SUNDAY_LONG`

### 18.2 Video Spesifikasyonları

- **Format**: 1920x1080 Full HD
- **Aspect Ratio**: 16:9 (horizontal)
- **FPS**: 30
- **Süre**: 240-360 saniye (4-6 dakika, random)
- **Codec**: libx264
- **Audio Codec**: AAC, stereo

### 18.3 Pipeline Farklılıkları

**Günlük Shorts vs Haftalık Uzun Video:**

| Özellik | Shorts (Günlük) | Long-Form (Haftalık) |
|---------|----------------|---------------------|
| Çözünürlük | 1080x1920 (9:16) | 1920x1080 (16:9) |
| Süre | 25-50 saniye | 240-360 saniye |
| Video Sayısı | 5-10 klip | 30-45 klip (ceil(duration/8)) |
| Ses | Kadın/Erkek değişken | Erkek sabit |
| Title Card | Yok | Var (5 saniye) |
| Outro Card | Yok | Var (5 saniye) |
| Playlist | Yok | "Weekly Deep Dives" |
| Kategori | Varsayılan | 28 (Science & Technology) |
| made_for_kids | Varsayılan | False |

### 18.4 Title Card (5 saniye)

- **Arka plan**: Koyu mavi (#141428)
- **Yazı**: Beyaz, Arial-Bold, fontsize 70
- **İçerik**: Video başlığı
- **Pozisyon**: Merkez

### 18.5 Outro Card (5 saniye)

- **Arka plan**: Koyu mavi (#141428)
- **Yazı**: Beyaz, Arial-Bold, fontsize 60
- **İçerik**: "Subscribe for more EV data — Evcarix"
- **Pozisyon**: Merkez

### 18.6 Video Montajı

**src/editor.py - `assemble_weekly_long_video()`**:

1. Audio loop (version-safe implementation)
2. Video klipleri 16:9 crop ve 1920x1080 resize
3. Video loop (version-safe implementation)
4. Title card (5s) ekle
5. Ana video (target_duration) ekle
6. Outro card (5s) ekle
7. CompositeVideoClip ile birleştir
8. FFmpeg export

### 18.7 YouTube Yükleme

- **Playlist**: "Weekly Deep Dives" (yoksa oluştur)
- **Kategori**: 28 (Science & Technology)
- **made_for_kids**: False
- **Tags**: `["ev", "electric car", "Evcarix", "long form", "deep dive"]`

### 18.8 main.py Routing

```python
upload_slot = os.getenv("UPLOAD_SLOT", "evening")

if upload_slot == "SUNDAY_LONG":
    asyncio.run(orchestrator.run_weekly_long_video_workflow())
else:
    asyncio.run(orchestrator.run_daily_shorts_workflow())
```

### 18.9 run_weekly_long_video_workflow()

**Adımlar:**

1. **Plan**: 67 konu havuzundan seçim, trend modu support
2. **AI Video**: clip_count = ceil(target_duration / 8)
3. **Stock Video**: orientation="landscape", daha fazla klip
4. **Seslendirme**: Erkek ses, normal hız
5. **Montaj**: 1920x1080, title + content + outro
6. **Yükleme**: Weekly Deep Dives playlist

### 18.10 Clip Sayısı Hesaplama

```
target_duration = random.randint(240, 360)  # 4-6 dakika
clip_count = math.ceil(target_duration / 8)  # Her klip ~8 saniye

Örnek:
- 240 saniye → 30 klip
- 300 saniye → 38 klip
- 360 saniye → 45 klip
```

### 18.11 Video Kaynakları

Haftalık uzun video için daha fazla klip gerekir:
- AI video: Stability AI, Replicate, Kling
- Stock video: Pexels, Pixabay (landscape orientation)
- OEM Press Kit: Tesla, Lucid, Waymo
- NASA/DOE Public Videos

### 18.12 Fallback Mekanizmaları

Günlük Shorts ile aynı:
- AI video yoksa → Stock video
- Stok bitse → AI video + tekrar kullanım
- Version-safe loop implementation

### 18.13 Thumbnail Generation

**src/thumbnail_generator.py**:

- **Çıkış**: 1280x720 JPEG, quality 97
- **Design katmanları (alttan üste)**:
  1. Kategori gradient arka plan (koyu → daha koyu, 9 palet)
  2. Hafif grid overlay
  3. Yumuşak glow accent elipsler (kategori accent rengi)
  4. Sol accent bar (8px solid)
  5. Stat bloğu — büyük numara sağ taraf (örn: -50%, 800V, 1M KM)
  6. Başlık metni — büyük harf, max 3 satır, stroke shadow
  7. Data progress bar — alt dekoratif element
  8. Brand bar — EVCARIX + motto sol alt
  9. Kategori badge — sağ üst köşe pill
- **Font**: DejaVu Sans Bold (sistem) with fallback to default
- **Kategori paletleri**:
  - battery: #0D1B2A → #1A3A5C, accent #00D4FF
  - range: #0A1628 → #1C3D6E, accent #00FF88
  - charging: #1A0A00 → #4A1800, accent #FF6B00
  - ownership: #0D1A0D → #1A3D1A, accent #7FFF00
  - comparison: #1A0A2E → #3D1A6E, accent #BF00FF
  - market: #1A1200 → #4A3600, accent #FFD700
  - infrastructure: #001A1A → #004D4D, accent #00FFFF
  - education: #0D0D1A → #1A1A4D, accent #4488FF
  - tools: #1A000D → #4D0026, accent #FF0066

**Integration**:
- `run_weekly_long_video_workflow()`'de otomatik çağrılır
- Video montajından sonra, YouTube yüklemeden önce
- YouTube uploader'a thumbnail_path parametresi olarak geçilir
