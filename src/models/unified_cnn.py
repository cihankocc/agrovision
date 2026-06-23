import torch
import torch.nn as nn
from torchvision import models


class WheatAIUnifiedModel(nn.Module):
    def __init__(
        self,
        num_disease_classes: int = 15,
        num_weed_classes: int = 2,
        num_harvest_classes: int = 3,
    ):
        super().__init__()

        # ResNet50'yi backbone olarak kullandım, ImageNet ağırlıklarıyla başlıyorum
        base = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
        self.backbone = nn.Sequential(*list(base.children())[:-1])  # son FC'yi atıyorum

        # ortak embedding katmanı, 3 görev de buradan beslenecek
        self.shared_embedding = nn.Sequential(
            nn.Flatten(),
            nn.Linear(2048, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
        )

        # her görev için ayrı bir sınıflandırma başlığı
        self.disease_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, num_disease_classes),
        )
        self.weed_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(128, num_weed_classes),
        )
        self.harvest_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(128, num_harvest_classes),
        )

        # ilk katmanları donduruyorum, sadece üst katmanlar eğitilsin
        for layer in list(self.backbone.children())[:6]:
            for param in layer.parameters():
                param.requires_grad = False

    def unfreeze_all(self):
        # fine-tuning aşamasına geçince tüm parametreleri açıyorum
        for param in self.parameters():
            param.requires_grad = True

    def forward(self, x: torch.Tensor) -> dict:
        feat = self.backbone(x)
        emb  = self.shared_embedding(feat)
        return {
            "disease": self.disease_head(emb),
            "weed":    self.weed_head(emb),
            "harvest": self.harvest_head(emb),
        }


if __name__ == "__main__":
    m = WheatAIUnifiedModel()
    x = torch.randn(4, 3, 224, 224)
    out = m(x)
    for k, v in out.items():
        print(f"{k:10s}: {v.shape}")
    total     = sum(p.numel() for p in m.parameters())
    trainable = sum(p.numel() for p in m.parameters() if p.requires_grad)
    print(f"\nToplam Parametre  : {total:,}")
    print(f"Egitilecek Param  : {trainable:,}")
