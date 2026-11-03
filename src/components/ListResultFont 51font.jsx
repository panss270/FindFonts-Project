import { useEffect, useState } from "react";
import "./ListResultFont.css";
import { getApiUrl } from "../config";
import { loadCustomFonts } from '../fonts';


// ฟังก์ชันสำหรับเช็คว่าเป็นฟอนต์ไทยนอกคลัง Google Fonts หรือไม่
const isCustomThaiFont = (cleanName) => {
   const name = cleanName.toLowerCase();
   
   // 1. เช็คถ้านามสกุล/ชื่อมีภาษาไทย ตัวอย่าง: "ทอศิลป์", "นิทรา"
   const hasThaiCharacter = /[\u0e00-\u0e7f]/i.test(cleanName);
  
   // 2. ดักจับ Keyword ขึ้นต้นของค่ายฟอนต์ไทยยอดฮิตที่ไม่มีใน Google Fonts
   const thaiPrefixes = [
    "sov", "torsi", "rd", "nura", "jao", "ekkamai", "fk", 
    "fc", "iannnn", "upc", "ps", "sp", "tx", "th", "rsu"
  ];
  const hasThaiPrefix = thaiPrefixes.some(prefix => name.startsWith(prefix));

  // 3. ฟอนต์ไทยชอบตั้งชื่อแบบ CamelCase แปลกๆ (เช่น JaoLatte, RDKonmek, FkLindo) 
  // ถ้าไม่ใช่ฟอนต์ภาษาอังกฤษมาตรฐานทั่วไป และเข้าเงื่อนไขด้านบน ให้ตีเป็นฟอนต์ไทยทั้งหมด
  return hasThaiCharacter || hasThaiPrefix;
};

const getFontFamily = (name) => {
  if (!name) return "sans-serif";

  // ตัดนามสกุลไฟล์ยอดฮิตออกให้หมด
  const clean = name
    .replace(/(Regular|-Regular|-Bold|-Italic|\.ttf|\.otf|\.woff|\.woff2)/gi, "")
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .trim();
  return clean || "sans-serif";
};

const F0NT_SLUG_OVERRIDES = {
  "torsilpthepniyailight": "torsilp-thepniyai",
  "torsilpthepniyai":      "torsilp-thepniyai",
  "torsilplamun":          "torsilp-lamun",
  "torsilpkhitthuengthoe": "torsilp-khitthueng-thoe",
  "nurachaba":             "nura-chaba-2",  
  "ekkamaivibe":           "ekkamai-vibe",
};

// ฟังก์ชันแยกแยะฟอนต์: ถ้าไม่ใช่ Google Font ให้ส่งไป f0nt.com
const getFontDownloadUrl = (fontName) => {
  if (!fontName) return "#";
  const cleanName = getFontFamily(fontName);


  // key สำหรับ lookup: lowercase ไม่มีช่องว่าง
  const lookupKey = cleanName.toLowerCase().replace(/ /g, "");
  const urlSlug = cleanName.toLowerCase().replace(/ /g, "-");

  // เช็ค override ก่อน
  const overrideSlug = F0NT_SLUG_OVERRIDES[lookupKey];
  if (overrideSlug) {
    return `https://www.f0nt.com/release/${overrideSlug}/`;
  }

  return `https://www.f0nt.com/release/${urlSlug}/`;
  
  return `https://fonts.google.com/specimen/${cleanName.replace(/ /g, "+")}`;
};


// 💡 เพิ่ม fontMapping เข้ามาเป็น Props ตรงนี้
const ListResultFont = ({ font, text, onDownload, fontMapping = {} }) => {
  const [isGoogleFont, setIsGoogleFont] = useState(true);
  const fontName = getFontFamily(font?.name);

  useEffect(() => {
    if (!font?.name) return;

    const currentFontName = getFontFamily(font.name);
    
    if (isCustomThaiFont(currentFontName)) {
      setIsGoogleFont(false);
      return; 
    }

    const fontId = `font-${currentFontName.replace(/ /g, "-")}`;
    if (document.getElementById(fontId)) return;

    const link = document.createElement("link");
    link.href = `https://fonts.googleapis.com/css2?family=${currentFontName.replace(/ /g, "+")}&display=swap`;
    link.rel = "stylesheet";
    link.id = fontId;

    document.head.appendChild(link);

    return () => {
      const targetLink = document.getElementById(fontId);
      if (targetLink) {
        document.head.removeChild(targetLink);
      }
    };
  }, [font?.name]);

  // 🛠️ ปรับแก้ Logic ตรงนี้เพื่อใช้จับคู่ชื่อฟอนต์ใหม่ครับ:
  // แปลงชื่อ font.name จาก API ให้เป็นรูปแบบตัวพิมพ์เล็กติดกันเหมือนกับใน fontMap
  const lookupKey = font?.name 
    ? font.name
        .replace(/(-Regular|Regular|\.ttf|\.otf)/gi, "")
        .replace(/[^a-zA-Z0-9]/g, "")
        .toLowerCase()
    : "";

  const customFontFamily = fontMapping[lookupKey]; 

  // เลือกฟอนต์ที่จะใช้แสดงผลจริง
  const finalFontFamily = isGoogleFont 
    ? `"${fontName}", sans-serif` 
    : (customFontFamily ? `"${customFontFamily}", sans-serif` : "sans-serif");

  const previewStyle = {
    fontFamily: finalFontFamily
  };

  return (
    <div className="result-card">
      <div className="font-preview-box" style={previewStyle}>
        {fontName?.[0] ?? "A"}{fontName?.[1]?.toLowerCase() ?? "a"}
      </div>

      <div className="font-info">
        <p className="test-text" style={previewStyle}>
          {text || "The Art of Typography ศิลปะแห่งการออกแบบตัวอักษร"}
        </p>

        <p className="font-name">{fontName}</p>

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