import io
import os
import faiss
import torch
import numpy as np
import torch.nn as nn
from pathlib import Path
from torchvision import models
import torchvision.transforms as transforms
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────── CONFIG ───────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR,'model_index', 'font_model_v18.pt')
DRIVE_DIR  = "../FontData51/"
IMG_SIZE   = 380
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using: {DEVICE}")

# ─────────────────────────── MODEL ───────────────────────────
class FontClassifier(nn.Module):
    def __init__(self, num_classes: int):
        super().__init__()
        base = models.efficientnet_b4(weights=None)
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


def load_model():
    print("Loading model...")
    ckpt        = torch.load(MODEL_PATH, map_location=DEVICE)
    classes     = ckpt.get("classes", [])
    num_classes = len(classes)

    model = FontClassifier(num_classes=num_classes)
    model.load_state_dict(ckpt["model_state"])
    model = model.eval().to(DEVICE)

    print(f"Model loaded | {num_classes} fonts | {IMG_SIZE}x{IMG_SIZE}")
    return model, classes


# ─────────────────────────── TRANSFORM & UTILS ───────────────────────────
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

SAMPLE_TEXTS = [
    "กขคงจฉชซ",
    "ญดตถทธนบ",
    "ปผฝพฟภมยร",
    "ลวศษสหอฮ",
    "เแโใไาิีุู",
    "กขคง",
    "จฉซ",
    "ญดท",
    "นบผห",
    "ฟภมร",
    "ลวศษ",
    "ค่ามีไป",
    "โว้และเธอ",
    "หูกระจงควรปลูกให้ห่างจากตัวบ้าน",
    "ส้มตำ ผัดไทย โอเลี้ยง",
    "เบิร์ดแปลว่านก",
    "๐๑๒๓๔๕๖๗๘๙",
    "AaB",
    "bicd",
    "Eefg",
    "HIm",
    "jKLq",
    "Nopv",
    "QRrS",
    "tuxy"
    "AaBbCcDdEeFfGg",
    "HhIiJjKkLlMm",
    "NnOoPpQqRrSs",
    "TtUuVvWwXxYyZz",
    "Hamburgevons",
    "SunDaymOndAy",
    "Phra Nakhon Si Ayutthaya",
    "0123456789"
]

SAMPLE_SIZES = [32, 48, 64]

def render_text_with_font(ttf_bytes: bytes, text: str, size: int = 48) -> Image.Image:
    try:
        font = ImageFont.truetype(io.BytesIO(ttf_bytes), size=size)
        left, top, right, bottom = font.getbbox(text)
        img = Image.new("RGB", (right - left + 40, bottom - top + 40), color="white")
        ImageDraw.Draw(img).text((20, 20 - top), text, font=font, fill="black")
        return pad_to_square(img, target_size=IMG_SIZE)
    except Exception as e:
        print(f"Render Error: {e}")
        return Image.new("RGB", (IMG_SIZE, IMG_SIZE), color="white")
    
# ─────────────────────────── BUILD INDEX ───────────────────────────
def build_faiss_index():
    model, classes = load_model()

    embed_dim     = 1792
    index         = faiss.IndexFlatIP(embed_dim)
    font_metadata = []
    all_vectors   = []

    for ttf_path in sorted(Path(DRIVE_DIR).glob("*.ttf")):
        font_name = ttf_path.stem
        ttf_bytes = ttf_path.read_bytes()

        imgs = [
            render_text_with_font(ttf_bytes, text, size)
            for text in SAMPLE_TEXTS
            for size in SAMPLE_SIZES
        ]

        tensors = torch.stack([TRANSFORM(img) for img in imgs]).to(DEVICE)
        with torch.no_grad():
            vecs = model(tensors, return_embedding=True).cpu().numpy()

        print(f"[DEBUG] vec norm sample: {np.linalg.norm(vecs[0]):.4f}")

        all_vectors.append(vecs)
        font_metadata.extend([font_name] * len(imgs))
        print(f"✓ {font_name} ({len(imgs)} vectors)")

    final_vecs = np.vstack(all_vectors).astype("float32")
    index.add(final_vecs)

    faiss.write_index(index, f"{DRIVE_DIR}font_v28.index")
    np.save(f"{DRIVE_DIR}font_names_v28.npy", np.array(font_metadata))
    print(f"\nIndex build complete! ({index.ntotal} vectors, {len(set(font_metadata))} fonts)")

if __name__ == "__main__":
    build_faiss_index()
    index = faiss.read_index(f"{DRIVE_DIR}font_v28.index")
    print(f"Verified: {index.ntotal} vectors in index")
