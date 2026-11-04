import io
import torch
import random
import numpy as np
import torch.nn as nn
from pathlib import Path
import torch.optim as optim
from PIL import Image, ImageFilter
from collections import defaultdict
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader


# ─────────────────────────── CONFIG ───────────────────────────
DATA_DIRS         = ["/kaggle/input/datasets/fontimgtest/img_preprocessing-en/", 
                     "/kaggle/input/datasets/fontimgtest/img_preprocessing-th/"]
VARIANT_FOLDERS   = ["img_cap", "img_pre-Blur", "img_pre-Clean", "img_pre-Color",
                     "img_pre-Dot", "img_pre-Noise", "img_pre-Perspective", "mobile", "img_html",
                     "addtxt-Clean-0", "addtxt-Clean-1", "addtxt-Clean-2", "addtxt-Clean-3",
                     "addtxt-Clean-4", "addtxt-Clean-5", "addtxt-Clean-6", "addtxt-Clean-7",
                     "addtxt-Color-0", "addtxt-Color-1", "addtxt-Color-2", "addtxt-Color-3",
                     "addtxt-Color-4", "addtxt-Color-5", "addtxt-Color-6", "addtxt-Color-7",
                     "addtxt-Blur-0", "addtxt-Blur-1", "addtxt-Blur-2", "addtxt-Blur-3",
                     "addtxt-Blur-4", "addtxt-Blur-5", "addtxt-Blur-6", "addtxt-Blur-7",
                     "addtxt-Dot-0", "addtxt-Dot-1", "addtxt-Dot-2", "addtxt-Dot-3",
                     "addtxt-Dot-4", "addtxt-Dot-5", "addtxt-Dot-6", "addtxt-Dot-7",
                     "addtxt-Noise-0", "addtxt-Noise-1", "addtxt-Noise-2", "addtxt-Noise-3",
                     "addtxt-Noise-4", "addtxt-Noise-5", "addtxt-Noise-6", "addtxt-Noise-7",
                     "addtxt-Perspective-0", "addtxt-Perspective-1", "addtxt-Perspective-2", "addtxt-Perspective-3",
                     "addtxt-Perspective-4", "addtxt-Perspective-5", "addtxt-Perspective-6", "addtxt-Perspective-7",
                     "addtxt2-Clean-0", "addtxt2-Clean-1", "addtxt2-Clean-2", "addtxt2-Clean-3",
                     "addtxt2-Clean-4", "addtxt2-Clean-5", "addtxt2-Clean-6", "addtxt2-Clean-7",
                     "addtxt2-Color-0", "addtxt2-Color-1", "addtxt2-Color-2", "addtxt2-Color-3",
                     "addtxt2-Color-4", "addtxt2-Color-5", "addtxt2-Color-6", "addtxt2-Color-7",
                     "addtxt2-Blur-0", "addtxt2-Blur-1", "addtxt2-Blur-2", "addtxt2-Blur-3",
                     "addtxt2-Blur-4", "addtxt2-Blur-5", "addtxt2-Blur-6", "addtxt2-Blur-7",
                     "addtxt2-Dot-0", "addtxt2-Dot-1", "addtxt2-Dot-2", "addtxt2-Dot-3",
                     "addtxt2-Dot-4", "addtxt2-Dot-5", "addtxt2-Dot-6", "addtxt2-Dot-7",
                     "addtxt2-Noise-0", "addtxt2-Noise-1", "addtxt2-Noise-2", "addtxt2-Noise-3",
                     "addtxt2-Noise-4", "addtxt2-Noise-5", "addtxt2-Noise-6", "addtxt2-Noise-7",
                     "addtxt2-Perspective-0", "addtxt2-Perspective-1", "addtxt2-Perspective-2", "addtxt2-Perspective-3",
                     "addtxt2-Perspective-4", "addtxt2-Perspective-5", "addtxt2-Perspective-6", "addtxt2-Perspective-7"]
SAVE_PATH         = "/kaggle/working/font_model_v17.pt"
IMG_SIZE          = 380
BATCH_SIZE        = 8 
EPOCHS            = 50
LR                = 1e-4
DEVICE            = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using: {DEVICE}")

# ─────────────────────────── AUGMENTATION ───────────────────────────
def augment_screenshot(img: Image.Image) -> Image.Image:
    img = img.copy()

    # พื้นหลังเทาอ่อน
    if random.random() < 0.5:
        bg = random.randint(220, 245)
        np_img = np.array(img)
        mask = np_img[:, :, 0] > 240
        np_img[mask] = [bg, bg, bg]
        img = Image.fromarray(np_img)

    # Blur
    if random.random() < 0.5:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.2, 0.7)))

    # Downscale แล้ว upscale (low-res capture)
    if random.random() < 0.4:
        w, h = img.size
        scale = random.uniform(0.5, 0.85)
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        img = img.resize((w, h), Image.LANCZOS)

    # JPEG noise
    if random.random() < 0.3:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=random.randint(70, 92))
        buf.seek(0)
        img = Image.open(buf).convert("RGB")

    return img


# ─────────────────────────── TRANSFORM ───────────────────────────
TRANSFORM = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

def pad_to_square(img: Image.Image, target_size: int = 380, pad: int = 10) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    avail_h = target_size - (pad * 2)
    scale_factor = avail_h / h
    new_h = avail_h
    new_w = int(w * scale_factor)
    if new_w > (target_size - (pad * 2)):
        new_w = target_size - (pad * 2)
        scale_factor = new_w / w
        new_h = int(h * scale_factor)

    img_resized = img.resize((new_w, new_h), Image.LANCZOS)
    result = Image.new("RGB", (target_size, target_size), (255, 255, 255))
    paste_x = (target_size - new_w) // 2
    paste_y = (target_size - new_h) // 2
    result.paste(img_resized, (paste_x, paste_y))
    return result

# ─────────────────────────── DATASET ───────────────────────────
class FontDataset(Dataset):
    def __init__(self, data_dirs: list[str], augment: bool = True):
        self.augment = augment
        self.font_to_imgs: dict[str, list[Path]] = defaultdict(list)
        extensions = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

        for data_dir in data_dirs:
            for variant in VARIANT_FOLDERS:
                folder = Path(data_dir) / variant
                if not folder.exists():
                    print(f"[WARN] not found: {folder}")
                    continue
                for img_path in folder.iterdir():
                    if img_path.suffix.lower() in extensions:
                        self.font_to_imgs[img_path.stem].append(img_path)

        self.fonts   = sorted(self.font_to_imgs.keys())
        self.font2id = {f: i for i, f in enumerate(self.fonts)}
        self.samples = [
            (img_path, self.font2id[font])
            for font, paths in self.font_to_imgs.items()
            for img_path in paths
        ]

        total = sum(len(v) for v in self.font_to_imgs.values())
        print(f"Dataset: {len(self.fonts)} fonts | {total} images")

    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        img = Image.open(img_path).convert("RGB")
        
        if self.augment:
            img = augment_screenshot(img)
            
        img = pad_to_square(img, target_size=IMG_SIZE)
        
        return TRANSFORM(img), label


# ─────────────────────────── MODEL ───────────────────────────
class FontClassifier(nn.Module):
    def __init__(self, num_classes: int, pretrained: bool = True):
        super().__init__()
        weights = models.EfficientNet_B4_Weights.DEFAULT if pretrained else None
        base = models.efficientnet_b4(weights=weights)
        base.classifier[1] = nn.Linear(1792, num_classes)
        self.features   = base.features
        self.avgpool    = base.avgpool
        self.classifier = base.classifier

    def forward(self, x, return_embedding: bool = False):
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        if return_embedding:
            return nn.functional.normalize(x, p=2, dim=1)

        return self.classifier(x)


# ─────────────────────────── TRAIN ───────────────────────────
def train():
    print("Loading dataset...")
    dataset = FontDataset(DATA_DIRS, augment=True)
    print(f"Dataset loaded: {len(dataset)} samples")

    print("Creating dataloader...")
    loader  = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    print("Starting training...")

    model     = FontClassifier(num_classes=len(dataset.fonts), pretrained=True).to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_loss = float("inf")

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        correct    = 0
        total      = 0

        for imgs, labels in loader:
            imgs   = imgs.to(DEVICE)
            labels = labels.to(DEVICE)

            logits = model(imgs)
            loss   = criterion(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            correct    += (logits.argmax(1) == labels).sum().item()
            total      += len(labels)

        avg_loss = total_loss / len(loader)
        acc      = correct / total * 100
        scheduler.step()

        print(f"Epoch {epoch:3d}/{EPOCHS} | loss: {avg_loss:.4f} | acc: {acc:.1f}%")

        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save({
                "model_state": model.state_dict(),
                "classes":     dataset.fonts,
                "img_size":    IMG_SIZE,
            }, SAVE_PATH)
            print(f"Saved best model → {SAVE_PATH}")

    print(f"\nDone! Best loss: {best_loss:.4f}")
    print(f"Next: รัน build_index เพื่อสร้าง FAISS index ใหม่")
