# Qarz Daftar Pro — Enterprise Sovereign Ledger Frontend

Ushbu katalog **Qarz Daftar Pro** tizimining zamonaviy, to'liq funksional va Django REST API bilan integratsiya qilingan yagona Single Page Application (SPA) frontend qismidir.

Barcha dizayn maketlari ("Asosiy boshqaruv paneli", "Mijozlar balansi", "Qarzlar boshqaruvi", "To'lovlar va kvitansiya tizimi") **Sovereign Ledger** qoidalariga asosan real backend bilan 100% integratsiya qilingan.

---

## 🚀 Ishga tushirish (Quick Start)

### 1. Backend (Django REST Framework)
Backend serverini ishga tushirish:
```powershell
cd "c:\Users\Admin\OneDrive\Документы\qarz daftar\backend"
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

### 2. Frontend (SPA)
Frontend statik serverini ishga tushirish:
```powershell
cd "c:\Users\Admin\OneDrive\Документы\qarz daftar\stitch_qarz_daftar_pro_frontend"
..\.venv\Scripts\python.exe -m http.server 3000
```
Brauzerda oching: **[http://127.0.0.1:3000/index.html](http://127.0.0.1:3000/index.html)**

---

## 🔐 Akkaunt va Do'kon Yaratish (Production Setup)

Tizim real foydalanuvchilar va toza ma'lumotlar bazasi bilan ishlaydi (demo mock ma'lumotlari olib tashlangan).

### 1-usul: Veb-interfeys orqali (Tavsiya etiladi)
1. Brauzerda ilovani oching: `http://127.0.0.1:3000/index.html`.
2. Ekranda ochilgan modal oynada **"Ro'yxatdan o'tish"** bo'limini tanlang.
3. Ism-familiya, telefon, email va parolingizni kiriting.
4. Tizimga kirganingizdan so'ng **"+ Yangi Do'kon Ochish"** orqali o'z savdo do'koningizni (nomi, manzili, valyutasi) bir necha soniyada yarating va qarz/mijoz kiritishni boshlang!

### 2-usul: CLI Terminal orqali (Administrator)
Backend buyruqlar satri orqali administrator hisobi va do'konni bir zumda yaratish:
```powershell
cd "c:\Users\Admin\OneDrive\Документы\qarz daftar\backend"
..\.venv\Scripts\python.exe manage.py setup_admin --email admin@domain.uz --password MaxfiyParol123! --first-name "Sardor" --last-name "Rustamov" --phone "+998901234567" --shop-name "Asosiy Savdo Markazi" --superadmin
```

---

## 📂 Fayllar tuzilishi

- **`index.html`** — Yagona SPA interfeysi:
  - **Avtorizatsiya & Ro'yxatdan o'tish modallari** (JWT token saqlash va avtomatik boshqaruv).
  - **Do'kon boshqaruvi & Almashtirish** (Multi-tenant ko'p do'konli izolyatsiya).
  - **Boshqaruv paneli (Dashboard):** Real joriy balans, undirilgan to'lovlar, muddati o'tgan qarzlar KPI ko'rsatkichlari, trend grafigi va so'nggi operatsiyalar jadvali.
  - **Mijozlar (Customers):** Mijozlar ro'yxati, kredit limitlari, joriy balans va qidiruv.
  - **Qarzlar (Debts):** Qarz shartnomalari, muddati, to'langan/qoldiq summalar, filtrlar va bekor qilish.
  - **To'lovlar & Chek (Payments & POS Receipt):** Barcha to'lovlar tarixi, termal chek (80mm) jonli ko'rinishi va chop etish (`window.print()`).
  - **Telegram Bot Integratsiyasi:** 6 xonali dinamik ulanish kodi va hisobni bog'lash holati.
  - **Modallar:** Yangi mijoz qo'shish, Yangi qarz rasmiylashtirish, To'lov qabul qilish (Naqd / Karta / Aralash), Do'kon qo'shish.
- **`styles.css`** — Sovereign Ledger dizayn tizimi (Navy `#0B132B` sidebar, tabulyar raqamlar, yumshoq soyalar, termal qog'oz uslubi va bosib chiqarish qoidalari).
- **`app.js`** — Frontend asosiy boshqaruvchi skripti:
  - Token boshqaruvi va avtomatik refresh.
  - Ko'p do'konli izolyatsiya (`X-Shop-ID` sarlavhasi).
  - Jonli CRUD operatsiyalari va Excel/CSV hisobot yuklab olish.
  - Toast xabarnomalar tizimi.
