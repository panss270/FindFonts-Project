import os
import time
import glob
import faiss
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv
from torchvision import models
import torchvision.transforms as transforms


load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR,'model_index', 'font_v1.index')
NAMES_PATH = os.path.join(BASE_DIR,'model_index', 'font_names_v1.npy')
DRIVE_DIR2 = "../img_test-th/img_cap/"

_index = None
_names = None

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using: {DEVICE}")

base = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.DEFAULT)
MODEL = torch.nn.Sequential(
    base.features,
    torch.nn.AdaptiveAvgPool2d((1, 1)),
    torch.nn.Flatten()
).eval().to(DEVICE)

TRANSFORM = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

_index = faiss.read_index(INDEX_PATH)
_names = np.load(NAMES_PATH, allow_pickle=True)

def pad_to_square(img, background_color=(255, 255, 255)):
    width, height = img.size
    if width == height:
        return img
    max_wh = max(width, height)
    result = Image.new(img.mode, (max_wh, max_wh), background_color)
    result.paste(img, ((max_wh - width) // 2, (max_wh - height) // 2))
    return result

def match_font(image_path: str, top_k: int = 5):
    img = Image.open(image_path).convert("RGB")
    img = pad_to_square(img)

    tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        vec = MODEL(tensor).cpu().numpy()

    vec = vec / (np.linalg.norm(vec, axis=1, keepdims=True) + 1e-8)
    query = vec.astype("float32")

    D, I = _index.search(query, k=top_k * 15)

    font_scores = {}
    for score, idx in zip(D[0], I[0]):
        if idx == -1: continue
        name = _names[idx]
        if name not in font_scores or score > font_scores[name]:
            font_scores[name] = float(score)

    return sorted(font_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

def is_match(stem, top1):
    clean_top1 = top1.lower()
    clean_stem = stem.lower()
    for suffix in ["-regular", "-bold", "-italic", "-light", "-medium", "-en", "-th"]:
        clean_stem = clean_stem.replace(suffix, "")
        clean_top1 = clean_top1.replace(suffix, "")
    clean_stem = clean_stem.replace(" ", "_")
    clean_top1 = clean_top1.replace(" ", "_")
    return clean_stem == clean_top1

# ── ทดสอบ ──────────────────────────────────────────────────
image_path = (
    glob.glob(f"{DRIVE_DIR2}*.png") +
    glob.glob(f"{DRIVE_DIR2}*.jpg") +
    glob.glob(f"{DRIVE_DIR2}*.jpeg")
)
image_files = image_path

if not image_files:
    print(f"Not found folder: {DRIVE_DIR2}")
else:
    print(f"found folder: {DRIVE_DIR2}")
    start   = time.time()
    correct = 0
    total   = 0
    for image_path in image_files:
        file_name = os.path.basename(image_path)
        results = match_font(image_path)
        top1    = results[0][0]
        ok = is_match(Path(image_path).stem, top1)
        status = "OK" if ok else "XX"
        if ok:
            correct += 1
        total += 1
        print(f"{status} === {Path(image_path).name} ===")
        for rank, (name, score) in enumerate(results, 1):
            print(f"  {rank}. {name:40} ->  {score:.4f}")
        print()

    elapsed = time.time() - start
    print("-" * 30)
    print(f"Accuracy:  {correct}/{total} = {correct/total*100:.1f}%")
    print(f"Render Time Per image: {elapsed/total:.2f}s")