# Shocar

เว็บเซิร์ฟเวอร์ควบคุมรถผ่าน Wi-Fi พร้อม dashboard และรีโมท

## รัน

```bash
venv/bin/python main.py
```

เปิด http://localhost:8000/dashboard

## ตั้งค่า

- `.env` — `ROBOT_URL`, `CAMERA_URL` (ดูตัวอย่างใน `.env.example`)
- `robot/robot_config.h` — ชื่อ Wi-Fi/รหัสผ่าน (copy จาก `robot_config.example.h`)
