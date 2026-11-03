import { useState,useRef, useEffect} from 'react'
import { getApiUrl } from '../config';
import './Admin.css'
import { useSearchParams } from 'react-router-dom';

const FileFilterImporter = () => {

  //--------UseState-----------
  const [successList, setSuccessList] = useState([]);
  const [loading, setLoading] = useState(false); 
  const [importMode, setImportMode] = useState('file');
  const [isFontLoading, setIsFontLoading] = useState(false);
  const [existingFonts, setExistingFonts] = useState([]);
  const [progress, setProgress] = useState({ current: 0, total: 0 }); 
  const [showAllFonts, setShowAllFonts] = useState(false);
  
  
 //UseRef 
  const successListRef = useRef([]);
  const duplicateListRef = useRef([]);
  const [renderTrigger, setRenderTrigger] = useState(0);

  const normalizeName = (name) => name.replace(/\.ttf$/i, '').toLowerCase();
  const [isSyncing, setIsSyncing] = useState(true);
  
  const fetchLatestFonts = async () => {
  try {
    const response = await fetch(getApiUrl("/fonts"));
    const data = await response.json();

    return data.fonts.map(name =>
      normalizeName(name)
    );
  } catch (err) {
    console.error("Fetch latest fonts error:", err);
    return [];
  }
};


  const handleOpenFonts = async () => {
  setShowAllFonts(true);
    try {
      const response = await fetch(getApiUrl("/fonts"));
      const data = await response.json();

      const fontItems = data.fonts.map(fontName => ({
        name: fontName,
        time: '-'
      }));
      setExistingFonts(fontItems);
      localStorage.setItem("fonts", JSON.stringify(fontItems));
    } catch (err) {
      console.error(err);
    }
};

  const refreshFonts = async () => {
    localStorage.removeItem("fonts");
    duplicateListRef.current = [];
    setDuplicates([]);
    setExistingFonts([]);
    const response = await fetch(getApiUrl("/fonts"));
    const data = await response.json();
    const fontItems = data.fonts.map(fontName => ({
      name: fontName,
      time: '-'
    }));
    setExistingFonts(fontItems);
    localStorage.setItem(
      "fonts",
      JSON.stringify(fontItems)
    );
  };

  const hasFetched = useRef(false); 
    useEffect(() => {
    setSuccessList([]);
    successListRef.current = [];
  }, []);

  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (loading) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [loading]);

  //เก็บรายชื่อฟอนต์ที่ซ้ำ
  useEffect(() => {
    const cached = localStorage.getItem("fonts");
    if (cached) {
      try {
        setExistingFonts(JSON.parse(cached));
        setIsFontLoading(true);
      } catch {
        localStorage.removeItem("fonts") 
  }
    }
    setIsSyncing(true);
    const fetchExistingFonts = async () => { 
      setIsFontLoading(true);
      try {
        const response = await fetch(getApiUrl("/fonts"));
        const data = await response.json();
        const fontItems = data.fonts.map(fontName => ({
          name: fontName,
          time: '-'
        }));
        const seen = new Set();
        const uniqueFontItems = fontItems.filter(item => {
          const key = normalizeName(item.name);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
        setExistingFonts(uniqueFontItems);
        setIsSyncing(false);
        localStorage.setItem("fonts", JSON.stringify(uniqueFontItems));
      } catch (err) {
        console.error("Failed to fetch fonts:", err);
        localStorage.removeItem("fonts");
      } finally {
        setIsFontLoading(false); 
        setIsSyncing(false);
      }
    };
      localStorage.removeItem("fonts");
      setExistingFonts([]);
      successListRef.current = [];
      duplicateListRef.current = [];
      setSuccessList([]);
      setDuplicates([]);
      fetchExistingFonts(); 
  }, []);

    const handleInputClick = (e) => {
      e.target.value = null; 
    };

    const addToSuccessList = (newItems) => {
        setSuccessList(prev => {
          const existing = new Set(
            prev.map(item => normalizeName(item.name))
          );
          const filtered = newItems.filter(item =>
            !existing.has(normalizeName(item.name))
          );
          const updated = [...prev, ...filtered];
          successListRef.current = updated;
          return updated;
        });
      };

    const setDuplicates = (list) => {
      duplicateListRef.current = list;           
      setRenderTrigger(prev => prev + 1);     
    };


//----- drage and drop-----
  const readAllFilesFromEntry = (entry, mode = 'folder') => {
      return new Promise((resolve) => {
        if (entry.isFile) {
          entry.file(file => {
            const name = file.name.toLowerCase();       
            if (mode === 'file' && !name.endsWith('.ttf')) {
              resolve([]);
              return;
            }
            resolve([file]);

          });
        } else if (entry.isDirectory) {
          if (mode === 'file') {
            resolve([]); 
            return;
          }
          const reader = entry.createReader();
          const allFiles = [];
          const readEntries = () => {
            reader.readEntries(async (entries) => {
              if (entries.length === 0) {
                resolve(allFiles);
              } else {
                for (const e of entries) {
                  const files = await readAllFilesFromEntry(e, importMode);
                  allFiles.push(...files);
                }
                readEntries(); 
              }
            });
          };
          readEntries();
        } else {
          resolve([]);
        }
      });
    };

  //-------file----------------
  // ฟังก์ชัน 1: รับไฟล์เฉพาะ .ttf (ใช้ accept ช่วยกรองที่หน้าต่างเลือกไฟล์)
  const handleFileChange = async (event) => {
  const file = event.target.files[0]; 
  if (!file.name.toLowerCase().endsWith('.ttf')) {
    alert("รองรับเฉพาะไฟล์ .ttf เท่านั้น");
    return;
  }
  const normalizedName = normalizeName(file.name);
  setLoading(true);
  const latestFonts = await fetchLatestFonts();
  const existingNames = new Set(latestFonts);

  if (existingNames.has(normalizedName)) {
      const latestFonts = await fetchLatestFonts();

      if (latestFonts.includes(normalizedName)) {
        setDuplicates([file.name]);
        setLoading(false);
        return;
      }
  }

  setDuplicates([]);
  setSuccessList([]);
  successListRef.current = [];
  const formData = new FormData();
  formData.append("file", file);
  formData.append("font_name", file.name);

  try {
    const response = await fetch(getApiUrl("/upload-font"), {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    if (response.ok) {
      addToSuccessList([
    {
      name: result.font_name,
      time: new Date().toLocaleTimeString()
    }
  ]);

    const latestFonts = await fetchLatestFonts();

    setExistingFonts(
      latestFonts.map(name => ({
        name,
        time: '-'
      }))
    );
    setSuccessList(prev =>
      prev.filter(item =>
        latestFonts.includes(
          normalizeName(item.name)
        )
      )
    );
    } else {
      alert("Error:\n" + JSON.stringify(result.detail, null, 2));
    }
  } catch (error) {
    console.error("Connection Error:", error);
    alert("ไม่สามารถติดต่อ Server ได้");
  }
  setLoading(false);
};


  //-------folder----------------
  // ฟังก์ชัน 2: อ่านโฟลเดอร์แล้วเลือกเฉพาะ .ttf
  const handleFolderChange = async (event) => {
    const rawFiles = Array.from(event.target.files);
    const seenUpload = new Set();
    
    const files = rawFiles.filter(file => {
      const key = normalizeName(file.name);
      if (seenUpload.has(key)) return false;
      seenUpload.add(key);
      return true;
    });
    if (!files.length) return;

    const invalidFiles = files.filter(file => !file.name.toLowerCase().endsWith('.ttf'));
    if (invalidFiles.length > 0) {
      alert("รองรับเฉพาะไฟล์ .ttf เท่านั้น");
      return;
    }

    setLoading(true); 
    setSuccessList([]);
    successListRef.current = [];
    const ttfFiles  = files.filter(file => file.name.toLowerCase().endsWith('.ttf'));
    console.log("ttfFiles:", ttfFiles);
    if (ttfFiles.length === 0) {
      alert("ไม่พบไฟล์ .ttf");
      setLoading(false);
      return; 
    }

    const latestFonts = await fetchLatestFonts();
    const existingNames = new Set(latestFonts);
    const newFiles = ttfFiles.filter(file => !existingNames.has(normalizeName(file.name)));
    const duplicated = ttfFiles.filter(file =>
    latestFonts.includes(normalizeName(file.name))
   );
    setDuplicates(duplicated.map(f => f.name));
    if (newFiles.length === 0) {
      setLoading(false);
      return;
    }

    setProgress({ current: 0, total: newFiles.length });
    const formData = new FormData();
    for (const file of newFiles) {
      formData.append("files", file);
      formData.append("font_names", file.name);
    }

    try {
      const response = await fetch(getApiUrl("/upload-fonts"), {
        method: "POST",
        body: formData,
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.trim().split("\n");

        for (const line of lines) {
          if (!line) continue;
          const result = JSON.parse(line);
          addToSuccessList([{ name: result.font_name, time: new Date().toLocaleTimeString() }]);
          setProgress(prev => ({ ...prev, current: prev.current + 1 })); // ✅ นับทีละ 1
        }
      }
      const latestFonts = await fetchLatestFonts();

      setExistingFonts(
        latestFonts.map(name => ({
          name,
          time: '-'
        }))
      );
      setSuccessList(prev =>
        prev.filter(item =>
          latestFonts.includes(
            normalizeName(item.name)
          )
        )
      );
    } catch (error) {
      console.error("Connection Error:", error);
      alert("ไม่สามารถติดต่อ Server ได้");
    }
    setLoading(false);
    setProgress({ current: 0, total: 0 });
      };

 return (
    <div className ="admin-page">
    <div className="importer-wrapper">
    <h2 className="importfont">File Import</h2>
    {isFontLoading && (
      <small style={{ color: 'gray' }}>
        ⏳ กำลังโหลดข้อมูลฟอนต์...
      </small>
    )}
    <div className="import-mode-selector">
      <label>
        <input 
          type="radio" 
          value="file" 
          checked={importMode === 'file'} 
          onChange={(e) => setImportMode(e.target.value)}
          disabled={loading}
          style={{ marginRight: '6px' }}
        /> 
        Import Files
      </label>
      <label>
        <input 
          type="radio" 
          value="folder" 
          checked={importMode === 'folder'} 
          onChange={(e) => setImportMode(e.target.value)}
          disabled={loading}
          style={{ marginRight: '6px' }}
        /> 
        Import Folder
      </label>
    </div>

    {loading && (
        <div className="loading-overlay">
          ⏳ กำลังประมวลผล...
          {progress.total > 0 && (
            <span className="loading-progress">
              {progress.current}/{progress.total}
            </span>
          )}
        </div>
      )}

    <div
      className={`import-input-box${loading ? ' loading' : ''}`}
      onDragOver={(e) => {
        if (loading) return; 
        e.preventDefault()}}

      onDrop={async (e) => {
        e.preventDefault();
        if (loading) return;

        

        const items = Array.from(e.dataTransfer.items);
        const entries = items
          .map(item => item.webkitGetAsEntry?.())
          .filter(Boolean);

        if (entries.length === 0) return;
        const hasFolder = entries.some(entry => entry.isDirectory);
        const hasFile = entries.some(entry => entry.isFile);
        if (importMode === 'file' && hasFolder) {
          alert('กรุณาเลือก "Import Folder" ก่อนลากโฟลเดอร์มาวาง');
          return;
        }
        if (importMode === 'folder' && hasFile && !hasFolder) {
          alert('กรุณาเลือก "Import Files" ก่อนลากไฟล์มาวาง');
          return;
        }
        const allFilesNested = await Promise.all(
          entries.map(entry => readAllFilesFromEntry(entry))
        );
        const allFiles = allFilesNested.flat();

        if (allFiles.length === 0) return;

        if (importMode === 'file' && allFiles.length > 1) {
          alert('รับได้ทีละ 1 ไฟล์เท่านั้น กรุณาลากทีละไฟล์');
          return;
        }

        const syntheticEvent = {
          target: { files: allFiles }
        };

        if (importMode === 'file') {
          handleFileChange(syntheticEvent);
        } else {
          handleFolderChange(syntheticEvent);
        }
      }}
      onClick={() => {
        if (loading) return;   
        document.getElementById('hidden-input').click();
      }}
    >
      <span className="drop-icon">📁</span>
      <p className="drop-text">
        {importMode === 'file'
          ? 'คลิกหรือลากไฟล์ .ttf มาวางที่นี่'
          : 'คลิกหรือลาก Folder มาวางที่นี่'}
      </p>

      <input
        id="hidden-input"
        type="file"
        accept=".ttf"
        {...(importMode === 'folder' 
          ? { webkitdirectory: 'true', multiple: true }  // folder: รับหลายไฟล์
          : {}                                             // file: รับทีละ 1
        )}
        disabled={loading}
        onClick={handleInputClick}
        onChange={importMode === 'file' ? handleFileChange : handleFolderChange}
        style={{ display: 'none' }}
      />
    </div>

    {/* Duplicate warning */}
    {duplicateListRef.current.length > 0 && (
      <div className="duplicate-warning">
        <strong>⚠️ ไฟล์ต่อไปนี้เคย import แล้ว ({duplicateListRef.current.length} ไฟล์)</strong>
        <ul>
          {duplicateListRef.current.map((name, index) => (
            <li key={index}>{name}</li>
          ))}
        </ul>
        <button onClick={() => setDuplicates([])}>ปิด</button>
      </div>
    )}

    {/* ประวัติการบันทึก */}
    <div>
      <div className="history-card">
      <h3>ประวัติการบันทึกสำเร็จจำนวน ({successList.length}) ฟอนต์
        <button 
          className="btn-view-all"
          onClick={handleOpenFonts}
        >
          🗂️ ดูฟอนต์ทั้งหมดในระบบ
        </button>
      </h3>
      </div>
      {showAllFonts && (  
          <div className="admin-modal-overlay" onClick={() => setShowAllFonts(false)}>
            <div className="addmin-modal-box" onClick={(e) => e.stopPropagation()}>
              <h3>ฟอนต์ทั้งหมดในระบบจำนวน ({existingFonts.length}) ฟอนต์</h3> 
              {existingFonts.length === 0 ? (
                <p>...</p>
              ) : (
                <>
              <ul className="modal-font-list">
                {existingFonts.map((font, index) => (
                  <li key={index}>{index + 1}. {font.name}</li>
                ))}
              </ul>
              <button className="btn-close-modal" onClick={() => setShowAllFonts(false)}>
                ปิด
              </button>
              </>
              )}
            </div>
          </div>      
       )}
      {successList.length > 0 && (
        <div className="success-table-card">
        <table className="success-table" border="1" cellPadding="10">
          <thead>
            <tr>
              <th>ชื่อฟอนต์</th>
              <th>เวลาที่สำเร็จ</th>
            </tr>
          </thead>
          <tbody>
            {successList.map((item, index) => (
              <tr key={index}>
                <td><strong>{item.name}</strong></td>
                <td>{item.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
       </div>
      )}
    </div>
  </div>
  </div>
  );
  
};
const AdminPage = () => {
  const [searchParams] = useSearchParams();
  const [authed, setAuthed] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const key = searchParams.get('Key');
    if (!key) return;
    // console.log("key = " , key)
    // console.log("authed = " ,authed)

    const verify = async () => {
      const formData = new FormData();
      formData.append("key", key);

      try {
        const res = await fetch(getApiUrl("/admin"), {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          setAuthed(true);
        } else {
          alert("Access denied");
        }
      } catch {
        alert("ไม่สามารถติดต่อ Server ได้");
      }
    };

    verify();
  }, []);

  if (!authed) {
    return <p>{error ||" กรุณาใส่ key ใน URL ให้ถูกต้อง"}</p>;
  }

  return <FileFilterImporter />;
};

export default AdminPage;