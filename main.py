import os
import json
import psycopg2
from typing import List
from dotenv import load_dotenv
from backend.database import save_font
from fastapi.middleware.cors import CORSMiddleware
from backend.match_endpoint import router as match_router 
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request

app = FastAPI()
app.include_router(match_router)
load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    print("เชื่อมต่อ:", DATABASE_URL[:30], "...")
    return conn

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                   "https://findfonts.vercel.app"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Endpoint: verify key Admin page ----
@app.post("/admin")
def admin(key: str = Form(...)):
    print(f"key = {key}")
    if key != "2026":
        raise HTTPException(status_code=403, detail="Access denied")
    return {"ok": True}
    
@app.get("/fontlist", response_class=HTMLResponse)
def fontlist():
    with open("Fontlist.html", encoding="utf-8") as f:
        return f.read()

#------- Endpoint: insert font to popularfont
@app.post("/downloadclicked")
async def insert_popularfont(request: Request):
    body_bytes = await request.body()
    font_name = body_bytes.decode("utf-8")
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO popular_fonts (font_name)
            VALUES (%s)
        """, (font_name,))
        conn.commit()
        conn.close()
        print(f"บันทึก {font_name} สำเร็จ")
    except Exception as e:
        print(f"Error insert popular font: {e}")
        raise
    return {"status": "success", "received": font_name}

# ---- Endpoint: search font ----
@app.get("/search")
def search_font():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("select font_name from fonts order by font_name")
        rows = cursor.fetchall()
        font_names = [row[0] for row in rows]
        cursor.close()
        conn.close()
        print(f"ดึงข้อมูล font สำเร็จ")
        return {
            "status": "success", 
            "data": font_names  
        }
    except Exception as e:
        print(f"Error search font: {e}")
        return {"status": "error", "message": {e}}
    
# ---- Endpoint: popular font ----
@app.get("/popular_font")
def popular_font():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("select font_name from popular_fonts where font_name in (select font_name from fonts) group by font_name order by count(font_name) desc limit 7")
        rows = cursor.fetchall()
        font_names = [row[0] for row in rows]
        cursor.close()
        conn.close()
        print(f"ดึงข้อมูล popular font สำเร็จ")
        print(font_names)
        return {
            "status": "success", 
            "data": font_names  
        }
    except Exception as e:
        print(f"Error select popular font: {e}")
        return {"status": "error", "message": {e}}

# ---- Endpoint: new font ----
@app.get("/new_font")
def new_font():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("select font_name from fonts where create_at >= now() - interval '7' day order by create_at desc ")
        rows = cursor.fetchall()
        font_names = [row[0] for row in rows]
        cursor.close()
        conn.close()
        print(f"ดึงข้อมูล new font สำเร็จ")
        print(font_names)
        return {
            "status": "success", 
            "data": font_names  
        }
    except Exception as e:
        print(f"Error select new font: {e}")
        return {"status": "error", "message": {e}}
    
# ---- Endpoint: get all font ----
@app.get("/fonts")
def all_font():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("select font_name from fonts order by font_name")
        rows = cursor.fetchall()
        font_names = [row[0] for row in rows]
        cursor.close()
        print(f"ดึงข้อมูล font สำเร็จ")
        return {
        "total": len(font_names),
        "fonts": font_names
        }
    except Exception as e:
        print(f"Error search font: {e}")
        return {"status": "error", "message": {e}}
    
# ----------------------------------------------------------- Endpoint import ------------------------------------------------------------

# ---- Endpoint: Upload font  ----
# file
@app.post("/upload-font")
async def upload_font(
    file: UploadFile = File(...), 
    font_name: str = Form(...)   
    ):
    font_name = os.path.splitext(file.filename)[0] 
    try:
        save_font(font_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ประมวลผลไม่สำเร็จ: {str(e)}")
    return {
        "message": "บันทึกสำเร็จ",
        "font_name": font_name
    }

# folder
@app.post("/upload-fonts")
async def upload_fonts(
    files: List[UploadFile] = File(...),
    font_names: List[str] = Form(...),
    ):
    if len(files) != len(font_names):
        raise HTTPException(status_code=400, detail="files และ font_names ต้องมีจำนวนเท่ากัน")
    print(f"font folder: {font_names}")
    async def generate():
        for file, font_name in zip(files, font_names):
            font_name = os.path.splitext(os.path.basename(file.filename))[0]
            print(f"font name: {font_name}")
            save_font(font_name)
            yield json.dumps({
                "font_name": font_name
            }) + "\n"

    return StreamingResponse(generate(), media_type="text/plain")

# ---- Health check ----
@app.get("/")
def root():
    return {"status": "ok"}

#-------loadDB-------
@app.get("/ready")
def ready():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "ok"}
    except:
        raise HTTPException(status_code=503)