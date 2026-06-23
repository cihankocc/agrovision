import sys
import os
import torch
import torchvision.transforms as transforms
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.models.unified_cnn import WheatAIUnifiedModel

console = Console()

# tahmin sırasında augmentation uygulamıyorum, sadece resize ve normalize
INFER_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def load_model(model_path: str, device: torch.device) -> tuple:
    if not os.path.exists(model_path):
        console.print(f"[bold red]HATA: Model dosyası bulunamadı![/bold red]\nBeklenen: {model_path}")
        sys.exit(1)

    checkpoint = torch.load(model_path, map_location=device)

    model = WheatAIUnifiedModel(
        num_disease_classes=checkpoint["num_disease_classes"],
        num_weed_classes=checkpoint["num_weed_classes"],
        num_harvest_classes=checkpoint["num_harvest_classes"],
    ).to(device)

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    return model, checkpoint


def predict(model, image_path: str, device: torch.device, checkpoint: dict) -> dict:
    img = Image.open(image_path).convert("RGB")
    tensor = INFER_TRANSFORM(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(tensor)

    results = {}
    task_meta = {
        "disease": {
            "tr":      "🦠 Hastalık Tespiti",
            "classes": checkpoint.get("disease_classes", [str(i) for i in range(checkpoint["num_disease_classes"])]),
        },
        "weed": {
            "tr":      "🌿 Yabani Ot Tespiti",
            "classes": checkpoint.get("weed_classes", ["Weed", "Wheat"]),
        },
        "harvest": {
            "tr":      "🌾 Hasat Olgunluğu",
            "classes": checkpoint.get("harvest_classes", ["Mature", "Seedling", "Unripe"]),
        },
    }

    for task, logits in outputs.items():
        probs      = torch.softmax(logits, dim=1).squeeze()
        conf, idx  = torch.max(probs, dim=0)
        class_name = task_meta[task]["classes"][idx.item()]
        results[task] = {
            "label":      class_name,
            "confidence": conf.item() * 100,
            "all_probs":  {
                cls: probs[i].item() * 100
                for i, cls in enumerate(task_meta[task]["classes"])
            },
            "title": task_meta[task]["tr"],
        }

    return results


def print_results(results: dict, image_path: str):
    console.print(Panel.fit(
        f"[bold yellow]🌾 WHEAT AI - UNIFIED MODEL TAHMİN SONUÇLARI[/bold yellow]\n"
        f"[dim]Görüntü: {os.path.basename(image_path)}[/dim]",
        border_style="yellow",
        box=box.DOUBLE_EDGE
    ))

    for task, res in results.items():
        # güven skoruna göre renk seçiyorum
        conf_color = "green" if res["confidence"] > 75 else "yellow" if res["confidence"] > 50 else "red"

        table = Table(
            title=f"{res['title']}  →  [bold {conf_color}]{res['label']}[/bold {conf_color}]  "
                  f"([{conf_color}]%{res['confidence']:.1f}[/{conf_color}])",
            box=box.ROUNDED,
            border_style="cyan" if task == "disease" else "blue" if task == "weed" else "green"
        )
        table.add_column("Sınıf",    style="bold white")
        table.add_column("Olasılık", justify="right")
        table.add_column("Bar",      no_wrap=True)

        for cls, prob in sorted(res["all_probs"].items(), key=lambda x: x[1], reverse=True):
            bar_len = int(prob / 5)
            bar     = "█" * bar_len + "░" * (20 - bar_len)
            color   = "green" if cls == res["label"] else "dim"
            table.add_row(
                f"[{color}]{cls}[/{color}]",
                f"[{color}]%{prob:.1f}[/{color}]",
                f"[{color}]{bar}[/{color}]"
            )

        console.print(table)

    console.print(Panel.fit(
        "📝 [bold]ÖZET KARAR:[/bold]\n\n" +
        "\n".join(
            f"  {res['title']:30s}: [bold green]{res['label']}[/bold green]  "
            f"(güven: %{res['confidence']:.1f})"
            for res in results.values()
        ),
        border_style="yellow",
        box=box.ROUNDED
    ))


def main():
    if len(sys.argv) < 2:
        console.print("[bold red]Kullanım:[/bold red] python predict_unified.py <resim_yolu>")
        console.print("[dim]Örnek:   python src/scripts/predict_unified.py test.jpg[/dim]")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.exists(image_path):
        console.print(f"[bold red]HATA: Resim bulunamadı![/bold red] {image_path}")
        sys.exit(1)

    BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    model_path = os.path.join(BASE_DIR, "wheat_ai_unified_model.pth")
    device     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    console.print(f"[cyan]📂 Model yükleniyor...[/cyan] {model_path}")
    model, checkpoint = load_model(model_path, device)

    console.print(f"[cyan]🖼️  Görüntü işleniyor...[/cyan] {image_path}\n")
    results = predict(model, image_path, device, checkpoint)

    print_results(results, image_path)


if __name__ == "__main__":
    main()
