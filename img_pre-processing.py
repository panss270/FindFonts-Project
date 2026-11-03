import os
import cv2
import time
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

INPUT_FONT_DIR = "../FontData33/"    
OUTPUT_IMAGE_DIR = "../img_preprocessing-th/" 
print(f"มีโฟลเดอร์นี้อยู่จริงไหม?: {os.path.exists(INPUT_FONT_DIR)}")
print(f"มีโฟลเดอร์นี้อยู่จริงไหม?: {os.path.exists(OUTPUT_IMAGE_DIR)}")
# SAMPLE_TEXT = [
    # "กขคง",
    # "จฉซ",
    # "ญดท",
    # "นบผห",
    # "ฟภมร",
    # "ลวศษ",
    # "ค่ามีไป",
    # "โว้และเธอ"
# ]   
SAMPLE_TEXT = [
    "AaB",
    "bicd",
    "Eefg",
    "HIm",
    "jKLq",
    "Nopv",
    "QRrS",
    "tuxy"
]    
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
# SAMPLE_TEXT = [
    # "AaBbCcDdEeFfGg",
    # "HhIiJjKkLlMm",
    # "NnOoPpQqRrSs",
    # "TtUuVvWwXxYyZz",
    # "Hamburgevons",
    # "SunDaymOndAy",
    # "Phra Nakhon Si Ayutthaya",
    # "0123456789"
# ]    

FONT_SIZE = 64

# --- Pre-processing
def apply_blur_fixed(img_np, ksize=5):
    return cv2.GaussianBlur(img_np, (ksize, ksize), 0)


def add_gaussian_noise(img_np):
    row, col, ch = img_np.shape
    mean = 0
    var = 0.1
    sigma = var**0.5
    gauss = np.random.normal(mean, sigma, (row, col, ch))
    gauss = gauss.reshape(row, col, ch)
    noisy = img_np + gauss * 255
    return np.clip(noisy, 0, 255).astype(np.uint8)

def change_colors(img_np):
    bg_color = [random.randint(200, 255) for _ in range(3)] 
    text_color = [random.randint(0, 100) for _ in range(3)]
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    result = np.full(img_np.shape, bg_color, dtype=np.uint8)
    result[mask == 0] = text_color
    return result

def add_perspective_distort(img_np):
    rows, cols, ch = img_np.shape
    pts1 = np.float32([[0, 0], [cols, 0], [0, rows], [cols, rows]])
    d = min(rows, cols) * 0.15
    pts2 = np.float32([
        [random.uniform(0, d), random.uniform(0, d)],
        [cols - random.uniform(0, d), random.uniform(0, d)],
        [random.uniform(0, d), rows - random.uniform(0, d)],
        [cols - random.uniform(0, d), rows - random.uniform(0, d)]
    ])

    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    distorted = cv2.warpPerspective(img_np, matrix, (cols, rows), borderValue=(255, 255, 255))
    return distorted

def add_salt_and_pepper(img_np):
    prob = 0.02
    output = np.copy(img_np)
    num_salt = np.ceil(prob * img_np.size * 0.5)
    coords = [np.random.randint(0, i - 1, int(num_salt)) for i in img_np.shape]
    output[tuple(coords)] = 255
    num_pepper = np.ceil(prob * img_np.size * 0.5)
    coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in img_np.shape]
    output[tuple(coords)] = 0
    return output

# --- Render ฟอนต์เป็นภาพ ---
def render_font_to_image(ttf_path, text, size):
    margin = 15
    start_time = time.time()
    if isinstance(text, list):
        lines = text
    else:
        lines = text.split("\n")

    font = ImageFont.truetype(str(ttf_path), size)
    images = []
    for line in lines:
        if not line.strip():
            continue

        dummy_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width  = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        img_width   = text_width  + (margin * 2)
        img_height  = text_height + (margin * 2)
        img = Image.new('RGB', (int(img_width), int(img_height)), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            draw.text(
                (margin - bbox[0], margin - bbox[1]),
                line,
                font=font,
                fill=(0, 0, 0)
            )
            images.append(img)
        except Exception as e:
            print(f"Error rendering '{line}' with {ttf_path.name}: {e}")
            continue
    
    end_time = time.time() 
    duration = end_time - start_time 
    print(f"{ttf_path.name} | Render Time: {duration:.4f} seconds")
    return images

# --- Main Process ---
print("Starting Font Processing...")
font_files = list(Path(INPUT_FONT_DIR).glob("*.ttf"))
for ttf_path in font_files:
    font_name = ttf_path.stem
    raw_imgs = render_font_to_image(ttf_path, SAMPLE_TEXT, FONT_SIZE)
    if not isinstance(raw_imgs, list):
        raw_imgs = [raw_imgs]

    for line_idx, raw_img in enumerate(raw_imgs):
        if raw_img is None: continue
        img_np = np.array(raw_img.convert("RGB"))
        os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt-Clean-{line_idx}", exist_ok=True)
        os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt-Color-{line_idx}", exist_ok=True)
        os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt-Noise-{line_idx}", exist_ok=True)
        os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt-Blur-{line_idx}", exist_ok=True)
        os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt-Perspective-{line_idx}", exist_ok=True)
        os.makedirs(f"{OUTPUT_IMAGE_DIR}/addtxt-Dot-{line_idx}", exist_ok=True)
        Image.fromarray(img_np).save(f"{OUTPUT_IMAGE_DIR}/addtxt-Clean-{line_idx}/{font_name}.png")
        color_img = change_colors(img_np)
        Image.fromarray(color_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt-Color-{line_idx}/{font_name}.png")
        noise_img = add_gaussian_noise(img_np) 
        Image.fromarray(noise_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt-Noise-{line_idx}/{font_name}.png")
        blur_img = apply_blur_fixed(img_np, ksize=5)
        Image.fromarray(blur_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt-Blur-{line_idx}/{font_name}.png")
        per_img = add_perspective_distort(img_np)
        Image.fromarray(per_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt-Perspective-{line_idx}/{font_name}.png")
        per_img = add_salt_and_pepper(img_np)
        Image.fromarray(per_img).save(f"{OUTPUT_IMAGE_DIR}/addtxt-Dot-{line_idx}/{font_name}.png")

print(f"\nFinished! All processed images are in: {OUTPUT_IMAGE_DIR}")