
import sys
import os
import io
import random

# Türkçe karakterlerin düzgün çıkması için bunu eklemek zorunda kaldım
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import torch
import torchvision.transforms as transforms
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, BASE_DIR)
from src.models.unified_cnn import WheatAIUnifiedModel

INFER_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

TASK_META = {
    "disease": "HASTALIK TESPITI",
    "weed":    "YABANI OT TESPITI",
    "harvest": "HASAT OLGUNLUGU",
}


def sep(c="=", n=65):
    print(c * n, flush=True)

def log(msg=""):
    print(msg, flush=True)

def bar(pct, w=24):
    filled = int(pct / 100 * w)
    return "[" + "#" * filled + "-" * (w - filled) + "]"

def conf_tag(pct):
    if pct >= 80: return "YUKSEK"
    if pct >= 55: return "ORTA"
    return "DUSUK"


def load_model(use_best=False):
    if use_best:
        path = os.path.join(BASE_DIR, "wheat_ai_unified_best.pth")
        label = "EN IYI"
    else:
        path = os.path.join(BASE_DIR, "wheat_ai_unified_model.pth")
        label = "SON"

    if not os.path.exists(path):
        # istenen dosya yoksa diğerine bakıyorum
        alt = os.path.join(BASE_DIR,
              "wheat_ai_unified_best.pth" if not use_best else "wheat_ai_unified_model.pth")
        if os.path.exists(alt):
            path, label = alt, ("EN IYI" if not use_best else "SON")
        else:
            log(f"[HATA] Model bulunamadi: {path}")
            log("       Once egitimi tamamlayin:")
            log("       python src/scripts/train_unified.py")
            sys.exit(1)

    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = WheatAIUnifiedModel(
        num_disease_classes=ckpt["num_disease_classes"],
        num_weed_classes   =ckpt["num_weed_classes"],
        num_harvest_classes=ckpt["num_harvest_classes"],
    ).to(device)

    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    sep()
    log(f"  WHEAT AI - DEMO ({label} MODEL)")
    log(f"  Dosya  : {os.path.basename(path)}")
    log(f"  Donanim: {str(device).upper()}")

    if "val_accuracy" in ckpt:
        va = ckpt["val_accuracy"]
        log(f"  Val Acc: Disease=%{va['disease']:.1f}  "
            f"Weed=%{va['weed']:.1f}  Harvest=%{va['harvest']:.1f}")
    sep()

    return model, ckpt, device


def predict(model, img_path, device, ckpt):
    img    = Image.open(img_path).convert("RGB")
    tensor = INFER_TRANSFORM(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(tensor)

    results = {}
    for task, logits in outputs.items():
        probs       = torch.softmax(logits, dim=1).squeeze().cpu()
        conf, idx   = probs.max(dim=0)
        classes     = ckpt.get(f"{task}_classes",
                      [str(i) for i in range(logits.shape[1])])
        results[task] = {
            "label":     classes[idx.item()],
            "conf":      conf.item() * 100,
            "all_probs": {c: probs[i].item() * 100 for i, c in enumerate(classes)},
        }
    return results


def print_result(results, img_path):
    sep()
    log(f"  RESIM : {os.path.basename(img_path)}")
    sep()

    for task, res in results.items():
        conf  = res["conf"]
        label = res["label"]
        log(f"\n  >> {TASK_META[task]}")
        log(f"     Tahmin : {label}  (%{conf:.1f})  [{conf_tag(conf)}]")
        log(f"     Guven  : {bar(conf)} %{conf:.1f}")
        log()
        for cls, prob in sorted(res["all_probs"].items(), key=lambda x: -x[1]):
            marker = " <--" if cls == label else ""
            log(f"     {cls:<30s} {bar(prob, 20)} %{prob:5.1f}{marker}")

    sep("-")
    log("\n  OZET:")
    for task, res in results.items():
        log(f"    {TASK_META[task]:<25s}: {res['label']}  (%{res['conf']:.1f})")
    sep()
    log()


def test_folder(model, folder, device, ckpt, max_imgs=10):
    imgs = [os.path.join(folder, f) for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMG_EXTS]
    if not imgs:
        log(f"[UYARI] Klasorde resim yok: {folder}")
        return

    if len(imgs) > max_imgs:
        imgs = random.sample(imgs, max_imgs)
        log(f"  {max_imgs} rastgele resim secildi.\n")

    for p in imgs:
        try:
            print_result(predict(model, p, device, ckpt), p)
        except Exception as e:
            log(f"  [HATA] {os.path.basename(p)}: {e}")


def auto_test(model, device, ckpt, n=5):
    # dataset klasöründen rastgele resimler çekip tahmin yapıyorum
    samples = []

    harvest_dir = os.path.join(BASE_DIR, "datasets", "harvest")
    for cls in os.listdir(harvest_dir):
        p = os.path.join(harvest_dir, cls)
        if os.path.isdir(p):
            imgs = [f for f in os.listdir(p) if os.path.splitext(f)[1].lower() in IMG_EXTS]
            # augmented dosyaları test için kullanmıyorum
            real_imgs = [f for f in imgs if not f.startswith("aug_")]
            if not real_imgs:
                real_imgs = imgs
            if real_imgs:
                samples.append(("harvest", cls, os.path.join(p, random.choice(real_imgs))))

    disease_test = os.path.join(BASE_DIR, "datasets", "disease", "data", "test")
    if os.path.exists(disease_test):
        for cls in os.listdir(disease_test):
            p = os.path.join(disease_test, cls)
            if os.path.isdir(p):
                imgs = [f for f in os.listdir(p) if os.path.splitext(f)[1].lower() in IMG_EXTS]
                if imgs:
                    samples.append(("disease", cls, os.path.join(p, random.choice(imgs))))

    if not samples:
        log("[UYARI] Otomatik test icin dataset klasoru bulunamadi.")
        return

    random.shuffle(samples)
    samples = samples[:n]

    log(f"\n  Otomatik test: {len(samples)} resim\n")
    sep("-")

    correct = {"disease": [0, 0], "weed": [0, 0], "harvest": [0, 0]}

    for task, true_cls, img_path in samples:
        try:
            res     = predict(model, img_path, device, ckpt)
            pred    = res[task]["label"]
            conf    = res[task]["conf"]
            true_cls_norm = true_cls.lower().replace(" ", "_")
            if true_cls_norm.endswith("_test"):
                true_cls_norm = true_cls_norm[:-5]
            is_ok   = pred.lower().replace(" ", "_") == true_cls_norm
            status  = "OK    " if is_ok else "YANLIS"
            correct[task][1] += 1
            if is_ok:
                correct[task][0] += 1

            log(f"  [{status}] {task:<9} | Gercek: {true_cls:<22} | "
                f"Tahmin: {pred:<22} | %{conf:.1f}")
        except Exception as e:
            log(f"  [HATA] {os.path.basename(img_path)}: {e}")

    sep("-")
    log("\n  MINI TEST SONUCU:")
    for task in ["disease", "weed", "harvest"]:
        c, t = correct[task]
        if t > 0:
            log(f"    {task:<10}: {c}/{t}  (%{100*c/t:.0f})")
    sep()


def main():
    use_best = "--best" in sys.argv
    args     = [a for a in sys.argv[1:] if not a.startswith("--")]

    model, ckpt, device = load_model(use_best=use_best)

    if not args:
        log("\n  Mod: OTOMATIK DATASET TESTI")
        log("  Kullanim: demo_unified.py resim.jpg | klasor/ | --best\n")
        auto_test(model, device, ckpt, n=5)

    elif os.path.isdir(args[0]):
        log(f"\n  Mod: KLASOR TESTI -> {args[0]}")
        test_folder(model, args[0], device, ckpt, max_imgs=10)

    elif os.path.isfile(args[0]):
        log(f"\n  Mod: TEK RESIM -> {args[0]}")
        print_result(predict(model, args[0], device, ckpt), args[0])

    else:
        log(f"[HATA] Bulunamadi: {args[0]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
