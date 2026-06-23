import os
import io
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def app_with_mocked_model():
    # 95 MB'lık model dosyası olmadan test çalıştırabilmek için modeli mock'luyorum
    mock_checkpoint = {
        "num_disease_classes": 15,
        "num_weed_classes": 2,
        "num_harvest_classes": 3,
        "disease_classes": [
            "Healthy", "Aphid", "Black Rust", "Brown Rust", "Yellow Rust",
            "Blast", "Common Root Rot", "Fusarium Head Blight", "Leaf Blight",
            "Mildew", "Mite", "Septoria", "Smut", "Stem fly", "Tan spot",
        ],
        "weed_classes": ["Weed", "Wheat"],
        "harvest_classes": ["Mature", "Seedling", "Unripe"],
        "val_accuracy": {"disease": 92.5, "weed": 97.1, "harvest": 89.3},
    }

    with patch("torch.load", return_value=mock_checkpoint), \
         patch("src.models.unified_cnn.WheatAIUnifiedModel") as MockModel:

        mock_model_instance = MagicMock()
        mock_model_instance.eval.return_value = mock_model_instance
        mock_model_instance.to.return_value = mock_model_instance
        MockModel.return_value = mock_model_instance

        import api as api_module
        api_module.model = mock_model_instance
        api_module.checkpoint = mock_checkpoint

        yield api_module.app


@pytest.fixture()
def minimal_jpeg() -> bytes:
    # gerçek dosya olmadan test geçebilmek için 1x1 JPEG üretiyorum
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(100, 150, 200)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_health_returns_200(app_with_mocked_model):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_mocked_model), base_url="http://test"
    ) as client:
        resp = await client.get("/api/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "online"
    assert body["app"] == "AgroVision API"


@pytest.mark.asyncio
async def test_health_model_loaded(app_with_mocked_model):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_mocked_model), base_url="http://test"
    ) as client:
        resp = await client.get("/api/health")

    assert resp.json()["model_loaded"] is True


@pytest.mark.asyncio
async def test_predict_rejects_non_image(app_with_mocked_model):
    # PDF geldiğinde 400 dönmeli, bunu kontrol ediyorum
    async with AsyncClient(
        transport=ASGITransport(app=app_with_mocked_model), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/predict",
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_predict_returns_three_tasks(app_with_mocked_model, minimal_jpeg):
    # geçerli JPEG'de disease, weed, harvest anahtarları dönmeli
    import torch

    fake_outputs = {
        "disease": torch.zeros(1, 15),
        "weed":    torch.zeros(1, 2),
        "harvest": torch.zeros(1, 3),
    }
    app_with_mocked_model.state

    import api as api_module
    api_module.model.return_value = fake_outputs

    with patch("api.get_gemini_treatment", new=AsyncMock(return_value="Mock tedavi önerisi.")):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mocked_model), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/predict",
                files={"file": ("field.jpg", minimal_jpeg, "image/jpeg")},
            )

    assert resp.status_code == 200
    body = resp.json()
    for key in ("disease", "weed", "harvest", "summary"):
        assert key in body, f"Yanıtta '{key}' anahtarı eksik"


@pytest.mark.asyncio
async def test_predict_result_structure(app_with_mocked_model, minimal_jpeg):
    import torch

    fake_outputs = {
        "disease": torch.zeros(1, 15),
        "weed":    torch.zeros(1, 2),
        "harvest": torch.zeros(1, 3),
    }

    import api as api_module
    api_module.model.return_value = fake_outputs

    with patch("api.get_gemini_treatment", new=AsyncMock(return_value="Mock tedavi.")):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mocked_model), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/predict",
                files={"file": ("field.jpg", minimal_jpeg, "image/jpeg")},
            )

    body = resp.json()
    for task in ("disease", "weed", "harvest"):
        task_obj = body[task]
        assert "label" in task_obj
        assert "label_tr" in task_obj
        assert "confidence" in task_obj
        assert "all_probs" in task_obj
        assert isinstance(task_obj["confidence"], float)


@pytest.mark.asyncio
async def test_fertilizer_no_model_returns_503(app_with_mocked_model):
    # gübre modeli yokken 503 dönmeli
    import api as api_module
    original = api_module.fert_model
    api_module.fert_model = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mocked_model), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/recommend_fertilizer",
                json={
                    "temperature": 25.0, "humidity": 60.0, "moisture": 40.0,
                    "soil_type": "Sandy", "crop_type": "Wheat",
                    "nitrogen": 30, "potassium": 20, "phosphorous": 15,
                },
            )
        assert resp.status_code == 503
    finally:
        api_module.fert_model = original


@pytest.mark.asyncio
async def test_fertilizer_with_mock_model(app_with_mocked_model):
    import api as api_module

    mock_fert = MagicMock()
    mock_fert.predict.return_value = ["Urea"]

    mock_label_enc = MagicMock()
    mock_label_enc.inverse_transform.return_value = ["Urea"]

    mock_crop_enc = MagicMock()
    mock_crop_enc.transform.return_value = [1]

    mock_soil_enc = MagicMock()
    mock_soil_enc.transform.return_value = [0]

    original_fert   = api_module.fert_model
    original_encs   = api_module.fert_encoders.copy()

    api_module.fert_model    = mock_fert
    api_module.fert_encoders = {
        "crop":  mock_crop_enc,
        "soil":  mock_soil_enc,
        "label": mock_label_enc,
    }

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mocked_model), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/recommend_fertilizer",
                json={
                    "temperature": 25.0, "humidity": 60.0, "moisture": 40.0,
                    "soil_type": "Sandy", "crop_type": "Wheat",
                    "nitrogen": 30, "potassium": 20, "phosphorous": 15,
                },
            )
        assert resp.status_code == 200
        assert "recommended_fertilizer" in resp.json()
        assert resp.json()["recommended_fertilizer"] == "Urea"
    finally:
        api_module.fert_model    = original_fert
        api_module.fert_encoders = original_encs


@pytest.mark.asyncio
async def test_gemini_fallback_when_no_api_key():
    # Gemini yokken statik TREATMENT_MAP'ten öneri gelmeli
    import api as api_module
    original_gemini = api_module.gemini_model
    api_module.gemini_model = None

    try:
        result = await api_module.get_gemini_treatment("Aphid", "Yaprak Biti")
        assert "insektisit" in result.lower() or len(result) > 10
    finally:
        api_module.gemini_model = original_gemini
