import React, { useState, useEffect } from 'react'
import { Header, Newfont, Popular, Search,Admin } from './components';
import { Routes, Route, Navigate } from 'react-router-dom';
import Detail from "./components/Detail/Detail";
import './App.css';
import { getApiUrl } from './config';

// สร้าง Layout ที่มี Header ครอบ
const WithHeader = ({ children }) => (
  <>
    <Header />
    {children}
  </>
);
const DetailWithReady = () => {
  const [backendReady, setBackendReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const waitForBackend = async () => {
      while (true) {
        if (cancelled) return;
        try {
          const res = await fetch(getApiUrl("/ready"));
          if (res.ok) { setBackendReady(true); return; }
        } catch {}
        await new Promise(r => setTimeout(r, 1000));
      }
    };
    waitForBackend();
    return () => { cancelled = true; };
  }, []);

  if (!backendReady) return (
    <div className="loader-wrapper">
      <div className="spinner" />
      <p className="loader-text">กำลังโหลด...</p>
    </div>
  );

  return <Detail />;
};

const App = () => {
  const [image, setImage] = useState(null);
  const [backendReady, setBackendReady] = useState(false);

  

  return (
    
    <Routes>
      <Route path="/" element={<Navigate to="/Detail" replace />} />

      {/*  หน้าที่ต้องการ Header ให้ครอบด้วย WithHeader */}
      <Route path="/Detail" element={<WithHeader><DetailWithReady  /></WithHeader>} />
      <Route path="/Newfont" element={<WithHeader><Newfont /></WithHeader>} />
      <Route path="/Popular" element={<WithHeader><Popular /></WithHeader>} />
      <Route path="/Search" element={<WithHeader><Search /></WithHeader>} />

      {/*  Admin ไม่ครอบ WithHeader → ไม่มี Header */}
      <Route path="/Admin" element={<Admin />} />
    </Routes>
  );
};

export default App