// fonts.js
export const loadCustomFonts = async () => {
  try {
    const res = await fetch("http://localhost:8000/fonts");
    const fonts = await res.json(); 

    const fontMap = {}; 

    await Promise.all(
      fonts.map(async (name) => {
        // 💡 1. ปรับการตัดคำให้คลีนที่สุด ลบทั้ง -Regular, Regular, .ttf ออกให้เกลี้ยง
        const familyName = name
          .replace(/(-Regular|Regular|\.ttf|\.otf)/gi, "")
          .replace(/[_-]/g, "") // ลบขีดกลางและอันเดอร์สกอร์ออกด้วย เช่น nura_chaba -> nurachaba
          .trim();
        
        // 2. ใช้ชื่อดิบจาก DB (ตัดแค่สกุลไฟล์ออก) เพื่อให้ Vite ไปหาไฟล์เจอใน assets/fonts/
        const cleanFileName = name.replace(/(\.ttf|\.otf)/gi, "");
        const url = new URL(`./assets/fonts/${cleanFileName}.ttf`, import.meta.url).href;
        
        // 3. โหลดฟอนต์เข้า Browser
        const font = new FontFace(familyName, `url(${url})`);
        const loaded = await font.load();
        document.fonts.add(loaded);

        // 💡 4. ทำคีย์พิมพ์เล็กแบบไม่มีช่องว่างและสัญลักษณ์พิเศษ เพื่อจับคู่กับหน้าบ้าน
        const lookupKey = name
          .replace(/(-Regular|Regular|\.ttf|\.otf)/gi, "")
          .replace(/[^a-zA-Z0-9]/g, "") // ลบสัญลักษณ์ทุกอย่าง (ขีด, สเปซ, อันเดอร์สกอร์)
          .toLowerCase();

        fontMap[lookupKey] = familyName;
      })
    );

    console.log("ระบบจับคู่ฟอนต์ (fontMap):", fontMap);
    return fontMap; 
  } catch (err) {
    console.error("โหลดฟอนต์ไม่ได้:", err);
    return {};
  }
};