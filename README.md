# AgroVision

**Yapay zeka destekli buğday tarlası analiz platformu**

---

## Proje Hakkında

AgroVision, tarla fotoğraflarından anlık karar desteği üreten bir web uygulamasıdır. Tek bir görüntüden hastalık tespiti, yabani ot analizi ve hasat olgunluğu tahmini yaparak sonuçları Gemini AI destekli açıklamalar ve indirilebilir PDF raporuyla sunar.

---

## Özellikler

| Özellik | Açıklama |
|---|---|
| Görüntü Analizi | JPG/PNG yükleyerek 3 farklı AI modeliyle eş zamanlı analiz |
| Gemini AI Yorumu | Google Gemini API üzerinden detaylı hastalık ve tedavi açıklaması |
| Harita Entegrasyonu | Leaflet.js ile tarla konumu seçimi ve etiketleme |
| PDF Raporu | Analiz sonuçlarının tek tıkla indirilebilir raporu |
| Gübre Tavsiyesi | Toprak değerlerine göre Random Forest tabanlı gübre önerisi |
| Docker Desteği | Ortam farkı olmadan tek komutla çalıştırma |

---

## Mimari

```
agrovision/
├── api.py                         # FastAPI uygulama giriş noktası
├── requirements.txt
├── Dockerfile
├── .env.example
│
├── src/
│   ├── models/
│   │   └── unified_cnn.py         # WheatAI Unified CNN tanımı
│   └── scripts/
│       ├── train_unified.py       # Model eğitim scripti
│       └── predict_unified.py     # Çıkarım (inference) scripti
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── config.js              # API endpoint yapılandırması
│   │   └── components/
│   │       ├── UploadZone.jsx
│   │       ├── ResultCard.jsx
│   │       ├── MapPicker.jsx
│   │       ├── FertilizerForm.jsx
│   │       ├── SummaryPanel.jsx
│   │       └── ReportButton.jsx
│   └── package.json
│
├── wheat_ai_unified_best.pth      # Eğitilmiş PyTorch ağırlıkları
├── fertilizer_rf_model.pkl        # Gübre öneri modeli
└── fert_*.pkl                     # Yardımcı model dosyaları
```

### Teknoloji Yığını

**Backend** — FastAPI · PyTorch · Google Gemini API · Scikit-learn · Uvicorn

**Frontend** — React 18 · Vite · Leaflet.js · CSS Modules

**Altyapı** — Docker · Google Cloud VM

---

## Kurulum

### Gereksinimler

- Python 3.11+
- Node.js 18+
- Docker _(opsiyonel)_

### 1. Repoyu klonla

```bash
git clone https://github.com/cihankocc/agrovision.git
cd agrovision
```

### 2. Ortam değişkenlerini ayarla

```bash
cp .env.example .env
```

`.env` dosyasını açıp `GEMINI_API_KEY` değerini doldur.

| Değişken | Açıklama | Zorunlu |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API anahtarı | Evet |

### 3a. Docker ile çalıştır (önerilen)

```bash
docker build -t agrovision .
docker run -p 8000:8000 --env-file .env agrovision
```

### 3b. Manuel kurulum

**Backend:**

```bash
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000
```

**Frontend — geliştirme:**

```bash
cd frontend
npm install
npm run dev
```

**Frontend — production:**

```bash
cd frontend
npm install
npm run build
# dist/ klasörü backend tarafından otomatik servis edilir
```

---

## Kullanım

1. `http://localhost:8000` adresini tarayıcıda aç.
2. İsteğe bağlı olarak haritadan tarla konumunu seç.
3. Tarla fotoğrafını yükle (JPG veya PNG, maks. 10 MB).
4. **Analizi Başlat** butonuna bas.
5. Sonuçları incele; PDF raporu indir.

---

## API Referansı

| Method | Endpoint | Açıklama |
|---|---|---|
| `POST` | `/predict` | Görüntü analizi |
| `POST` | `/predict-fertilizer` | Gübre tavsiyesi |
| `GET` | `/health` | Servis durum kontrolü |

---

## Katkı

1. Repoyu fork'la.
2. Feature branch oluştur: `git checkout -b feature/ozellik-adi`
3. Değişiklikleri commit et: `git commit -m 'feat: kısa açıklama'`
4. Branch'i push et: `git push origin feature/ozellik-adi`
5. Pull Request aç.

---

## Lisans

MIT — ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.
