import React,{useState,useEffect} from 'react'
import './Search.css';
import{ useSearchParams} from "react-router-dom";
import { robot } from '../../assets';
import ListResultFont from '../ListResultFont';
import { getApiUrl } from '../../config';

const Search = () => {
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q") || ""; 
  const [previewText, setPreviewText] = useState("");
  const [loading, setLoading] = useState(false);
  const [fonts, setFonts] = useState([]);
  

  const fetchFonts = async (query) => {
    try {
        setLoading(true);
        setFonts([]); 
        const url = getApiUrl(
          `/search?q=${encodeURIComponent(query)}`
        );

        const res = await fetch(url);
        const result = await res.json();

        setFonts(result.data ?? []);
    } catch (err) {
        console.error("fetch error:", err);
    
    }finally{
      setLoading(false);
    }
  };

  const filteredFonts = fonts.filter(font => {
  const name = typeof font === "string" ? font : font.name || "";
  const cleanName = name
    .replace(".ttf", "")
    .replace("-Regular", "")
    .replace(/_/g, " ")
    .toLowerCase();
   return q ? cleanName.startsWith(q.toLowerCase()) : true;
  });  

  useEffect(() => {
    setPreviewText(""); 
    fetchFonts(q); 
   }, [q]);
  
  return (
    <div className="search-container">
            <div className="search-card">
            {/* header ส่วนบน */}
            <div className="search-header">
                <div className = "font-preview">           
                     Searching for: {q || "All Fonts"}
                </div>
            </div>
            {/* 2. ส่วนที่พิมพ์แก้ได้ (ใหญ่ๆ) */}
            <input
                type="text"
                className="result-label-input"
                value={previewText}
                placeholder="Type something..."
                onChange={(e) => setPreviewText(e.target.value.slice(0,100))}
                spellCheck="false"
                list="font-suggestions"
            />
            {/* 3. ส่วนแสดงผลลัพธ์ข้างล่าง (ถ้ามี) */}
            <div className={`result-content ${loading ? "loading":filteredFonts.length === 0 ? "empty" : "has-data" }`}>
                {loading ? (
                  <div className = "loading-container">
                    <p>Loading....</p>
                  </div>
                 ) : filteredFonts.length > 0 ? (
                <div className="results-list">
                  {filteredFonts.map((font, index) => (
                    <ListResultFont
                      key={index}
                      font={typeof font === "string" ? { name: font } : font}
                      text={previewText   || "The Art of Typography ศิลปะแห่งการออกแบบตัวอักษร"}
                    />
                  ))}
                </div>
              ) : (
                <>
                  
                  <div className="result-text-group">
                    <img src={robot} alt="robot" className="robot-icon" />
                      <div className="result-text-content">
                        <h1 className="not-found-title">we don’t recognize that font.</h1>
                        <p className="not-found-desc">
                          Try a different search or check the spelling of your query
                        </p>
                      </div>
                  </div>
                </>
              )} 
            </div>
        </div>
       </div>
  )
}

export default Search