import os
import cv2
import time
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

INPUT_FONT_DIR = "../FontData51/"       # โฟลเดอร์ที่เก็บไฟล์ .ttf
OUTPUT_IMAGE_DIR = "../img_preprocessing-th/"  # โฟลเดอร์ที่จะเซฟรูปภาพ
print(f"มีโฟลเดอร์นี้อยู่จริงไหม?: {os.path.exists(INPUT_FONT_DIR)}")
print(f"มีโฟลเดอร์นี้อยู่จริงไหม?: {os.path.exists(OUTPUT_IMAGE_DIR)}")

# ----------------------- ori txt th-en
SAMPLE_TEXT = "กรุงเทพประเทศไทย"
# SAMPLE_TEXT = "BaNgKok ThaIlAnD"

# ----------------------- addtxt th
# SAMPLE_TEXT = [
#     "กขคงจฉชซ",
#     "ญดตถทธนบ",
#     "ปผฝพฟภมยร",
#     "ลวศษสหอฮ",
#     "หูกระจงควรปลูกให้ห่างจากตัวบ้าน",
#     "ส้มตำ ผัดไทย โอเลี้ยง",
#     "เบิร์ดแปลว่านก",
#     "๐๑๒๓๔๕๖๗๘๙"
# ]   

# ----------------------- addtxt en
# SAMPLE_TEXT = [
#     "AaBbCcDdEeFfGg",
#     "HhIiJjKkLlMm",
#     "NnOoPpQqRrSs",
#     "TtUuVvWwXxYyZz",
#     "Hamburgevons",
#     "SunDaymOndAy",
#     "Phra Nakhon Si Ayutthaya",
#     "0123456789"
# ]   

# ----------------------- addtxt2 th
# SAMPLE_TEXT = [
#     "กขคง",
#     "จฉซ",
#     "ญดท",
#     "นบผห",
#     "ฟภมร",
#     "ลวศษ",
#     "ค่ามีไป",
#     "โว้และเธอ"
# ]   

# ----------------------- addtxt2 en
# SAMPLE_TEXT = [
#     "AaB",
#     "bicd",
#     "Eefg",
#     "HIm",
#     "jKLq",
#     "Nopv",
#     "QRrS",
#     "tuxy"
# ]    

 

FONT_SIZE = 64
# -------------------------------------------------------- for ori image ----------------------------------------------
# สร้างโฟลเดอร์แยกตามประเภท
categories = ["img_pre-Clean", "img_pre-Color", "img_pre-Noise", "img_pre-Blur", "img_pre-Perspective", "img_pre-Dot"]

for cate in categories:
    os.makedirs(os.path.join(OUTPUT_IMAGE_DIR, cate), exist_ok=True)
# -------------------------------------------------------- for ori image ----------------------------------------------

# --- Pre-processing
def apply_blur_fixed(img_np, ksize=5):
    """เพิ่มความเบลอตามขนาด Kernel ที่กำหนด"""
    return cv2.GaussianBlur(img_np, (ksize, ksize), 0)


def add_gaussian_noise(img_np):
    """เพิ่มสัญญาณรบกวนแบบ Gaussian (เม็ดทราย)"""
    row, col, ch = img_np.shape
    mean = 0
    var = 0.1
    sigma = var**0.5
    gauss = np.random.normal(mean, sigma, (row, col, ch))
    gauss = gauss.reshape(row, col, ch)
    noisy = img_np + gauss * 255
    return np.clip(noisy, 0, 255).astype(np.uint8)

def change_colors(img_np):
    """เปลี่ยนสีพื้นหลังและสีตัวอักษรแบบสุ่ม"""
    # สุ่มสี RGB (0-255)
    bg_color = [random.randint(200, 255) for _ in range(3)] # พื้นหลังสีอ่อน
    text_color = [random.randint(0, 100) for _ in range(3)] # ตัวอักษรสีเข้ม
    
    # แยกส่วนที่เป็นตัวอักษร (สีดำจากภาพต้นฉบับ)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    # สร้างภาพใหม่ตามสีที่สุ่ม
    result = np.full(img_np.shape, bg_color, dtype=np.uint8)
    result[mask == 0] = text_color # จุดที่ mask เป็น 0 (ตัวอักษร) ให้ใส่สี text_color
    
    return result

def add_perspective_distort(img_np):
    """บิดภาพให้ดูมีมิติ (Perspective Transformation)"""
    rows, cols, ch = img_np.shape
    
    # กำหนดจุด 4 จุดเดิม (มุมภาพ)
    pts1 = np.float32([[0, 0], [cols, 0], [0, rows], [cols, rows]])
    
    # สุ่มการบิดของจุด 4 จุดใหม่ (บิดได้ไม่เกิน 15% ของขนาดภาพ)
    d = min(rows, cols) * 0.15
    pts2 = np.float32([
        [random.uniform(0, d), random.uniform(0, d)],
        [cols - random.uniform(0, d), random.uniform(0, d)],
        [random.uniform(0, d), rows - random.uniform(0, d)],
        [cols - random.uniform(0, d), rows - random.uniform(0, d)]
    ])

    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    # ใส่ BorderValue เป็นสีพื้นหลัง (ขาว) เพื่อไม่ให้ขอบดำ
    distorted = cv2.warpPerspective(img_np, matrix, (cols, rows), borderValue=(255, 255, 255))
    return distorted

def add_salt_and_pepper(img_np):
    """เพิ่มจุดขาวดำกระจายทั่วภาพ (เหมือนเศษฝุ่นบนสแกนเนอร์)"""
    prob = 0.02 # สัดส่วนของ noise
    output = np.copy(img_np)
    # Salt (ขาว)
    num_salt = np.ceil(prob * img_np.size * 0.5)
    coords = [np.random.randint(0, i - 1, int(num_salt)) for i in img_np.shape]
    output[tuple(coords)] = 255
    # Pepper (ดำ)
    num_pepper = np.ceil(prob * img_np.size * 0.5)
    coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in img_np.shape]
    output[tuple(coords)] = 0
    return output


# --- Render ฟอนต์เป็นภาพ ---
def render_font_to_image(ttf_path, text, size):
    margin = 15
    start_time = time.time()

    # แปลง text เป็น list ของบรรทัดเสมอ
    if isinstance(text, list):
        lines = text
    else:
        lines = text.split("\n")

    # โหลดฟอนต์
    font = ImageFont.truetype(str(ttf_path), size)
    images = []
    for line in lines:
        if not line.strip():
            continue

        # วัดขนาดทีละบรรทัด
        dummy_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), line, font=font)

        # คำนวณ Bounding Box ของข้อความ (left, top, right, bottom)
        text_width  = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # คำนวณขนาดรูปภาพใหม่โดยรวม Margin
        img_width   = text_width  + (margin * 2)
        img_height  = text_height + (margin * 2)

        # สร้างภาพพื้นหลังสีขาว ต่อบรรทัด
        img = Image.new('RGB', (int(img_width), int(img_height)), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
    
        try:
            draw.text(
                # ลบ bbox[0] และ bbox[1] ออก เพื่อกำจัดขอบขาวส่วนเกินที่ติดมากับฟอนต์
                (margin - bbox[0], margin - bbox[1]),
                line,
                font=font,
                fill=(0, 0, 0)
            )
            images.append(img)
        except Exception as e:
            print(f"Error rendering '{line}' with {ttf_path.name}: {e}")
            continue
    
    end_time = time.time()    # 2. จับเวลาสิ้นสุด
    duration = end_time - start_time  # 3. คำนวณส่วนต่าง
    print(f"{ttf_path.name} | Render Time: {duration:.4f} seconds")
    return images  # list[PIL.Image]  — ความยาว = จำนวนบรรทัดที่ render ได้

# --- Main Process: วนลูปจัดการไฟล์ ---

print("Starting Font Processing...")

font_files = list(Path(INPUT_FONT_DIR).glob("*.ttf"))

for ttf_path in font_files:
    font_name = ttf_path.stem
    raw_imgs = render_font_to_image(ttf_path, SAMPLE_TEXT, FONT_SIZE)

    # ถ้าได้ list กลับมา ให้วนทีละภาพ
    if not isinstance(raw_imgs, list):
        raw_imgs = [raw_imgs]

    for line_idx, raw_img in enumerate(raw_imgs):

        # สร้างภาพต้นฉบับ (Clean)
        if raw_img is None: continue
        img_np = np.array(raw_img.convert("RGB"))


        # -------------------------------------------------------- for ori image ----------------------------------------------

        # 1. Clean
        Image.fromarray(img_np).save(f"{OUTPUT_IMAGE_DIR}/img_pre-Clean/{font_name}.png")
        
        # 2. Color
        color_img = change_colors(img_np)
        Image.fromarray(color_img).save(f"{OUTPUT_IMAGE_DIR}/img_pre-Color/{font_name}.png")
        
        # 3. Noise
        noise_img = add_gaussian_noise(img_np) 
        Image.fromarray(noise_img).save(f"{OUTPUT_IMAGE_DIR}/img_pre-Noise/{font_name}.png")
        
        # 4. Blur
        blur_img = apply_blur_fixed(img_np, ksize=5)
        Image.fromarray(blur_img).save(f"{OUTPUT_IMAGE_DIR}/img_pre-Blur/{font_name}.png")

        # 5. Perspective
        per_img = add_perspective_distort(img_np)
        Image.fromarray(per_img).save(f"{OUTPUT_IMAGE_DIR}/img_pre-Perspective/{font_name}.png")

        # 6. blackwhite dot
        per_img = add_salt_and_pepper(img_np)
        Image.fromarray(per_img).save(f"{OUTPUT_IMAGE_DIR}/img_pre-Dot/{font_name}.png")
        # -------------------------------------------------------- for ori image ----------------------------------------------


        # -------------------------------------------------------- for addtxt image ----------------------------------------------

        # os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt2-Clean-{line_idx}", exist_ok=True)
        # os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt2-Color-{line_idx}", exist_ok=True)
        # os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt2-Noise-{line_idx}", exist_ok=True)
        # os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt2-Blur-{line_idx}", exist_ok=True)
        # os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt2-Perspective-{line_idx}", exist_ok=True)
        # os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt2-Dot-{line_idx}", exist_ok=True)
        
        # # บันทึกแยกแต่ละแบบ
        # # 1. Clean
        # Image.fromarray(img_np).save(f"{OUTPUT_IMAGE_DIR}/addtxt2-Clean-{line_idx}/{font_name}.png")
        
        # # 2. Color
        # color_img = change_colors(img_np)
        # Image.fromarray(color_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt2-Color-{line_idx}/{font_name}.png")
        
        # # 3. Noise
        # noise_img = add_gaussian_noise(img_np) 
        # Image.fromarray(noise_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt2-Noise-{line_idx}/{font_name}.png")
        
        # # 4. Blur
        # blur_img = apply_blur_fixed(img_np, ksize=5)
        # Image.fromarray(blur_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt2-Blur-{line_idx}/{font_name}.png")

        # # 5. Perspective
        # per_img = add_perspective_distort(img_np)
        # Image.fromarray(per_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt2-Perspective-{line_idx}/{font_name}.png")

        # # 6. blackwhite dot
        # per_img = add_salt_and_pepper(img_np)
        # Image.fromarray(per_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt2-Dot-{line_idx}/{font_name}.png")
        # -------------------------------------------------------- for addtxt image ----------------------------------------------


print(f"\nFinished! All processed images are in: {OUTPUT_IMAGE_DIR}")