import React,{useEffect,useState} from 'react'
import "./Popular.css";
import { box } from '../../assets';
import { data, useLocation } from 'react-router-dom';
import ListResultFont from '../ListResultFont';
import { getApiUrl } from '../../config';


const Popular = () => {
    const location = useLocation();
    const [ocrText, setOcrText] = useState("");
    const navFonts = location.state?.fonts || [];
    const [fonts, setFonts] = useState(navFonts.length > 0 ? navFonts : undefined);
    const [loading, setLoading] = useState(navFonts.length === 0);

    const fetchFonts = (showLoading = true) => {
        if (showLoading) setLoading(true);
            fetch(getApiUrl("/popular_font"))
            .then(res => res.json())
            .then(result => {
                if (result.status === "success") {
                    setFonts(result.data);
                } else {
                    setFonts([]);
                }
            })
            .catch(err => {
                console.error(err);
                setFonts([]);
            })
            .finally(() => { if (showLoading) setLoading(false);});
    };

    useEffect(() => {
        if (navFonts.length > 0) {
            setFonts(navFonts);
            setLoading(false);
        }

        fetchFonts(true);
        const handleFocus = () => fetchFonts(false); 
        window.addEventListener("focus", handleFocus);
        return () => window.removeEventListener("focus", handleFocus);
    }, []);


  return (
      <div className="popular-container">
            <div className="popular-card">
            <div className="popular-header">
                <div className = "font-preview">
                    <span>Popular</span>
                </div>
            </div>
            <input
                className="popurlar-label-input"
                value={ocrText} 
                onChange={(e) => setOcrText(e.target.value.slice(0,100))}
                placeholder="Type something..."
            />
            <div className={`popular-content ${loading ? "loading" : ""}`} >
                {loading ? (  
                    <div >
                        loading.....
                        </div>
                ): !fonts || fonts.length === 0 ?(
                    <>  
                   
                    <div className="popular-text-group">
                        <img src={box} alt="box" className="box-icon" />
                        <div className="text-content">
                        <h1 className="not-found-title">No trending fonts found</h1>
                        <p className="not-found-desc">It looks like there’s no data available at the moment.</p>
                        <p className="not-found-desc">Check back soon to see the most popular fonts.</p>
                        </div>
                    </div>               
                    </>
                ):(
                    <div className="results-list">
                    {fonts.map((font, index) => (
                        <ListResultFont
                        key={index}
                        font={typeof font === "string" ? { name: font } : font}
                        text={ocrText || "The Art of Typography ศิลปะแห่งการออกแบบตัวอักษร"}
                        onDownload={() => fetchFonts(false)}
                        />
                    ))}
                    </div>  
                )}  
                </div>
            </div>  
        </div>
  )
}

export default Popular