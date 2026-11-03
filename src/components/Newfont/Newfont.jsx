import React ,{useEffect,useState} from 'react'
import "./Newfont.css";
import { comming } from '../../assets';
import { useLocation } from 'react-router-dom';
import ListResultFont from '../ListResultFont';
import { getApiUrl } from '../../config';

const Newfont = () => {
    const location = useLocation();
    const navFonts = location.state?.fonts || [];

    const [ocrText, setOcrText] = useState("");
    const [fonts, setFonts] = useState(navFonts.length > 0 ? navFonts : undefined);
    const [loading, setLoading] = useState(navFonts.length === 0);


    const fetchFonts = (showLoading = true) => {
            if (showLoading) setLoading(true);
                fetch(getApiUrl("/new_font"))
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
    <div className="newfont-container">
            <div className="newfont-card">
            <div className="newfont-header">
                <div className = "font-preview">
                    <span>New Fonts</span>

                </div>
            </div>
            <input
                type="text"
                className="newfont-label-input"
                value={ocrText} 
                onChange={(e) => setOcrText(e.target.value.slice(0,100))}
                placeholder="Type something..."
            />
            <div className={`newfont-content ${loading ? "loading" : ""}`}>
                    {loading ? (
                        <div>loading.....</div>
                    ) : !fonts || fonts.length === 0 ? (
                        <>
                            
                            <div className="newfont-text-group">
                                <img src={comming} alt="comming" className="comming-icon" />
                                <div className="newfont-text-content">
                                    <h1 className="not-found-title">Fresh fonts are on the way!</h1>
                                    <p className="not-found-desc">We're currently hand-picking the latest font designs for you.</p>
                                    <p className="not-found-desc">Hang tight and check back soon!</p>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="results-list">
                            {fonts.map((font, index) => (
                                <ListResultFont
                                    key={index}
                                    font={typeof font === "string" ? { name: font } : font}
                                    text={ocrText || "The Art of Typography ศิลปะแห่งการออกแบบตัวอักษร"}
                                />
                            ))}
                        </div>
                    )}
            </div>   
            
        </div>
       </div>
  )
}

export default Newfont