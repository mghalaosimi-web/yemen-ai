# Yemen AI v5 — التثبيت والتشغيل
## للمستخدم
1. شغّل `Yemen_AI_Setup.exe` بعد بنائه.
2. اختر التثبيت.
3. استخدم اختصار سطح المكتب `Yemen AI`.
4. البرنامج يشغّل الخادم المحلي ويفتح الواجهة تلقائيًا.

## للمطور
```powershell
.\scripts\build_windows.ps1
```
يتطلب بناء EXE: Python + PyInstaller. ولإنشاء Setup.exe ثبّت NSIS.

## بوابات الدخول
- `/training`: admin, developer, trainer
- `/developer`: admin, developer
- `/user`: جميع المستخدمين المسجلين
- `/dashboard`: admin, developer

يتم منع الوصول المباشر للبوابات على مستوى الخادم وليس JavaScript فقط.
