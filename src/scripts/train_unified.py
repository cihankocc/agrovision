
import sys
import os
import io
import time

# Windows'ta Türkçe karakterler bazen bozuluyor, bunu düzeltmek için ekledim
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split, Dataset
from torchvision import datasets, transforms
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, BASE_DIR)
from src.models.unified_cnn import WheatAIUnifiedModel


# eğitim parametreleri
EPOCHS      = 25
BATCH       = 32
LR_BACK     = 5e-5    # backbone için daha küçük lr
LR_HEAD     = 5e-4    # head katmanları daha hızlı öğrensin
UNFREEZE_EP = 10      # 10. epoch'ta backbone'u açıyorum
WEIGHTS     = {"disease": 1.0, "weed": 0.8, "harvest": 1.5}
# harvest weight'ini yüksek tutuyorum çünkü o veri seti daha az


TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomVerticalFlip(p=0.3),
    transforms.RandomRotation(25),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.25, hue=0.08),
    transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.85, 1.15)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

VAL_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


class TransformSubset(Dataset):
    # random_split sonrası val kısmına train augmentation uygulanmaması için bunu yazdım
    def __init__(self, subset, transform):
        self.subset    = subset
        self.transform = transform

    def __len__(self):
        return len(self.subset)

    def __getitem__(self, idx):
        real_idx      = self.subset.indices[idx]
        path, label   = self.subset.dataset.samples[real_idx]
        img           = Image.open(path).convert("RGB")
        return self.transform(img), label


def sep(c="=", n=68):
    print(c * n, flush=True)

def log(msg=""):
    print(msg, flush=True)

def inf_iter(loader):
    # loader bitince başa dönüyor, böylece tüm task'lar senkronize çalışıyor
    while True:
        for batch in loader:
            yield batch


def load_datasets():
    disease_dir = os.path.join(BASE_DIR, "datasets", "disease", "data")
    weed_dir    = os.path.join(BASE_DIR, "datasets", "weed",
                               "Combined Data set of all weeks", "Combined")
    harvest_dir = os.path.join(BASE_DIR, "datasets", "harvest")

    # disease'in kendi train/valid klasörü var
    dis_train = datasets.ImageFolder(
        os.path.join(disease_dir, "train"), transform=TRAIN_TRANSFORM)
    val_path = os.path.join(disease_dir, "valid")
    if not os.path.exists(val_path):
        val_path = os.path.join(disease_dir, "test")
    dis_val = datasets.ImageFolder(val_path, transform=VAL_TRANSFORM)

    # weed ve harvest için %80/%20 bölüyorum
    weed_full = datasets.ImageFolder(weed_dir, transform=TRAIN_TRANSFORM)
    wt = int(0.80 * len(weed_full))
    wv = len(weed_full) - wt
    weed_tr, weed_vr = random_split(
        weed_full, [wt, wv], generator=torch.Generator().manual_seed(42))
    weed_val = TransformSubset(weed_vr, VAL_TRANSFORM)

    harv_full = datasets.ImageFolder(harvest_dir, transform=TRAIN_TRANSFORM)
    ht = int(0.80 * len(harv_full))
    hv = len(harv_full) - ht
    harv_tr, harv_vr = random_split(
        harv_full, [ht, hv], generator=torch.Generator().manual_seed(42))
    harv_val = TransformSubset(harv_vr, VAL_TRANSFORM)

    def dl(ds, bs, shuf):
        return DataLoader(ds, batch_size=bs, shuffle=shuf,
                          num_workers=0, pin_memory=True)

    return {
        "disease": {
            "train": dl(dis_train, BATCH, True),
            "val":   dl(dis_val,   BATCH, False),
            "num_classes": len(dis_train.classes),
            "classes":     dis_train.classes,
            "train_size":  len(dis_train),
            "val_size":    len(dis_val),
        },
        "weed": {
            "train": dl(weed_tr,  BATCH, True),
            "val":   dl(weed_val, BATCH, False),
            "num_classes": len(weed_full.classes),
            "classes":     weed_full.classes,
            "train_size":  wt,
            "val_size":    wv,
        },
        "harvest": {
            "train": dl(harv_tr,  BATCH, True),
            "val":   dl(harv_val, BATCH, False),
            "num_classes": len(harv_full.classes),
            "classes":     harv_full.classes,
            "train_size":  ht,
            "val_size":    hv,
        },
    }


@torch.no_grad()
def evaluate(model, loaders, device):
    model.eval()
    results = {}
    for task in ["disease", "weed", "harvest"]:
        correct, total = 0, 0
        for imgs, lbls in loaders[task]["val"]:
            imgs = imgs.to(device, non_blocking=True)
            lbls = lbls.to(device, non_blocking=True)
            preds = model(imgs)[task].argmax(dim=1)
            correct += (preds == lbls).sum().item()
            total   += lbls.size(0)
        results[task] = 100.0 * correct / total if total > 0 else 0.0
    model.train()
    return results


def main():
    model_path      = os.path.join(BASE_DIR, "wheat_ai_unified_model.pth")
    best_model_path = os.path.join(BASE_DIR, "wheat_ai_unified_best.pth")

    sep()
    log("  WHEAT AI - UNIFIED MULTI-TASK TRAINING  (v3 FIXED)")
    log("  ResNet50 | Disease-15 | Weed-2 | Harvest-3")
    sep()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log(f"  Donanim : {str(device).upper()}")

    log("\n[1/4] Datasetler yukleniyor...")
    loaders = load_datasets()

    sep("-")
    for task in ["disease", "weed", "harvest"]:
        L = loaders[task]
        log(f"  {task:<9}: {L['train_size']:>6} egitim | "
            f"{L['val_size']:>5} val | {L['num_classes']} sinif")
    sep("-")

    log(f"\n[2/4] Model olusturuluyor...")
    log(f"  Epoch={EPOCHS}  LR_back={LR_BACK}  LR_head={LR_HEAD}")
    log(f"  Task weights: {WEIGHTS}")
    log(f"  Backbone unfreeze: Epoch {UNFREEZE_EP}'den itibaren")

    model = WheatAIUnifiedModel(
        num_disease_classes=loaders["disease"]["num_classes"],
        num_weed_classes   =loaders["weed"]["num_classes"],
        num_harvest_classes=loaders["harvest"]["num_classes"],
    ).to(device)

    criterion = nn.CrossEntropyLoss()

    backbone_params = [p for n, p in model.named_parameters()
                       if "backbone" in n and p.requires_grad]
    head_params     = [p for n, p in model.named_parameters()
                       if "backbone" not in n]

    # backbone ve head için farklı lr kullanıyorum
    optimizer = optim.AdamW([
        {"params": backbone_params, "lr": LR_BACK,  "weight_decay": 1e-4},
        {"params": head_params,     "lr": LR_HEAD,  "weight_decay": 1e-4},
    ])
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    # AMP sadece GPU'da çalışıyor
    use_amp = device.type == "cuda"
    scaler  = torch.amp.GradScaler("cuda") if use_amp else None

    log("\n[3/4] Egitim basliyor...\n")
    sep()

    history   = []
    best_val  = 0.0
    start_all = time.time()

    for epoch in range(EPOCHS):
        model.train()
        epoch_start = time.time()

        # backbone unfreeze zamanı geldi mi?
        if epoch == UNFREEZE_EP:
            model.unfreeze_all()
            optimizer.param_groups[0]["params"] = [
                p for n, p in model.named_parameters() if "backbone" in n
            ]
            log(f"  [!] Epoch {epoch+1}: Backbone tamamen acildi (fine-tuning basladi)")

        d_it = inf_iter(loaders["disease"]["train"])
        w_it = inf_iter(loaders["weed"]["train"])
        h_it = inf_iter(loaders["harvest"]["train"])

        # en uzun loader kadar adım atıyorum
        steps = max(
            len(loaders["disease"]["train"]),
            len(loaders["weed"]["train"]),
            len(loaders["harvest"]["train"]),
        )

        loss_sum = {"disease": 0.0, "weed": 0.0, "harvest": 0.0, "total": 0.0}

        log(f"Epoch {epoch+1:02d}/{EPOCHS}  ({steps} adim)")

        for step in range(steps):
            d_imgs, d_lbls = next(d_it)
            w_imgs, w_lbls = next(w_it)
            h_imgs, h_lbls = next(h_it)

            d_imgs = d_imgs.to(device, non_blocking=True)
            d_lbls = d_lbls.to(device, non_blocking=True)
            w_imgs = w_imgs.to(device, non_blocking=True)
            w_lbls = w_lbls.to(device, non_blocking=True)
            h_imgs = h_imgs.to(device, non_blocking=True)
            h_lbls = h_lbls.to(device, non_blocking=True)

            optimizer.zero_grad()

            if use_amp:
                with torch.amp.autocast("cuda"):
                    d_loss = criterion(model(d_imgs)["disease"], d_lbls) * WEIGHTS["disease"]
                    w_loss = criterion(model(w_imgs)["weed"],    w_lbls) * WEIGHTS["weed"]
                    h_loss = criterion(model(h_imgs)["harvest"], h_lbls) * WEIGHTS["harvest"]
                    total_loss = d_loss + w_loss + h_loss

                scaler.scale(total_loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                d_loss = criterion(model(d_imgs)["disease"], d_lbls) * WEIGHTS["disease"]
                w_loss = criterion(model(w_imgs)["weed"],    w_lbls) * WEIGHTS["weed"]
                h_loss = criterion(model(h_imgs)["harvest"], h_lbls) * WEIGHTS["harvest"]
                total_loss = d_loss + w_loss + h_loss

                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            loss_sum["disease"] += d_loss.item()
            loss_sum["weed"]    += w_loss.item()
            loss_sum["harvest"] += h_loss.item()
            loss_sum["total"]   += total_loss.item()

            if (step + 1) % 50 == 0 or (step + 1) == steps:
                n     = step + 1
                pct   = n / steps * 100
                ela   = time.time() - epoch_start
                log(f"  [{pct:5.1f}%] adim {n:4d}/{steps} | "
                    f"total:{loss_sum['total']/n:.4f} | "
                    f"D:{loss_sum['disease']/n:.4f} "
                    f"W:{loss_sum['weed']/n:.4f} "
                    f"H:{loss_sum['harvest']/n:.4f} | "
                    f"{ela:.0f}s")

        scheduler.step()

        n        = steps
        avg_tot  = loss_sum["total"]   / n
        avg_d    = loss_sum["disease"] / n
        avg_w    = loss_sum["weed"]    / n
        avg_h    = loss_sum["harvest"] / n
        ep_time  = time.time() - epoch_start
        history.append((epoch + 1, avg_tot, avg_d, avg_w, avg_h))

        trend = ""
        if len(history) > 1:
            trend = "v" if avg_tot < history[-2][1] else "^"

        log(f"\n  Epoch {epoch+1:02d} {trend}  "
            f"total={avg_tot:.4f}  D={avg_d:.4f}  W={avg_w:.4f}  H={avg_h:.4f}  "
            f"({ep_time/60:.1f} dk)")

        val_acc = evaluate(model, loaders, device)
        mean_acc = sum(val_acc.values()) / 3
        log(f"  Val Acc:  Disease=%{val_acc['disease']:.1f}  "
            f"Weed=%{val_acc['weed']:.1f}  "
            f"Harvest=%{val_acc['harvest']:.1f}  "
            f"Ort=%{mean_acc:.1f}")

        # ortalama doğruluk arttıysa kaydediyorum
        if mean_acc > best_val:
            best_val = mean_acc
            torch.save({
                "model_state_dict":    model.state_dict(),
                "num_disease_classes": loaders["disease"]["num_classes"],
                "num_weed_classes":    loaders["weed"]["num_classes"],
                "num_harvest_classes": loaders["harvest"]["num_classes"],
                "disease_classes":     loaders["disease"]["classes"],
                "weed_classes":        loaders["weed"]["classes"],
                "harvest_classes":     loaders["harvest"]["classes"],
                "val_accuracy":        val_acc,
                "training_history":    history,
                "epoch":               epoch + 1,
            }, best_model_path)
            log(f"  [BEST] En iyi model kaydedildi! (ort=%{best_val:.1f})")

        sep("-")

    # eğitim bitti, son ağırlıkları da kaydediyorum
    torch.save({
        "model_state_dict":    model.state_dict(),
        "num_disease_classes": loaders["disease"]["num_classes"],
        "num_weed_classes":    loaders["weed"]["num_classes"],
        "num_harvest_classes": loaders["harvest"]["num_classes"],
        "disease_classes":     loaders["disease"]["classes"],
        "weed_classes":        loaders["weed"]["classes"],
        "harvest_classes":     loaders["harvest"]["classes"],
        "val_accuracy":        evaluate(model, loaders, device),
        "training_history":    history,
    }, model_path)

    total_time = time.time() - start_all

    sep()
    log("  EGITIM GECMISI")
    sep("-")
    log(f"  {'Ep':>4} | {'Total':>8} | {'Disease':>8} | {'Weed':>8} | {'Harvest':>8}")
    sep("-")
    for ep, tot, d, w, h in history:
        log(f"  {ep:>4} | {tot:>8.4f} | {d:>8.4f} | {w:>8.4f} | {h:>8.4f}")
    sep()
    log(f"\n  Toplam Sure  : {total_time/60:.1f} dakika")
    log(f"  Son Model    : {model_path}")
    log(f"  En Iyi Model : {best_model_path}  (ort val=%{best_val:.1f})")
    log(f"\n  Egitim tamamlandi. Test icin:")
    log(f"    python src/scripts/demo_unified.py")
    sep()


if __name__ == "__main__":
    main()
