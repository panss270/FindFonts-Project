import os
import gc
import faiss
import torch
import numpy as np
from PIL import Image
import torch.nn as nn
from pathlib import Path
from torchvision import models, transforms

# ── Config ───────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR,'model_index', 'font_model_v6.pt')
INDEX_PATH = os.path.join(BASE_DIR,'model_index', 'font_v6.index')
NAMES_PATH = os.path.join(BASE_DIR,'model_index', 'font_names_v6.npy')
img_dir = "../img_test-th/mobile"

IMG_SIZE = 380
DEVICE   = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using: {DEVICE}")

class FontEmbedder(nn.Module):
    def __init__(self, pretrained: bool = True):
        super().__init__()
        weights = models.EfficientNet_B4_Weights.DEFAULT if pretrained else None
        base = models.efficientnet_b4(weights=weights)
        self.features = base.features
        self.pool     = nn.AdaptiveAvgPool2d((1, 1))
        self.flatten  = nn.Flatten()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.pool(x)
        x = self.flatten(x)
        return nn.functional.normalize(x, p=2, dim=1)
    
# ── Transform ────────────────────────────────────────────────
TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


# ── Preprocessing Pipeline ───────────────────────────────────
def _binarize(img):
    import cv2
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(result)


def _remove_background(img):
    import cv2
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(result)


def _denoise(img):
    import cv2
    gray     = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    result   = cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(result)


def preprocess(img):
    import cv2
    np_img = np.array(img.convert("RGB"))
    gray   = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)

    lap_var   = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_noisy  = lap_var > 500
    is_blurry = lap_var < 100

    r, g, b  = np_img[:,:,0], np_img[:,:,1], np_img[:,:,2]
    max_diff = max(
        np.abs(r.astype(int) - g.astype(int)).mean(),
        np.abs(r.astype(int) - b.astype(int)).mean(),
        np.abs(g.astype(int) - b.astype(int)).mean()
    )
    is_colorful = max_diff > 5

    gray_f      = np.mean(np_img, axis=2)
    gray_pixels = gray_f[(gray_f > 10) & (gray_f < 245)]
    has_alias   = len(gray_pixels) > 500

    if is_noisy:
        img = _denoise(img)
    if is_colorful:
        img = _remove_background(img)
    elif has_alias and not is_blurry:
        img = _binarize(img)
    return img

# ── Helpers ──────────────────────────────────────────────────
def pad_to_square(img, bg=(255, 255, 255)):
    w, h = img.size
    if w == h:
        return img
    m = max(w, h)
    result = Image.new(img.mode, (m, m), bg)
    result.paste(img, ((m - w) // 2, (m - h) // 2))
    return result

def is_match(stem, top1):
    clean_top1 = top1.lower()
    clean_stem = stem.lower()
    for suffix in ["-regular", "-bold", "-italic", "-light", "-medium", "-en", "-th"]:
        clean_stem = clean_stem.replace(suffix, "")
        clean_top1 = clean_top1.replace(suffix, "")
    clean_stem = clean_stem.replace(" ", "_")
    clean_top1 = clean_top1.replace(" ", "_")
    return clean_stem == clean_top1


# ── Load Model ───────────────────────────────────────────────
def load_model():
    print("Loading model...")
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
    classes    = checkpoint['classes']
    model = FontEmbedder(pretrained=False)
    model.load_state_dict(checkpoint['model_state'])
    feature_extractor = model.eval().to(DEVICE)
    print(f"Model loaded | {len(classes)} fonts | {IMG_SIZE}x{IMG_SIZE}")
    return feature_extractor, classes

# ── Load Index ───────────────────────────────────────────────
def load_index():
    print("Loading FAISS index...")
    index = faiss.read_index(INDEX_PATH)
    names = np.load(NAMES_PATH, allow_pickle=True)
    print(f"Index loaded | {index.ntotal} vectors")
    return index, names

# ── Match Font ───────────────────────────────────────────────
def match_font(image_or_path, feature_extractor, index, names, top_k=5):
    if isinstance(image_or_path, (str, Path)):
        img = Image.open(image_or_path).convert("RGB")
    else:
        img = image_or_path.convert("RGB")

    img    = preprocess(img)     # ← preprocessing pipeline
    img    = pad_to_square(img)
    tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        vec = feature_extractor(tensor).cpu().numpy()
    vec   = vec / (np.linalg.norm(vec) + 1e-8)
    query = vec.astype("float32")

    D, I = index.search(query, k=top_k * 15)

    font_scores = {}
    for score, idx in zip(D[0], I[0]):
        name = names[idx]
        if name not in font_scores or score > font_scores[name]:
            font_scores[name] = float(score)

    return sorted(font_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

# ── Main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import time

    feature_extractor, classes = load_model()
    index, names               = load_index()
    print()

    if len(sys.argv) > 1:
        for img_path in sys.argv[1:]:
            img_path = Path(img_path)
            if not img_path.exists():
                print(f"File not found: {img_path}")
                continue

            start   = time.time()
            results = match_font(img_path, feature_extractor, index, names)
            elapsed = time.time() - start
            print(f"=== {img_path.name} ===")
            for rank, (name, score) in enumerate(results, 1):
                print(f"  {rank}. {name:40} ->  {score:.4f}")
            print(f"  Time: {elapsed:.2f}s\n")

    else:
        test_dir = Path(img_dir)
        print(test_dir)

        if not test_dir.exists():
            print(f"ไม่พบโฟลเดอร์ {img_dir}")
        else:
            test_images = list(test_dir.glob("*.png")) + list(test_dir.glob("*.jpg"))

            if not test_images:
                print("ไม่พบภาพในโฟลเดอร์")
            else:
                start   = time.time()
                correct = 0
                total   = 0

                for img_path in sorted(test_images):
                    results = match_font(img_path, feature_extractor, index, names)
                    top1    = results[0][0]

                    ok     = is_match(img_path.stem, top1)
                    status = "OK" if ok else "XX"
                    if ok:
                        correct += 1
                    total += 1

                    print(f"{status} === {img_path.name} ===")
                    for rank, (name, score) in enumerate(results, 1):
                        print(f"  {rank}. {name:40} ->  {score:.4f}")
                    print()

                elapsed = time.time() - start
                print(f"{'='*50}")
                print(f"Accuracy:  {correct}/{total} = {correct/total*100:.1f}%")
                print(f"Per image: {elapsed/total:.2f}s")