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
from PIL import Image, ImageOps
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

def _binarize(img):
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(result)

def _remove_background(img):
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
    gray     = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    result   = cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(result)

def preprocess(img):
    # 1. แปลงเป็น Grayscale
    img_gray = img.convert("L")
    
    # ตรวจสอบว่าเป็นภาพพื้นหลังมืดตัวอักษรสว่างหรือไม่
    # ดูค่าเฉลี่ยของสีพิกเซลทั้งหมด ถ้าต่ำกว่า 127 แสดงว่าภาพส่วนใหญ่เป็นสีมืด
    img_np_check = np.array(img_gray)
    if np.mean(img_np_check) < 127:
        # กลับสีภาพ: จากพื้นหลังดำตัวอักษรขาว -> พื้นหลังขาวตัวอักษรดำ
        img_gray = ImageOps.invert(img_gray)

    # 2. แปลงกลับเป็น RGB เพื่อทำ Thresholding
    img = img_gray.convert("RGB")
    np_img = np.array(img)
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

def pad_to_square_direct(img, bg=(255, 255, 255)):
    w, h = img.size
    if w == h:
        return img
    m = max(w, h)
    result = Image.new(img.mode, (m, m), bg)
    result.paste(img, ((m - w) // 2, (m - h) // 2))
    return result

def search_font_from_crops(crops, feature_extractor, index, names, top_k=10):
    if not crops:
        return []

    font_scores = {}
    for img in crops:
        if img.mode != "RGB":
            img = img.convert("RGB")

        img = preprocess_for_crops(img)
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

def preprocess_for_crops(img: Image.Image, target_size=380, margin=20) -> Image.Image:
    # 1. แปลงเป็น Grayscale
    img_gray = img.convert("L")
    
    # ตรวจสอบว่าเป็นภาพพื้นหลังมืดตัวอักษรสว่างหรือไม่
    # ดูค่าเฉลี่ยของสีพิกเซลทั้งหมด ถ้าต่ำกว่า 127 แสดงว่าภาพส่วนใหญ่เป็นสีมืด
    img_np_check = np.array(img_gray)
    if np.mean(img_np_check) < 127:
        # กลับสีภาพ: จากพื้นหลังดำตัวอักษรขาว -> พื้นหลังขาวตัวอักษรดำ
        img_gray = ImageOps.invert(img_gray)

    # 2. แปลงกลับเป็น RGB เพื่อทำ Thresholding
    img = img_gray.convert("RGB")
    img_np = np.array(img)
    threshold = 180
    img_np = np.where(img_np < threshold, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_np)

    # 3. หา Bounding Box เพื่อ Crop เอาเฉพาะตัวอักษร
    bbox = img.convert("L").point(lambda x: 0 if x > 128 else 255).getbbox()
    if bbox:
        img = img.crop(bbox)
    
    # 4. จัดการ Padding ให้เป็นสี่เหลี่ยมจัตุรัสตามเดิม
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

    # ตรวจสอบพื้นหลังมืด (ถ้าค่าเฉลี่ยพิกเซลน้อยกว่า 127 แสดงว่าเป็นพื้นหลังมืด)
    if np.mean(gray) < 127:
        # กลับสีพิกเซล (Invert) ให้เป็นตัวอักษรดำบนพื้นหลังขาวก่อนประมวลผลต่อ
        gray = cv2.bitwise_not(gray)
        print("--- Inverted Dark Background for OCR ---")
        
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

    # ── 2.1 EasyOCR ───────────────────────────────────────────────────────────────
    model = ocr_predictor(pretrained=True)
    t0 = time.time()
    reader = get_ocr_reader()
    ocr_results = reader.readtext(preprocess_for_ocr(img_np))
    confident_texts = [r for r in ocr_results if r[2] >= 0.4]
    print(f"EasyOCR time : {time.time() - t0:.2f}s")

    # ── 2.2 docTR ───────────────────────────────────────────────────────────────
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
   
    print(f"confident texts: {confident_texts}")
    if not confident_texts:
        raise HTTPException(status_code=422, detail="NO_TEXT_DETECTED")

    detected_text = " ".join([r[1] for r in confident_texts]).strip()
    print(f"detected text: {detected_text}")

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

    print(f"query_images: {query_images_to_search}")

    if not query_images_to_search:
        # นำรูปภาพต้นฉบับทั้งก้อน มาปรับสภาพและทำเป็นสี่เหลี่ยมจัตุรัส
        direct_img = preprocess(img)
        direct_img = pad_to_square_direct(direct_img)
        query_images_to_search.append(direct_img)
        print("---- No Using ocr_predictor ----")
    #     raise HTTPException(status_code=422, detail="NO_CROP")

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
    # print(f"Detected text: {detected_text}")
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
