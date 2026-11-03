import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import "./Header.css";
import { logo, search } from '../../assets';
import { getApiUrl } from '../../config';



const cleanFontName = (name) => {
  if (!name) return "";
  return name
    .replace(/\.(ttf|otf|woff2?)$/i, '')
    .replace(/[-_](Regular|Bold|Italic|Light|Medium|Thin).*/i, '')
    .replace(/[-_]/g, ' ')
    .trim();
};

const Header = ({ disabled }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") || "");

  const [allFonts, setAllFonts] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [isFetchingFonts, setIsFetchingFonts] = useState(false);
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);
  const isFetchingRef = useRef(false);

  const waitUntilReady = async (maxAttempts = 10, interval = 1000) => {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const res = await fetch(getApiUrl("/ready"));
        if (res.ok) return;
      } catch (_) {}
      await new Promise(res => setTimeout(res, interval));
    }
  };

  const fetchAllFonts = async () => {
    if (disabled) return;
    if (isFetchingRef.current) return; 
    isFetchingRef.current = true;
    setIsFetchingFonts(true);
    try {
      await waitUntilReady();
      const response = await fetch(getApiUrl("/search"));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      if (result.data) {
        const unique = [...new Set(result.data.map(f =>
          typeof f === "string" ? f : f.name || f.font_name
        ))];
        setAllFonts(unique);
      }
    } catch (error) {
      console.error("โหลดฟอนต์ไม่สำเร็จ", error);
    } finally {
      setIsFetchingFonts(false);
      isFetchingRef.current = false;
    }
  };

  useEffect(() => {
    if (disabled) return;
    fetchAllFonts();
  }, [disabled]);

  useEffect(() => {
    if (allFonts.length > 0 && document.activeElement === inputRef.current) {
      const filtered = query.trim()
        ? allFonts.filter(f =>
            cleanFontName(f).toLowerCase().startsWith(query.trim().toLowerCase())
          )
        : allFonts;
      setSuggestions(filtered);
      setShowDropdown(true);
    }
  }, [allFonts]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const q = searchParams.get("q");
    if (q) {
      setQuery(q);
    } else if (!location.pathname.startsWith('/search')) {
      setQuery("");
    }
  }, [searchParams, location.pathname]);

  const handleInputChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    if (value.trim()) {
      const filtered = allFonts.filter(f =>
        cleanFontName(f).toLowerCase().startsWith(value.trim().toLowerCase())
      );
      setSuggestions(filtered);
    } else {
      setSuggestions(allFonts);
    }
    setShowDropdown(true);
  };

  const handleFocus = () => {
    if (allFonts.length > 0) {
      const filtered = query.trim()
        ? allFonts.filter(f =>
            cleanFontName(f).toLowerCase().startsWith(query.trim().toLowerCase())
          )
        : allFonts;
      setSuggestions(filtered);
      setShowDropdown(true);
      return;
    }
    if (!isFetchingRef.current) {
      fetchAllFonts();
    }
  };

  const handleSelectFont = (fontName) => {
    const cleaned = cleanFontName(fontName);
    setQuery(cleaned);
    setShowDropdown(false);
    navigate(`/Search?q=${encodeURIComponent(cleaned)}`);
  };

  const handleSearch = (e) => {
    if (e) e.preventDefault();
    setShowDropdown(false);
    if (query.trim()) {
      navigate(`/Search?q=${encodeURIComponent(query.trim())}`);
    } else {
      navigate('/Search');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch(e);
    }
  };

  return (
    <header className="header">

      <div className="nav-logo" onClick={() => navigate('/', { replace: true })}>
        <img src={logo} alt="logo" className="logo" />
      </div>
      <div className="search-box" ref={dropdownRef}>
        <div className="combobox-row">
          <input
            ref={inputRef}
            type="text"
            placeholder="Search Font"
            className="search-input"
            value={query}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={handleFocus}
          />
          <button className="search-btn" onClick={handleSearch} aria-label="ค้นหา">
            <svg viewBox="0 0 24 24" width="10" height="10"
              stroke="currentColor" fill="none"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
          </button>
        </div>

        {showDropdown && (
          <ul className="font-dropdown">
            {isFetchingFonts ? (
              <li className="font-dropdown-item loading">กำลังโหลดฟอนต์...</li>
            ) : suggestions.length > 0 ? (
              suggestions.map((fontName, index) => {
                const cleaned = cleanFontName(fontName);
                const initial = cleaned.charAt(0).toUpperCase();
                return (
                  <li
                    key={index}
                    className="font-dropdown-item"
                    onMouseDown={() => handleSelectFont(fontName)}
                  >
                    <span className="font-icon">{initial}</span>
                    <span className="font-label">{cleaned}</span>
                  </li>
                );
              })
            ) : (
              <li className="font-dropdown-item loading">ไม่พบฟอนต์</li>
            )}
          </ul>
        )}
      </div>

      <div className="menu">
        <span className="home-btn" onClick={() => window.location.href = '/Detail'}>Home</span>
        <span className="popular-btn" onClick={() => navigate('/Popular')}>Popular</span>
        <span className="newfont-btn" onClick={() => navigate('/Newfont')}>Newfont</span>
      </div>

    </header>
  );
};

export default Header