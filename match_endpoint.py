import io
import os
import gc
import cv2
import time
import faiss
import torch
import easyocr
import numpy as np
import torch.nn as nn
from PIL import Image
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from torchvision import models, transforms
from fastapi import APIRouter, File, UploadFile, HTTPException

# ── Config ───────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR,'model_index','33', 'font_model_v17.pt')
INDEX_PATH = os.path.join(BASE_DIR,'model_index','33', 'font_v27.index')
NAMES_PATH = os.path.join(BASE_DIR,'model_index','33', 'font_names_v27.npy')

IMG_SIZE = 380
DEVICE   = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using: {DEVICE}")

_ocr_reader = None
_feature_extractor = None
_classes = None

# ── Function ────────────────────────────────────────────────────────────────────
def get_ocr_reader() -> easyocr.Reader:
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(["en", "th"], gpu=torch.cuda.is_available())
    return _ocr_reader

def load_model():
    global _feature_extractor, _classes
    if _feature_extractor is not None:
        return _feature_extractor, _classes

    print("Loading model...")
    checkpoint  = torch.load(MODEL_PATH, map_location=DEVICE)
    _classes     = checkpoint['classes']
    num_classes = len(_classes)
    model = models.efficientnet_b4(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    model.load_state_dict(checkpoint['model_state'])
    _feature_extractor = nn.Sequential(
        model.features,
        model.avgpool,
        nn.Flatten()
    ).eval().to(DEVICE)

    del model
    gc.collect()

    print("Model loaded")
    return _feature_extractor, _classes

TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

def search_font_from_crops(crops, feature_extractor, index, names, top_k=10):
    if not crops:
        return []

    font_scores = {}
    for img in crops:
        if img.mode != "RGB":
            img = img.convert("RGB")

        img = preprocess(img)
        img = pad_to_square(img)
        tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            vec = feature_extractor(tensor).cpu().numpy()

        vec = vec / (np.linalg.norm(vec) + 1e-8)
        query = vec.astype("float32")
        D, I = index.search(query, k=top_k * 15)
        for score, idx in zip(D[0], I[0]):
            name = names[idx]
            if name not in font_scores or score > font_scores[name]:
                font_scores[name] = float(score)

    sorted_results = sorted(font_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return sorted_results

def preprocess(img: Image.Image, target_size=380, margin=20) -> Image.Image:
    img = img.convert("L").convert("RGB")
    img_np = np.array(img)
    threshold = 180
    img_np = np.where(img_np < threshold, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_np)
    bbox = img.convert("L").point(lambda x: 0 if x > 128 else 255).getbbox()
    if bbox:
        img = img.crop(bbox)
    
    w, h = img.size
    pad_size = max(w, h) + margin * 2
    padded = Image.new("RGB", (pad_size, pad_size), (255, 255, 255))
    padded.paste(img, ((pad_size - w) // 2, (pad_size - h) // 2))
    img = padded.resize((target_size, target_size), Image.LANCZOS)
    return img


def pad_to_square(img, background_color=(255, 255, 255)):
    width, height = img.size
    if width == height:
        return img

    padding=5
    new_w = width + padding * 2
    new_h = height + padding * 2
    max_wh = max(new_w, new_h)
    result = Image.new(img.mode, (max_wh, max_wh), background_color)
    result.paste(img, ((max_wh - new_w) // 2, (max_wh - new_h) // 2))
    return result


def preprocess_for_ocr(img_np: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    print(f"w: {w}, h: {h}")
    if w < 100 and h < 90:
        scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(scaled)
        print("--- Upscaled! ---")
    else: 
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
    
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return thresh

# ── Router ────────────────────────────────────────────────────────────────────
router = APIRouter()

@router.post("/match")
async def match_font(file: UploadFile = File(...)):
    print(f"\nMatching font...")
    start   = time.time()

    # ── 1. รับไฟล์ภาพจาก FastAPI (In-memory) ────────────────────────────────
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="INVALID_IMAGE")

    img_np = np.array(img)

    # ── 2. OCR ───────────────────────────────────────────────────────────────
    model = ocr_predictor(pretrained=True)
    t0 = time.time()
    reader = get_ocr_reader()

    ocr_results = reader.readtext(preprocess_for_ocr(img_np))
    confident_texts = [r for r in ocr_results if r[2] >= 0.4]
    print(f"EasyOCR time : {time.time() - t0:.2f}s")

    _, buffer = cv2.imencode(".jpg", img_np)
    img_bytes = buffer.tobytes()
    
    doc = DocumentFile.from_images(img_bytes)
    result = model(doc)
    h, w = img_np.shape[:2]
    if not confident_texts:
        texts = []
        t1 = time.time()
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    line_text = " ".join([word.value for word in line.words])
                    line_conf = np.mean([word.confidence for word in line.words])
                    geo = line.geometry  # ((x1,y1), (x2,y2)) normalized
                    x1 = int(geo[0][0] * w)
                    y1 = int(geo[0][1] * h)
                    x2 = int(geo[1][0] * w)
                    y2 = int(geo[1][1] * h)
                    
                    bbox = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                    texts.append((bbox, line_text, line_conf))
        confident_texts = [t for t in texts if t[2] >= 0.4]
        print(f"docTR time : {time.time() - t1:.2f}s")
        print("---- Using ocr_predictor ----")
   
    if not confident_texts:
        raise HTTPException(status_code=422, detail="NO_TEXT_DETECTED")

    detected_text = " ".join([r[1] for r in confident_texts]).strip()

    # ── 3. Crop ที่ OCR ตรวจพบ ──────────────────────────
    query_images_to_search = []
    MIN_W, MIN_H = 20, 10
    for bbox, text, conf in confident_texts:
        PAD_V = 15  
        PAD_H = 8   
        pts = np.array(bbox, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(pts)

        x1 = max(0, x - PAD_H)
        y1 = max(0, y - PAD_V)
        x2 = min(img.width,  x + w + PAD_H)
        y2 = min(img.height, y + h + PAD_V)
        
        if w <= 0 or h <= 0:
            continue
        if w < MIN_W or h < MIN_H:             
            print(f"Skip small crop: {w}x{h}")
            continue
      
        crop = img.crop((x, y, x + w, y + h))
        query_images_to_search.append(crop)

    if not query_images_to_search:
        raise HTTPException(status_code=422, detail="NO_CROP")

    # ── 4. โหลด Model + FAISS Index และทำ Search ────────────────────────────
    feature_extractor, classes = load_model()
    index = faiss.read_index(INDEX_PATH)
    names = np.load(NAMES_PATH, allow_pickle=True)
    t2   = time.time()
    faiss_matches = search_font_from_crops(
        crops=query_images_to_search,
        feature_extractor=feature_extractor,
        index=index,
        names=names,
        top_k=20
    )

    # ── 5. Cleanup memory ────────────────────────────────────────────────────
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ── 6. Return ─────────────────────────────────────────────────────────────
    print("\n===== FONT MATCH RESULTS =====")
    print(f"Detected text: {detected_text}")
    print(f"Top {len(faiss_matches[:20])} matches:")
    for i, (name, score) in enumerate(faiss_matches[:20], 1):
        print(f"  {i}. {name:40} -> {score:.4f}")
    print("==============================")
    print(f"index search time : {time.time() - t2:.2f}s")

    print(f"\nMatching font time : {time.time() - start:.2f}s \n")

    return {
        "matches": [
            {"name": name, "similarity": round(float(score), 4)}
            for name, score in faiss_matches[:20]
        ],
        "detected_text": detected_text
    }
