import io
import os
import sys
import asyncio
import logging
import torch
import torchvision.transforms as transforms
from PIL import Image
import pickle
import pandas as pd
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

# logları bir yere yazmak lazım, bunu hocam söylemişti zaten
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("agrovision")

# maksimum dosya boyutu 10 MB yaptım, daha büyük gelirse reddeder
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from src.models.unified_cnn import WheatAIUnifiedModel

# Gemini API anahtarını .env dosyasından okuyorum
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_model   = None
_gemini_cache  = {}  # aynı hastalığı tekrar tekrar sormamak için cache

if GEMINI_API_KEY and GEMINI_API_KEY != "BURAYA_API_KEY_YAZI":
    try:
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
        gemini_model  = _genai_client.models
        logger.info("Gemini API bağlantısı kuruldu.")
    except Exception as e:
        logger.warning("Gemini başlatılamadı: %s", e)
else:
    logger.warning("GEMINI_API_KEY bulunamadı. Tedavi önerileri için sabit harita kullanılacak.")


async def get_gemini_treatment(disease_en: str, disease_tr: str) -> str:
    # önce cache'e baktım, daha önce sorduysam tekrar sormuyorum
    if disease_en in _gemini_cache:
        return _gemini_cache[disease_en]

    if gemini_model is None:
        return TREATMENT_MAP.get(disease_en, "Lütfen bir tarım uzmanına danışın.")

    prompt = (
        f"Buğday bitkisinde '{disease_tr}' hastalığı tespit edildi. "
        f"Bir tarım uzmanı olarak Türkçe, 2-3 cümlelik pratik bir tedavi ve ilaç önerisi yaz. "
        f"Önerilen ilaç isimlerini ve uygulama zamanını belirt. Sadece öneriyi yaz, başka açıklama yapma."
    )

    try:
        # Gemini çağrısı blocking, bunu thread'e atarak event loop'u bloke etmiyorum
        response = await asyncio.to_thread(
            gemini_model.generate_content,
            model="gemini-1.5-flash",
            contents=prompt,
        )
        text = response.text.strip()
        _gemini_cache[disease_en] = text
        logger.info("Gemini tedavi önerisi alındı: %s", disease_en)
        return text
    except Exception as e:
        logger.warning("Gemini API hatası (%s): %s", disease_en, e)
        fallback = TREATMENT_MAP.get(disease_en, "Lütfen bir tarım uzmanına danışın.")
        _gemini_cache[disease_en] = fallback
        return fallback


# Türkçe karşılıkları burada tutuyorum, frontend'e hep Türkçe gönderiyorum
DISEASE_TR = {
    "Healthy":              "Sağlıklı",
    "Aphid":               "Yaprak Biti",
    "Black Rust":          "Siyah Pas",
    "Brown Rust":          "Kahverengi Pas",
    "Yellow Rust":         "Sarı Pas",
    "Blast":               "Yanıklık",
    "Common Root Rot":     "Kök Çürüklüğü",
    "Fusarium Head Blight":"Başak Yanıklığı (Fusarium)",
    "Leaf Blight":         "Yaprak Yanıklığı",
    "Mildew":              "Külleme",
    "Mite":                "Kırmızı Örümcek (Akar)",
    "Septoria":            "Septoria Yaprak Lekesi",
    "Smut":                "Rastık (Sürme)",
    "Stem fly":            "Sap Sineği",
    "Tan spot":            "Kahverengi Leke",
}

HARVEST_TR = {
    "Mature":   "Hasat Olgunluğunda",
    "Unripe":   "Henüz Olgunlaşmadı",
    "Seedling": "Fide Dönemi",
}

WEED_TR = {
    "Weed":   "Yabani Ot Var",
    "Weeds":  "Yabani Ot Var",
    "weed":   "Yabani Ot Var",
    "Wheat":  "Yabani Ot Yok",
    "Wheats": "Yabani Ot Yok",
    "wheat":  "Yabani Ot Yok",
}

def get_weed_tr(label: str) -> str:
    # bazen label büyük-küçük harf farklı geliyor, o yüzden esnek bir kontrol yaptım
    if label in WEED_TR:
        return WEED_TR[label]
    lower = label.strip().lower()
    if "wheat" in lower:
        return "Yabani Ot Yok"
    if "weed" in lower:
        return "Yabani Ot Var"
    return label

# Gemini yokken veya hata verirse bu statik önerilere dönüyorum
TREATMENT_MAP = {
    "Aphid":               "Yaprak bitine karşı insektisit uygulaması önerilir. Acetamiprid veya Imidacloprid etken maddeli ilaçlar kullanılabilir.",
    "Black Rust":          "Siyah pasa karşı fungisit uygulaması gereklidir. Tebuconazole veya Propiconazole içeren ilaçlar kullanılabilir.",
    "Brown Rust":          "Kahverengi pasa karşı fungisit uygulaması gereklidir. Tebuconazole veya Propiconazole içeren ilaçlar kullanılabilir.",
    "Yellow Rust":         "Sarı pasa karşı erken dönemde fungisit (Azoxystrobin, Tebuconazole) uygulaması şarttır.",
    "Blast":               "Yanıklığa karşı fungisit (Tricyclazole veya Isoprothiolane) uygulaması önerilir.",
    "Common Root Rot":     "Kök çürüklüğüne karşı tohum ilaçlaması ve uygun drenaj önemlidir. Triazole grubu fungisitler kullanılabilir.",
    "Fusarium Head Blight":"Başak yanıklığına karşı çiçeklenme döneminde Tebuconazole veya Prothioconazole içeren fungisitler ile koruyucu ilaçlama yapılmalıdır.",
    "Leaf Blight":         "Yaprak yanıklığına karşı geniş spektrumlu fungisitler (Mancozeb, Chlorothalonil) kullanılmalıdır.",
    "Mildew":              "Küllemeye karşı kükürt bazlı veya sistemik fungisitler (Myclobutanil, Penconazole) önerilir.",
    "Mite":                "Kırmızı örümceğe karşı akarisit (Abamectin veya Spirodiclofen) uygulaması yapılmalıdır.",
    "Septoria":            "Septoria lekesine karşı fungisit (Chlorothalonil veya Pyraclostrobin) uygulaması önerilir.",
    "Smut":                "Rastık hastalığına karşı sistemik tohum ilaçları (Carboxin, Tebuconazole) kullanımı en etkili yöntemdir.",
    "Stem fly":            "Sap sineğine karşı sistemik insektisitler (Dimethoate veya Imidacloprid) ile ilaçlama yapılmalıdır.",
    "Tan spot":            "Kahverengi lekeye karşı hasat sonrası anız yönetimi ve fungisit (Propiconazole, Pyraclostrobin) uygulaması önerilir.",
}


class FertilizerRequest(BaseModel):
    temperature: float
    humidity: float
    moisture: float
    soil_type: str
    crop_type: str
    nitrogen: int
    potassium: int
    phosphorous: int


MODEL_PATH    = os.path.join(BASE_DIR, "wheat_ai_unified_best.pth")
FALLBACK_PATH = os.path.join(BASE_DIR, "wheat_ai_unified_model.pth")

# eğitimde kullandığım ImageNet normalizasyonunu burada da uyguluyorum
INFER_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

device     = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model      = None
checkpoint = None
fert_model = None
fert_encoders = {}


def load_model():
    global model, checkpoint, fert_model, fert_encoders

    # önce best modeli dene, yoksa son kaydedilen modele bak
    path = MODEL_PATH if os.path.exists(MODEL_PATH) else FALLBACK_PATH
    if not os.path.exists(path):
        logger.error("Model dosyası bulunamadı: %s", path)
        return

    checkpoint = torch.load(path, map_location=device, weights_only=False)
    model = WheatAIUnifiedModel(
        num_disease_classes=checkpoint["num_disease_classes"],
        num_weed_classes   =checkpoint["num_weed_classes"],
        num_harvest_classes=checkpoint["num_harvest_classes"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    logger.info("Model yüklendi: %s | Cihaz: %s", os.path.basename(path), device)

    if "val_accuracy" in checkpoint:
        va = checkpoint["val_accuracy"]
        logger.info(
            "Val Acc — Disease: %.1f%%  Weed: %.1f%%  Harvest: %.1f%%",
            va["disease"], va["weed"], va["harvest"],
        )

    # gübre modeli ayrı .pkl dosyasında, onu da burada yüklüyorum
    try:
        with open(os.path.join(BASE_DIR, "fertilizer_rf_model.pkl"), "rb") as f:
            fert_model = pickle.load(f)
        with open(os.path.join(BASE_DIR, "fert_crop_encoder.pkl"), "rb") as f:
            fert_encoders["crop"] = pickle.load(f)
        with open(os.path.join(BASE_DIR, "fert_soil_encoder.pkl"), "rb") as f:
            fert_encoders["soil"] = pickle.load(f)
        with open(os.path.join(BASE_DIR, "fert_label_encoder.pkl"), "rb") as f:
            fert_encoders["label"] = pickle.load(f)
        logger.info("Gübre modeli yüklendi.")
    except Exception as e:
        logger.warning("Gübre modeli yüklenemedi: %s", e)


@asynccontextmanager
async def lifespan(app):
    load_model()
    yield


app = FastAPI(
    title="AgroVision API",
    description="AgroVision — Buğday tarlası hastalık, yabani ot ve hasat analiz API",
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "app": "AgroVision API",
        "version": "1.1.0",
        "status": "online",
        "model_loaded": model is not None,
        "fertilizer_model_loaded": fert_model is not None,
        "gemini_active": gemini_model is not None,
        "device": str(device),
    }


@app.get("/api/model-info")
async def model_info():
    if model is None or checkpoint is None:
        raise HTTPException(status_code=503, detail="Model henüz yüklenmedi.")

    disease_classes = checkpoint.get(
        "disease_classes",
        [str(i) for i in range(checkpoint["num_disease_classes"])],
    )
    weed_classes = checkpoint.get("weed_classes", ["Weed", "Wheat"])
    harvest_classes = checkpoint.get("harvest_classes", ["Mature", "Seedling", "Unripe"])

    return {
        "model_file": os.path.basename(
            MODEL_PATH if os.path.exists(MODEL_PATH) else FALLBACK_PATH
        ),
        "device": str(device),
        "tasks": {
            "disease": {
                "num_classes": checkpoint["num_disease_classes"],
                "classes_en": disease_classes,
                "classes_tr": [DISEASE_TR.get(c, c) for c in disease_classes],
            },
            "weed": {
                "num_classes": checkpoint["num_weed_classes"],
                "classes_en": weed_classes,
                "classes_tr": [get_weed_tr(c) for c in weed_classes],
            },
            "harvest": {
                "num_classes": checkpoint["num_harvest_classes"],
                "classes_en": harvest_classes,
                "classes_tr": [HARVEST_TR.get(c, c) for c in harvest_classes],
            },
        },
        "val_accuracy": checkpoint.get("val_accuracy", {}),
    }


@app.post("/api/predict")
async def predict(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=503, detail="Model yüklenemedi.")

    # desteklenmeyen format gelirse hemen reddediyorum
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen format: {file.content_type}. "
                   f"Kabul edilenler: JPEG, PNG, WebP.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Dosya çok büyük ({len(contents) / 1024 / 1024:.1f} MB). "
                   f"Maksimum 10 MB yükleyebilirsiniz.",
        )

    logger.info(
        "Predict isteği — dosya: %s | format: %s | boyut: %.1f KB",
        file.filename, file.content_type, len(contents) / 1024,
    )

    try:
        img    = Image.open(io.BytesIO(contents)).convert("RGB")
        tensor = INFER_TRANSFORM(img).unsqueeze(0).to(device)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Görüntü okunamadı: {str(e)}")

    TASK_CLASSES = {
        "disease": checkpoint.get("disease_classes",
                   [str(i) for i in range(checkpoint["num_disease_classes"])]),
        "weed":    checkpoint.get("weed_classes",    ["Weed", "Wheat"]),
        "harvest": checkpoint.get("harvest_classes", ["Mature", "Seedling", "Unripe"]),
    }

    with torch.no_grad():
        outputs = model(tensor)

    result = {}
    for task, logits in outputs.items():
        probs     = torch.softmax(logits, dim=1).squeeze().cpu()
        conf, idx = torch.max(probs, dim=0)
        classes   = TASK_CLASSES[task]
        raw_label = classes[idx.item()]

        if task == "disease":
            label_tr = DISEASE_TR.get(raw_label, raw_label)
            all_probs_tr = {
                DISEASE_TR.get(cls, cls): round(probs[i].item() * 100, 2)
                for i, cls in enumerate(classes)
            }
        elif task == "harvest":
            label_tr = HARVEST_TR.get(raw_label, raw_label)
            all_probs_tr = {
                HARVEST_TR.get(cls, cls): round(probs[i].item() * 100, 2)
                for i, cls in enumerate(classes)
            }
        elif task == "weed":
            label_tr = get_weed_tr(raw_label)
            all_probs_tr = {
                get_weed_tr(cls): round(probs[i].item() * 100, 2)
                for i, cls in enumerate(classes)
            }
        else:
            label_tr = raw_label
            all_probs_tr = {
                cls: round(probs[i].item() * 100, 2)
                for i, cls in enumerate(classes)
            }

        result[task] = {
            "label":      raw_label,
            "label_tr":   label_tr,
            "confidence": round(conf.item() * 100, 2),
            "all_probs":  all_probs_tr,
        }

        # sağlıklı değilse tedavi önerisi de ekliyorum
        if task == "disease" and raw_label != "Healthy":
            result[task]["treatment"] = await get_gemini_treatment(raw_label, label_tr)

    # sonuçları birleştirip kullanıcıya anlamlı bir özet mesajı hazırlıyorum
    disease_lbl  = result["disease"]["label"]
    harvest_lbl  = result.get("harvest", {}).get("label", "")
    has_weed     = result.get("weed", {}).get("label_tr") == "Yabani Ot Var"

    is_healthy = disease_lbl == "Healthy"
    is_mature  = harvest_lbl == "Mature"

    weed_warning = " (⚠️ Tarlada yabani ot tespit edildi, temizlenmesi önerilir)" if has_weed else ""

    if is_healthy:
        if is_mature:
            summary = f"✅ Bitki Sağlıklı — Hasat Zamanı!{weed_warning}"
        else:
            harvest_tr = result.get("harvest", {}).get("label_tr", "")
            summary = f"✅ Bitki Sağlıklı — {harvest_tr}, Daha Hasat Vakti Değil.{weed_warning}"
    else:
        disease_tr = result["disease"]["label_tr"]
        treatment  = result["disease"].get("treatment", "")
        summary    = f"⚠️ Hastalık Tespit Edildi: {disease_tr}.\n{treatment}\n{weed_warning}".strip()

    result["summary"]     = summary
    result["gemini_used"] = gemini_model is not None
    return result


@app.post("/api/predict/batch")
async def predict_batch(files: List[UploadFile] = File(...)):
    """Birden fazla görüntüyü aynı anda analiz eder (max 10 dosya)."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model yüklenemedi.")

    MAX_BATCH = 10
    if len(files) > MAX_BATCH:
        raise HTTPException(
            status_code=400,
            detail=f"En fazla {MAX_BATCH} fotoğraf yükleyebilirsiniz. Gönderilen: {len(files)}",
        )
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="En az bir dosya göndermelisiniz.")

    async def _process_one(upload: UploadFile) -> dict:
        """Tek bir dosyayı işle, hata varsa error anahtarı ile dön."""
        try:
            if upload.content_type not in ALLOWED_TYPES:
                return {
                    "filename": upload.filename,
                    "error": f"Desteklenmeyen format: {upload.content_type}",
                }

            contents = await upload.read()
            if len(contents) > MAX_FILE_SIZE:
                return {
                    "filename": upload.filename,
                    "error": f"Dosya çok büyük ({len(contents)/1024/1024:.1f} MB). Maks. 10 MB.",
                }

            img    = Image.open(io.BytesIO(contents)).convert("RGB")
            tensor = INFER_TRANSFORM(img).unsqueeze(0).to(device)

            TASK_CLASSES = {
                "disease": checkpoint.get("disease_classes",
                           [str(i) for i in range(checkpoint["num_disease_classes"])]),
                "weed":    checkpoint.get("weed_classes",    ["Weed", "Wheat"]),
                "harvest": checkpoint.get("harvest_classes", ["Mature", "Seedling", "Unripe"]),
            }

            with torch.no_grad():
                outputs = model(tensor)

            result = {}
            for task, logits in outputs.items():
                probs     = torch.softmax(logits, dim=1).squeeze().cpu()
                conf, idx = torch.max(probs, dim=0)
                classes   = TASK_CLASSES[task]
                raw_label = classes[idx.item()]

                if task == "disease":
                    label_tr     = DISEASE_TR.get(raw_label, raw_label)
                    all_probs_tr = {DISEASE_TR.get(cls, cls): round(probs[i].item()*100, 2) for i, cls in enumerate(classes)}
                elif task == "harvest":
                    label_tr     = HARVEST_TR.get(raw_label, raw_label)
                    all_probs_tr = {HARVEST_TR.get(cls, cls): round(probs[i].item()*100, 2) for i, cls in enumerate(classes)}
                elif task == "weed":
                    label_tr     = get_weed_tr(raw_label)
                    all_probs_tr = {get_weed_tr(cls): round(probs[i].item()*100, 2) for i, cls in enumerate(classes)}
                else:
                    label_tr     = raw_label
                    all_probs_tr = {cls: round(probs[i].item()*100, 2) for i, cls in enumerate(classes)}

                result[task] = {
                    "label":      raw_label,
                    "label_tr":   label_tr,
                    "confidence": round(conf.item()*100, 2),
                    "all_probs":  all_probs_tr,
                }

                if task == "disease" and raw_label != "Healthy":
                    result[task]["treatment"] = await get_gemini_treatment(raw_label, label_tr)

            disease_lbl = result["disease"]["label"]
            harvest_lbl = result.get("harvest", {}).get("label", "")
            has_weed    = result.get("weed", {}).get("label_tr") == "Yabani Ot Var"
            is_healthy  = disease_lbl == "Healthy"
            is_mature   = harvest_lbl == "Mature"
            weed_warn   = " (⚠️ Tarlada yabani ot tespit edildi)" if has_weed else ""

            if is_healthy:
                harvest_tr = result.get("harvest", {}).get("label_tr", "")
                summary = (f"✅ Sağlıklı — Hasat Zamanı!{weed_warn}" if is_mature
                           else f"✅ Sağlıklı — {harvest_tr}{weed_warn}")
            else:
                disease_tr = result["disease"]["label_tr"]
                treatment  = result["disease"].get("treatment", "")
                summary    = f"⚠️ {disease_tr}.\n{treatment}{weed_warn}".strip()

            result["summary"]     = summary
            result["gemini_used"] = gemini_model is not None
            return {"filename": upload.filename, "result": result}

        except Exception as e:
            logger.warning("Batch işlemi hatası (%s): %s", upload.filename, e)
            return {"filename": upload.filename, "error": str(e)}

    logger.info("Batch predict isteği — %d dosya", len(files))
    items = await asyncio.gather(*[_process_one(f) for f in files])
    return {"count": len(items), "results": list(items)}


@app.post("/api/recommend_fertilizer")
async def recommend_fertilizer(req: FertilizerRequest):
    if fert_model is None:
        raise HTTPException(status_code=503, detail="Gübre modeli yüklenemedi.")

    try:
        crop_enc = fert_encoders["crop"].transform([req.crop_type])[0]
        soil_enc = fert_encoders["soil"].transform([req.soil_type])[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Geçersiz ürün veya toprak tipi: {str(e)}")

    input_data = pd.DataFrame([[
        req.temperature, req.humidity, req.moisture,
        soil_enc, crop_enc,
        req.nitrogen, req.potassium, req.phosphorous,
    ]], columns=[
        "Temparature", "Humidity", "Moisture",
        "Soil Type", "Crop Type",
        "Nitrogen", "Potassium", "Phosphorous",
    ])

    try:
        pred = fert_model.predict(input_data)
        recommended = fert_encoders["label"].inverse_transform(pred)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tahmin sırasında hata: {str(e)}")

    logger.info("Gübre önerisi: %s", recommended)
    return {"recommended_fertilizer": str(recommended)}


# React build varsa statik dosyaları serve ediyorum
DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")
if not os.path.exists(DIST_DIR):
    # Eğer sunucudaki gibi dist direkt ana dizindeyse
    DIST_DIR = os.path.join(BASE_DIR, "dist")

if os.path.exists(DIST_DIR) and os.path.exists(os.path.join(DIST_DIR, "index.html")):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react(full_path: str):
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
else:
    logger.warning("React dist klasörü (frontend/dist veya dist) bulunamadı. Önce 'npm run build' çalıştırın.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
