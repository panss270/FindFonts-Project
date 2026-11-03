import React, {useRef, useState, useCallback,useEffect } from 'react'
import "./Detail.css";
import { iconUpload,search } from '../../assets';
import ListResultFont from '../ListResultFont';
import { getApiUrl } from '../../config';


// แปลง Blob/File เป็น Base64 string โดยใช้ FileReader คืนค่าเป็น Promise ใช้สำหรับเก็บรูปไว้ใน memory โดยไม่ต้องพึ่ง URL
const blobToBase64 = (blob) =>
  new Promise((resolve) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.readAsDataURL(blob);
  });
const clamp = (v, min, max) => Math.min(Math.max(v, min), max);

// ตรวจว่าบริเวณที่ crop มีตัวอักษรอยู่จริงหรือไม่ โดยใช้ Sobel filter หา edge ในภาพ ถ้า 
// edge density ≥ 3% ถือว่าผ่าน (มีตัวอักษร) ก่อนส่งไป backend
function checkEdgeDensity(blob) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const MAX = 256;
      const scale = Math.min(MAX / img.width, MAX / img.height, 1);
      const W = Math.round(img.width * scale);
      const H = Math.round(img.height * scale);

      const cv = document.createElement("canvas");
      cv.width = W; cv.height = H;
      const ctx = cv.getContext("2d");
      ctx.drawImage(img, 0, 0, W, H);

      const { data } = ctx.getImageData(0, 0, W, H);
      const gray = new Uint8Array(W * H);
      for (let i = 0; i < W * H; i++) {
        const r = data[i * 4], g = data[i * 4 + 1], b = data[i * 4 + 2];
        gray[i] = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
      }

      const Gx = [-1,0,1, -2,0,2, -1,0,1];
      const Gy = [-1,-2,-1, 0,0,0, 1,2,1];
      let edgeCount = 0;
      const THRESHOLD = 15;

      for (let y = 1; y < H - 1; y++) {
        for (let x = 1; x < W - 1; x++) {
          let gx = 0, gy = 0;
          for (let ky = -1; ky <= 1; ky++) {
            for (let kx = -1; kx <= 1; kx++) {
              const px = gray[(y + ky) * W + (x + kx)];
              const ki = (ky + 1) * 3 + (kx + 1);
              gx += px * Gx[ki];
              gy += px * Gy[ki];
            }
          }
          if (Math.sqrt(gx * gx + gy * gy) > THRESHOLD) edgeCount++;
        }
      }

      const edgeDensity = edgeCount / ((W - 2) * (H - 2));
      resolve({ passed: edgeDensity >= 0.03, edgeDensity });
      URL.revokeObjectURL(img.src);
    };
    img.src = URL.createObjectURL(blob);
  });
}

//===============================================
// COMPONENT - Header
// แสดงหัวข้อและ subtitle ของหน้า
// ช่อนตอน step = "results"
//===============================================
function PageHeader({ title, subtitle }) {
  return (
    <div className="header-section-fixed">
      <h1 className="header-title">{title}</h1>
      <p className="header-subtitle">{subtitle}</p>
    </div>
  );
}

//==============================================
// COMPONENT - WarnBanner
// แถบเตือนสีเหลือง แสดงเมื่อไม่พบตัวอักษร
// props : massage (ข้อความ) , onDismiss (ปิด banner)
//==================================================
function WarnBanner({ message, onDismiss }) {
  return (
    <div className="warn-banner">
      <span className="warn-icon" role="img" aria-label="warning">⚠️</span>
      <div className="warn-content">
        <p className="warn-title">
          No text found in the image
        </p>
        <p className="warn-message">{message}</p>
      </div>
      <button onClick={onDismiss} className="warn-close-btn" aria-label="Close warning">x</button>
    </div>
  );
}

//===================================================
// COMPONENT - UploadZone
// หน้าแรกสำหรับรับไฟล์รูปภาพ
// รองรับ: คลิกเลือกไฟล์ และ drage & drop
// props: onFile (callback เมื่อได้ไฟล์)
//===================================================
function UploadZone({ onFile }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const handleDrop = (e) => {
    e.preventDefault(); 
    setDragging(false);
    e.stopPropagation();
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  };
  return (
    <div
      className = {`upload-zone ${dragging ? 'dragging' : ''}`}
      onClick={() => inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); e.stopPropagation(); }}
      onDragLeave={(e) => {
        if (e.currentTarget.contains(e.relatedTarget)) return;
        setDragging(false);
      }}
      onDrop={handleDrop}
    >
      <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png" className="upload-zone-input"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) {
            onFile(f);
            e.target.value = null;
          }
        }}/>
      <div className="upload-icon">🖼️</div>
      <p className="upload-text">
        Drag and drop an <span className="upload-link">image here</span>
      </p>
      <p className="upload-hint">PNG · JPG</p>
    </div>
  );
}

//=====================================================
// COMPONENT - CropCanvas
// วาดรูปบน canvas และให้ user ลากเลือกกรอบ crop
// props:
//    imageSrc  - URL ของรูปต้นฉบับ
//    onConfirm - callback เมื่อกด Identify font (ส่ง blob)
//    onBack    - callback เมื่อกด reset
//    checking  - true ขณะกำลัง checkEdgeDensity (ล็อก UI)
//    onNewFile - callback เมื่อ upload ไฟล์ใหม่หน้านี้
// ======================================================
function CropCanvas({ imageFile, onConfirm, onBack, checking ,onNewFile}) {
  const canvasRef = useRef(null);
  const inputRef = useRef(null);
  const drag = useRef(null);

  const [imgEl, setImgEl] = useState(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [box, setBox] = useState(null);
   
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;

    const onTouchStart = (e) => { e.preventDefault(); onMD(e); };
    const onTouchMove  = (e) => { e.preventDefault(); onMM(e); };
    const onTouchEnd   = ()  => { onMU(); };

    cv.addEventListener("touchstart",  onTouchStart, { passive: false });
    cv.addEventListener("touchmove",   onTouchMove,  { passive: false });
    cv.addEventListener("touchend",    onTouchEnd,   { passive: false });

    return () => {
      cv.removeEventListener("touchstart",  onTouchStart);
      cv.removeEventListener("touchmove",   onTouchMove);
      cv.removeEventListener("touchend",    onTouchEnd);
    };
  }, [imgEl]);

  useEffect(() => {
    if (!imageFile || !(imageFile instanceof File || imageFile instanceof Blob)) return;
    
    let cancelled = false;
    const url = URL.createObjectURL(imageFile);
    const img = new Image();

    img.onload = () => {
      if (!cancelled) {
        setImgEl(img);
        setBox(null);
      }
      URL.revokeObjectURL(url);
    };
    img.onerror = ()=>{
      console.error("img faild to load");
      URL.revokeObjectURL(url);
    };
    img.src = url;
    
    return () => { 
      cancelled = true;
      setImgEl(null);
    };
}, [imageFile]);
  

  useEffect(() => {
    if (!imgEl || !canvasRef.current) return;          
    if (!imgEl.complete || !imgEl.naturalWidth) return;
    const cv = canvasRef.current;
    
    
    const rect = cv.getBoundingClientRect();
    const maxW = Math.floor(rect.width);
    const maxH = Math.floor(rect.height);

    if (maxW === 0 || maxH === 0) return;

    if (!imgEl.width || !imgEl.height) return;

    const s = Math.min(maxW / imgEl.width, maxH / imgEl.height, 1);
    setScale(s);
    setOffset({ x: (maxW - imgEl.width * s) / 2, y: (maxH - imgEl.height * s) / 2 });
    setBox(null);
  }, [imgEl]);


 useEffect(() => {
    if (!imgEl || !canvasRef.current) return;
    if (!imgEl.complete || !imgEl.naturalWidth) return;
    const cv = canvasRef.current;
    const ctx = cv.getContext("2d");
    const rect = cv.getBoundingClientRect();         
    if (rect.width === 0 || rect.height === 0) return;
    
    cv.width = Math.floor(rect.width);
    cv.height = Math.floor(rect.height);
    ctx.clearRect(0, 0, cv.width, cv.height);
    
    ctx.drawImage(imgEl, offset.x, offset.y, imgEl.width * scale, imgEl.height * scale);

    if (box) {
      ctx.fillStyle = "rgba(0,0,0,.55)";
      ctx.fillRect(0, 0, cv.width, box.y);
      ctx.fillRect(0, box.y, box.x, box.h);
      ctx.fillRect(box.x + box.w, box.y, cv.width - box.x - box.w, box.h);
      ctx.fillRect(0, box.y + box.h, cv.width, cv.height - box.y - box.h);
      ctx.strokeStyle = "#c084fc"; ctx.lineWidth = 2; ctx.setLineDash([6, 3]);
      ctx.strokeRect(box.x, box.y, box.w, box.h); ctx.setLineDash([]);
      [[box.x,box.y],[box.x+box.w,box.y],[box.x,box.y+box.h],[box.x+box.w,box.y+box.h]]
        .forEach(([hx,hy]) => { ctx.fillStyle="#c084fc"; ctx.fillRect(hx-5,hy-5,10,10); });
    } else {
      ctx.fillStyle = "rgba(0,0,0,.35)"; ctx.fillRect(0,0,cv.width,cv.height);
      ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
      ctx.font = "16px 'Sora',sans-serif"; 
      ctx.textAlign = "center";
      ctx.fillText("Drag to select text area.", cv.width/2, cv.height/6);
    }
}, [imgEl, scale, offset, box]);

  
  const getPos = (e) => {
    const cv = canvasRef.current, r = cv.getBoundingClientRect();
    return { 
      x: (e.clientX ?? e.touches?.[0]?.clientX) - r.left,
      y: (e.clientY ?? e.touches?.[0]?.clientY) - r.top 
    };
  };

  const onMD = (e) => { const p = getPos(e); drag.current = { startX: p.x, startY: p.y }; };
  
  const onMM = (e) => {
    if (!drag.current) return;
    const p = getPos(e), { startX, startY } = drag.current;
    setBox({ 
      x: Math.min(p.x,startX), y: Math.min(p.y,startY),
      w: Math.abs(p.x-startX),  h: Math.abs(p.y-startY) 
    });
  };

  const onMU = () => { drag.current = null; };


  const handleConfirm = () => {
    if (!box || !imgEl) return;

    const imgLeft   = offset.x;
    const imgTop    = offset.y;
    const imgRight  = offset.x + imgEl.width  * scale;
    const imgBottom = offset.y + imgEl.height * scale;

    if (
      box.x < imgLeft  ||
      box.y < imgTop   ||
      box.x + box.w > imgRight  ||
      box.y + box.h > imgBottom
    ) {
      alert("กรุณาเลือกพื้นที่ภายในรูปภาพเท่านั้น");
      return;
    }

    const PAD = 20; 
    const ix = (box.x - offset.x) / scale;
    const iy = (box.y - offset.y) / scale;
    const iw = box.w / scale;
    const ih = box.h / scale;

    const displayCanvas = document.createElement("canvas");
    displayCanvas.width  = Math.round(iw);
    displayCanvas.height = Math.round(ih);
    displayCanvas.getContext("2d").drawImage(
      imgEl, ix, iy, iw, ih, 0, 0, Math.round(iw), Math.round(ih)
    );
    const displayBase64 = displayCanvas.toDataURL("image/png"); 

    const px = clamp(ix - PAD, 0, imgEl.width);
    const py = clamp(iy - PAD, 0, imgEl.height);
    const pw = clamp(iw + PAD * 2, 1, imgEl.width - px);
    const ph = clamp(ih + PAD * 2, 1, imgEl.height - py);

    const MAX = 1200;
    const cropScale = Math.min(1, MAX / Math.max(pw, ph));
    const finalW = Math.round(pw * cropScale);
    const finalH = Math.round(ph * cropScale);

    const tmp = document.createElement("canvas");
    
    tmp.width  = finalW;  
    tmp.height = finalH;  
    tmp.getContext("2d").drawImage(imgEl, px, py, pw, ph, 0, 0, finalW, finalH);
    tmp.toBlob((blob) => { if (blob) onConfirm(blob, displayBase64); }, "image/png");
  };

  const handleImageFile = (file) => {
  if (file && file.type.startsWith('image/')) {
    if (onNewFile) onNewFile(file);
    setBox(null); 
  }
};

  const disabled = !box || box.w < 10 || box.h < 10 || checking;
 
  return (
    <div className="crop-container">
      <canvas ref={canvasRef}
        className={checking ? "cursor-wait" : "cursor-crosshair"}
        width={560} 
        height={350}
        onMouseDown={onMD} onMouseMove={onMM} onMouseUp={onMU}

        // ---  Drag & Drop  ---
        onDragOver={(e)   => { e.preventDefault(); e.stopPropagation(); }}
        onDrop={(e) => {
          e.preventDefault(); e.stopPropagation();
          handleImageFile(e.dataTransfer.files?.[0]);
        }}
      />
      <div className="crop-actions">
        <input
          ref={inputRef} 
          type="file" 
          accept="image/*" 
          className="hidden" 
          style={{ display: 'none' }}
          onChange={(e) => { 
            const f = e.target.files?.[0]; 
            if (f) {
          
              handleImageFile(f); 
              e.target.value =null;
            }
          }}
           />
        <button 
          onClick={() => inputRef.current.click()} 
          className="btn-base btn-upload" 
          disabled={checking}>

          <img 
          src={iconUpload} 
          alt="upload" 
          className="upload-picture" 
          />
          Upload new</button>
        <button onClick={handleConfirm} disabled={disabled} className="btn-base btn-identify">
          <img 
          src={search} 
          alt="search" 
          className="search-picture" 
          />
          Identify font
        </button>
      </div>
    </div>
  );
}


// ══════════════════════════════════════════════════════════
//  Main component - ImageCropModal
//  State machin ควบคุมการแสดงผลแต่ละ step
//
//  step flow: Upload -> crop -> checking -> loading -> results
//                   
//         ครอบรูปไม่ผ่าน crop(warn)        loading ไม่ผ่าน error
// ══════════════════════════════════════════════════════════
export default function ImageCropModal() {
  const [step, setStep]         = useState("upload");
  const [imageFile, setImageFile] = useState(null); 
  const [results, setResults]   = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [warn, setWarn]         = useState(null);
  const [croppedImage, setCroppedImage] = useState(null); 
  const [ocrText, setOcrText] = useState("");            
 
  const originalFileRef = useRef(null); 
  const lastSuccessRef = useRef(null);  
  const originalBase64Ref = useRef(null);

  // ── subtitle แต่ละ step ──────────────────────────
  const subtitle = {
    upload:  {text:"Share an image and we'll find the best matching font.",
              class:"header-subtitle "
    },
    crop:  {text:"Select your preferred placement.",
            class:"header-subtitlecrop"},  
    checking: "checking",
    loading:  "loading",
    results:  `พบ ${results.length} ฟอนต์ที่ใกล้เคียง`,
    error:    "error",
  }[step] ?? "";

  //-------รับไฟล์จาก UploadZone-----------------
  const handleFile = (file) => {

    if (!["image/jpeg", "image/png"].includes(file?.type)) {
      alert("รองรับเฉพาะไฟล์ JPG และ PNG เท่านั้น");
      return;
    }
    const MAX_SIZE = 2 * 1024 * 1024; // 3MB

    if (file.size > MAX_SIZE) {
      alert("ไฟล์รูปภาพที่มีขนาดเกินกว่า 2 MB");
      return;
    }

    originalFileRef.current = file; 
    blobToBase64(file).then(b64 => {
      originalBase64Ref.current = b64;
    });
    setImageFile(file);
    setStep("crop");
  };

  //-------รับไฟล์ใหม่จากหน้า crop อัปเดต ref ล้าง warn และ results-----------------
  const handleNewFileFromCrop = (file)=>{
    if (!["image/jpeg", "image/png"].includes(file?.type)) {
      alert("รองรับเฉพาะไฟล์ JPG และ PNG เท่านั้น");
      return;
    }
    if (!file) return;
    const MAX_SIZE = 2 * 1024 * 1024; 

    if (file.size > MAX_SIZE) {
      alert("ไฟล์ใหญ่เกิน 2MB");
      return;
    }
   
    originalFileRef.current = file; 
    blobToBase64(file).then(b64 => {
      originalBase64Ref.current = b64; 
    });

    setImageFile(file);
    setWarn(null);
    setResults([]);
  };

  const handleCropConfirm = useCallback(async (blob, displayBase64) => {
  
    // 1. แปลง Blob เป็นรูปภาพล่าสุด
    if(!blob) return; 

      // ── LAYER 1:  — ตรวจ edge density (frontend) ──────────
      setStep("checking");
      const { passed, edgeDensity } = await checkEdgeDensity(blob);

  
        if (!passed) {
          setWarn(
            `[Layer1] edge density ${(edgeDensity * 100).toFixed(1)}% ต่ำเกินไป`
          );
          setStep("crop");
          return;
        }

    // ── LAYER 2: - กำลังโหลด loading... (backend) ─────────
    setStep("loading");
    try {
      // console.log("BLOB size:", blob.size, "| type:", blob.type);
      const formData = new FormData();
      formData.append("file", blob, "crop.png");
      const res = await fetch(getApiUrl("/match"),{
        method:"POST", 
        body:formData 
      });

      //  ป้องกัน parse ล้มเหลว
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
          const msg = typeof data?.detail === "string" ? data.detail : "";

          //  console.log("STATUS:", res.status, "| DETAIL:", data?.detail, "| FULL DATA:", data);
            if (res.status === 422) {
                const isNoText = msg.includes("NO_TEXT"); 
                if (isNoText || msg.includes("NO_CROP")) {
                  setWarn("ไม่พบตัวอักษรในภาพ — ลองเลือกบริเวณที่มีตัวอักษรชัดเจนกว่านี้");
                } else {
                  setWarn("Backend: 422 — รูปแบบไฟล์หรือข้อมูลไม่ถูกต้อง");
                }
                setStep("crop");
                return;
            }

          throw new Error(msg || `Server error ${res.status}`);
      }
      setCroppedImage(displayBase64);
      lastSuccessRef.current = originalFileRef.current;
      setResults(data.matches ?? data.results ?? data);
      setStep("results");

    } catch (err) {
      // console.log(err);
      setErrorMsg(err?.message || "เกิดข้อผิดพลาด");
      setStep("error");
        }
  }, []);

  //-----รีเซ็ตทุกอย่าง กลับหน้า upload-------
  const reset = () => {
     if (imageFile) {
      URL.revokeObjectURL(imageFile);
    }

    setCroppedImage(null); 
    setStep("upload");
    setImageFile(null);     
    setResults([]);
    setErrorMsg("");
    setWarn(null);
    lastSuccessRef.current = null;
  };

  
  
  //-----กลับหน้า crop จากหน้า results-------
  const goBackToCrop = () => {
    setResults([]);
    setWarn(null);
    setOcrText("");
    if (originalBase64Ref.current) {
      fetch(originalBase64Ref.current)
        .then(r => r.blob())
        .then(blob => {
          const file = new File([blob], "original.png", { type: "image/png" });
          setImageFile(file);
          setStep("crop");
        });
    }else {
      setStep("crop");
    }  
  };
  
  // ============================================
  // RENDER
  // =============================================
  return (
    <>
    <div className="detail-page">
    {step !== "results"&&(
      <PageHeader 
            title="Find Font"
            subtitle={subtitle.text}
      />
    )}     
      <div className="modal-overlay">
        <div className={`modal-container ${step === "results" ? "modal-container-results" : "modal-container-home"}`}>
        
          {warn && step === "crop" && (
            <div style={{ marginBottom:16 }}>
              <WarnBanner message={warn} onDismiss={() => setWarn(null)} />
            </div>
          )}
          {step === "upload" && <UploadZone onFile={handleFile} />}

          {(step === "crop" || step === "checking") && (
            <div className="crop-wrapper">
              <CropCanvas
                key={imageFile ? `${imageFile.name}-${imageFile.lastModified}` : "no-file"}
                imageFile={imageFile}
                onConfirm={handleCropConfirm}
                onBack={reset}
                checking={step === "checking"}
                onNewFile={handleNewFileFromCrop}
              />
            </div>
          )}
          {step === "loading" && (
            <div style={{ height:250 }}>
              <div className="loader-container">
                  
                  <div style={{
                      marginTop:10,
                      marginBottom: 10,
                      display: "flex",
                      justifyContent: "center"
                    }}
                  >
                    <div className="loadingicon"></div>
                  </div>

                  <p className="loader-text">
                  Loading.....
                  </p>                
              </div>
            </div>
          )}
          {step === "results" && (
            <>
            <div className="results-page-wrapper"> 
              <div className="summary-block-white">
                <div className="summary-top">
                  <span className="text-resultfor">Result for</span>
                  {croppedImage && (
                    <img src={croppedImage} alt="crop" className="crop-image" />
                  )}
                  <button onClick={goBackToCrop} className="btn-back-to-image">Back to image</button>
                </div>
                <input 
                  className="ocr-edit-input"
                  value={ocrText} 
                  onChange={(e) => setOcrText(e.target.value.slice(0,100))} 
                  placeholder="Type something..."
                />
                <div className ="results-content ">
                <div className="results-list">
                {results.map((f, i) => (
                  <ListResultFont key={i} font={f} text={ocrText} />
                ))}
                </div>
                </div>
              </div>
            </div>    
            </>    
          )}
          {step === "error" && (
            <div style={{ height:250 }}>
            <div className="error-container">
              <p className="error-text">{errorMsg}</p>
              <button onClick={reset} className="btn-base btn-identify mt-16">Please try again.</button>
            </div>
            </div>
          )}
        </div>
      </div>
      </div>
    </>
  );
}