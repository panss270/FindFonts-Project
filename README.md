# ชื่อโปรเจกต์ เว็บแอปพลิเคชันค้นหาฟอนต์จากภาพโดยใช้เทคโนโลยีปัญญาประดิษฐ์

เป็นระบบที่พัฒนาขึ้นโดยมีความสามารถในการค้นหาฟอนต์จากภาพ ระบบรองรับการค้นหาฟอนต์ทั้งภาษาไทยและภาษาอังกฤษจำนวน 33 ฟอนต์จากเว็บ **https://fonts.google.com/** โดยสามารถรับภาพที่ผู้ใช้งานอัปโหลดและวิเคราะห์ลักษณะของฟอนต์ในภาพผ่านโมเดลปัญญาประดิษฐ์ที่ได้รับการพัฒนาขึ้น จากนั้นแสดงรายการฟอนต์ที่มีความคล้ายคลึงกันพร้อมค่าเปอร์เซ็นต์ความคล้ายของแต่ละฟอนต์ เพื่อให้ผู้ใช้งานสามารถเปรียบเทียบได้อย่างชัดเจน


### Live Demo
ทดลองใช้งานระบบจริงได้ที่: **https://findfonts.vercel.app/Detail**
ไฟล์รูปภาพสำหรับทดสอบ **https://drive.google.com/drive/folders/1VyWYcQXBN86dvVMhgu7mxG5Zpzmr6s43?usp=sharing**



### Languages & Frameworks
 
- **Frontend:** [React, HTML/CSS, JavaScript]
- **Backend:** [FastAPI (Python), RESTful API Architecture, Node.js]
- **Database:** [PostgreSQL, Supabase]
- **Deep Learning:** [Convolutional Neural Network ]
- **Model:** [EfficientNet ]


### Tools & Deployment
 
 - **Hosting / Deployment:** Vercel, Hugging Face
 - **Version Control:** GitHub
 - **IDE:** VS Code


### ฟีเจอร์หลัก
 
- [ ] 1. อัปโหลดภาพฟอนต์ที่ต้องการค้นหาในหน้า Home ระบบจะแสดงรายการฟอนต์พร้อมเปอร์เซ็นต์ความคล้ายคลึงของฟอนต์ สามารถ crop เพื่อเลือกข้อความในรูปได้
- [ ] 2. สามารถพิมพ์ในกล่อง Type something ของทุกหน้าเพื่อดูการแสดงผลของฟอนต์
- [ ] 3. ดูรายการฟอนต์ยอดนิยมที่มียอดดาวน์โหลดสูงสุด 7 อันดับได้ที่หน้า Popular
- [ ] 4. ดูรายการฟอนต์ใหม่ล่าสุดของระบบได้ที่หน้า NewFont
- [ ] 5. ค้นหารายชื่อฟอนต์ของระบบได้ที่กล่องค้นหา
