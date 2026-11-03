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
INDEX_PATH = os.path.join(BASE_DIR,'model_index','33', 'font_v1.index')
NAMES_PATH = os.path.join(BASE_DIR,'model_index','33', 'font_names_v1.npy')
DRIVE_DIR2 = "../img_test-th/img_html/"
# folder image
# img_preprocessing-en/img_pre-Blur/
# img_cap-en/
# คำสั่งรัน python match_index.py
# INDEX_URL = os.getenv("INDEX_URL")
# NAMES_URL = os.getenv("NAMES_URL")

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

# โหลดครั้งเดียวตอน import module
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

    # L2 Normalization (สำคัญมากเพื่อให้ค่า Distance นิ่ง)
    vec = vec / (np.linalg.norm(vec, axis=1, keepdims=True) + 1e-8)
    query = vec.astype("float32")
    # vec = vec / (np.linalg.norm(vec) + 1e-8)

    # ใช้ตัวที่โหลดไว้แล้ว
    D, I = _index.search(query, k=top_k * 15)

    font_scores = {}
    for score, idx in zip(D[0], I[0]):
        if idx == -1: continue
        name = _names[idx]
        if name not in font_scores or score > font_scores[name]:
            font_scores[name] = float(score)

    return sorted(font_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

def is_match(stem, top1):
    """เทียบชื่อ font ระหว่างชื่อภาพกับฟอนต์ที่มี (สำหรับการทดสอบเท่านั้น)"""
    clean_top1 = top1.lower()
    clean_stem = stem.lower()
    for suffix in ["-regular", "-bold", "-italic", "-light", "-medium", "-en", "-th"]:
        clean_stem = clean_stem.replace(suffix, "")
        clean_top1 = clean_top1.replace(suffix, "")
    clean_stem = clean_stem.replace(" ", "_")
    clean_top1 = clean_top1.replace(" ", "_")
    # print(f"stem {stem}")
    # print(f"top1 {top1}")
    # print(f"clean_stem  {clean_stem}")
    # print(f"clean_top1  {clean_top1}")
    return clean_stem == clean_top1

# ── ทดสอบ ──────────────────────────────────────────────────
# image_path = f"{DRIVE_DIR2}*.png" # อ่านทุกไฟล์ .png ในโฟลเดอร์
image_path = (
    glob.glob(f"{DRIVE_DIR2}*.png") +
    glob.glob(f"{DRIVE_DIR2}*.jpg") +
    glob.glob(f"{DRIVE_DIR2}*.jpeg")
)
# image_files = glob.glob(image_path)
image_files = image_path

# 1. ตรวจสอบว่าไฟล์มีอยู่จริงหรือไม่
if not image_files:
    print(f"Not found folder: {DRIVE_DIR2}")
else:
    # print(f"found folder: {image_path}")
    print(f"found folder: {DRIVE_DIR2}")
    # 3. ส่งภาพไป Match ฟอนต์
    start   = time.time()
    correct = 0
    total   = 0
    for image_path in image_files:
        # 2. แสดงชื่อภาพที่กำลังเทียบ (ใช้ os.path.basename เพื่อเอาแค่ชื่อไฟล์)
        file_name = os.path.basename(image_path)
        # print(f"img name: [ {file_name} ]")

        results = match_font(image_path)
        top1    = results[0][0]
        ok = is_match(Path(image_path).stem, top1)
        status = "OK" if ok else "XX"
        if ok:
            correct += 1
        total += 1

        # 4. แสดงผลลัพธ์
        print(f"{status} === {Path(image_path).name} ===")
        # print(f"{status} ======")
        for rank, (name, score) in enumerate(results, 1):
            print(f"  {rank}. {name:40} ->  {score:.4f}")
        print()

    elapsed = time.time() - start
    print("-" * 30) # ขีดเส้นคั่นระหว่างภาพ
    print(f"Accuracy:  {correct}/{total} = {correct/total*100:.1f}%")
    print(f"Render Time Per image: {elapsed/total:.2f}s")


   



# def run_test():
#     image_folder = os.path.join(DRIVE_DIR2, "*.png")
#     image_files = glob.glob(image_folder)

#     print(f"กำลังค้นหาไฟล์ใน: {os.path.abspath(DRIVE_DIR2)}")
#     print(f"พบไฟล์ทั้งหมด: {len(image_files)} ไฟล์")

#     if not image_files:
#         print("ไม่พบไฟล์รูปภาพในโฟลเดอร์")
#     else:
#         print(f"Processing :{image_folder} ")
#         return

#     for i, img_path in enumerate(image_files, 1):
#         try:
#             start_time = time.time()
#             file_name = os.path.basename(img_path)
#             print(f"[{i}/{len(image_files)}] กำลังประมวลผล: {file_name}...", end=" ", flush=True)

#             results = match_font(img_path)

#             print("เสร็จสิ้น!") # ถ้าขึ้นอันนี้แสดงว่า match_font ทำงานจบ
#             print("=== ผลลัพธ์ ===")
#             if not results:
#                 print("ไม่พบผลลัพธ์")
#             else:
#                 for rank, (name, score) in enumerate(results, 1):
#                     print(f"{rank}. {name}  →  {score:.4f}")
            
#             end_time = time.time()
#             print(f"Render Time: {end_time - start_time:.4f} seconds")
#             print("-" * 30)
            
#         except Exception as e:
#             print(f"\nเกิดข้อผิดพลาดกับไฟล์ {file_name}: {str(e)}")
#             # ใส่ continue เพื่อให้มันข้ามไฟล์ที่มีปัญหาไปทำไฟล์ถัดไป
#             continue

# if __name__ == "__main__":
#     run_test()
