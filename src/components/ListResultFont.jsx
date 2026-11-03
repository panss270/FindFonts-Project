import { useEffect } from "react";
import "./ListResultFont.css";
import { getApiUrl } from "../config";
import "../../otherfont.css";


// รายชื่อฟอนต์ที่มีใน otherfont.css
const LOCAL_FONTS = new Set([
  'EkkamaiVibe', 'FkLindo', 'JaoLatte',
  'nura_chaba', 'nura_nemomo', 'RDKonmek',
  'SOV_HuaHliam', 'SOV_HuaHmun', 'SOV_HuaHyak',
  'SOV_Pabmum', 'SOV_Rajbutr', 'SOV_Rajbutri',
  'SOV_Saifai', 'SOV_Sontna', 'SOV_Swadee',
  'TorsilpKhitthuengThoe', 'TorsilpLamun', 'TorsilpThepniyaiLight',
  'Royal Institute of Siam New'
]);

const getDisplayFontFamily = (name) => {
  if (!name) return "sans-serif";
  
  const fontName = name.replace(/\.ttf$/gi, "").trim();
  
  // local font → คืนชื่อตรงๆ ห้ามแปลง _ หรือ -
  if (LOCAL_FONTS.has(fontName)) return fontName;

  // Google Font
  return fontName
    .replace(/-Regular$/gi, "")
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .trim();
};

const getGoogleFontUrl = (name) => {
  if (!name) return "#";

  const cleanName = name
    .replace(/-Regular|\.ttf/gi, "")
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .trim();

  return `https://fonts.google.com/specimen/${cleanName.replace(/ /g, "+")}`;
};



const ListResultFont = ({ font, text ,onDownload}) => {
const handleDownloadClick = async (fontName) => {
    window.open(getGoogleFontUrl(fontName), "_blank");
    try {
        await fetch(getApiUrl("/downloadclicked"), {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: fontName,
        });
        if (onDownload) onDownload();
    } catch (error) {
        console.error("Error:", error);
    } 
  };

   useEffect(() => {
    if (!font?.name) return;

    const fontName = font.name.replace(/\.ttf$/gi, "").trim();
    // console.log("fontName:", fontName, "| inLocal:", LOCAL_FONTS.has(fontName)); // ← เพิ่มตรงนี้

    // ถ้ามีใน otherfont.css → ไม่ต้องโหลดอะไรเพิ่ม
    if (LOCAL_FONTS.has(fontName)) return;

    // clean สำหรับส่ง Google Fonts
    const googleName = fontName
      .replace(/-Regular$/gi, "")
      .replace(/_/g, " ")
      .replace(/-/g, " ")
      .trim(); // "Sarabun"

    // ถ้าไม่มี → ไปโหลดจาก Google Fonts
    const fontId = `font-${googleName.replace(/ /g, "-")}`;
    if (document.getElementById(fontId)) return;

    const link = document.createElement("link");
    link.href = link.href = `https://fonts.googleapis.com/css2?family=${googleName.replace(/ /g, "+")}&display=swap`;
    link.rel = "stylesheet";
    link.id = fontId;
    document.head.appendChild(link);

    return () => {
      if (document.getElementById(fontId)) {
        document.head.removeChild(link);
      }
    };
  }, [font?.name]);

  return (
    
    <div className="result-card">

      <div
        className="font-preview-box"
        style={{ fontFamily: `${getDisplayFontFamily(font?.name)}, sans-serif` }}
      >
       {getDisplayFontFamily(font?.name)?.[0] ?? "A"}{getDisplayFontFamily(font?.name)?.[0]?.toLowerCase() ?? "a"}
      </div>

      <div className="font-info">

        <p
          className="test-text"
          style={{ fontFamily: `${getDisplayFontFamily(font?.name)}, sans-serif` }}
        >
          {text || "The Art of Typography ศิลปะแห่งการออกแบบตัวอักษร"}
        </p>

        <p className="font-name">
          {getDisplayFontFamily(font?.name)}
        </p>

        {font?.similarity && (
          <p className="similarity-text">
            ความคล้าย {(font.similarity * 100).toFixed(1)}%
          </p>
        )}

      
      </div>

      <button
          className="downloads"
          onClick={() => handleDownloadClick(font.name)}
      >
          download
      </button>
    </div>
    
  );
};

export default ListResultFont;