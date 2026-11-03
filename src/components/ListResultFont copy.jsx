import { useEffect } from "react";
import "./ListResultFont.css";
import { getApiUrl } from "../config";

const getFontFamily = (name) => {
  if (!name) return "sans-serif";

  const clean = name
    .replace(/-Regular|\.ttf/gi, "")
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .trim();
  return clean || "sans-serif";
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

    const fontName = getFontFamily(font.name);
    const fontId = `font-${fontName.replace(/ /g, "-")}`;

    if (document.getElementById(fontId)) return;

    const link = document.createElement("link");
    link.href = `https://fonts.googleapis.com/css2?family=${fontName.replace(/ /g, "+")}&display=swap`;
    link.rel = "stylesheet";
    link.id = fontId;

    document.head.appendChild(link);

    return () => {
      document.head.removeChild(link);
    };
  }, [font?.name]);

  return (
    
    <div className="result-card">

      <div
        className="font-preview-box"
        style={{ fontFamily: `${getFontFamily(font?.name)}, sans-serif` }}
      >
       {getFontFamily(font?.name)?.[0] ?? "A"}{getFontFamily(font?.name)?.[0]?.toLowerCase() ?? "a"}
      </div>

      <div className="font-info">

        <p
          className="test-text"
          style={{ fontFamily: `${getFontFamily(font?.name)}, sans-serif` }}
        >
          {text || "The Art of Typography ศิลปะแห่งการออกแบบตัวอักษร"}
        </p>

        <p className="font-name">
          {getFontFamily(font?.name)}
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