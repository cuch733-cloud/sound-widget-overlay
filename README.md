# Sound Widget Overlay

A floating glass "dynamic island" for Windows that controls media and volume.
كبسولة زجاجية عائمة للتحكم بالميديا والصوت على ويندوز.

---

## English

### Features
- Works with anything that reports to Windows media controls (Spotify, YouTube in Chrome/Edge, Movies & TV…) plus **MPC-HC** and **VLC (including VLC 3)** through their web interfaces.
- Two collapsed styles: **Small** (clock + live sound waves) or **Normal** (cover + title + progress). It expands when you hover over it.
- Live glass (real blur of what is behind it), 8 built-in themes and **5 saved custom themes**, per-region colors (top / bottom / left / right).
- Play / Pause, Previous / Next, **Shuffle**, **Repeat** (off / all / one), seek bar with elapsed and total time.
- Volume icon (3 levels) with a horizontal slider. The mouse wheel changes the volume.
- Hold **Next** for a silent fast-forward (x2, then x3 after 4 seconds). Sound returns when you release.
- Drag anywhere (it snaps to the screen edge), size from Settings, tray icon, start with Windows, English / Arabic.

### Run
```
pip install -r requirements.txt
python sound_widget_overlay.py
```
To build a single exe, run `build_exe.bat`. The result is `dist\Sound.Widget.Overlay.exe`.

### MPC-HC setup
1. Open MPC-HC and go to **View → Options → Player → Web Interface**.
2. Tick **Listen on port** and keep `13579`, then click **OK**.
3. Play a file. If nothing shows, open `http://127.0.0.1:13579` in a browser to check.

If Pause / Prev / Next do nothing, edit `MPC_CMD_PAUSE`, `MPC_CMD_PREV` and `MPC_CMD_NEXT` at the top of the script (try `889`, `918`, `919`).
Shuffle is not available with MPC-HC, and "Repeat all" only restarts the current file.

### VLC setup (VLC 3 and newer)
VLC does not report to Windows media controls, so the widget talks to VLC through its built-in web interface. Do this once:

1. Open VLC and press **Ctrl + P** (or **Tools → Preferences**).
2. At the bottom-left, under **Show settings**, choose **All**. The full settings tree appears.
3. In the tree, click **Interface**, then **Main interfaces**.
4. Tick **Web** only. The text box at the bottom should now say `http`.
   Do **not** tick **Lua interpreter**: it opens an ugly black console window.
5. Under **Main interfaces**, click **Lua**. In the **Lua HTTP** section, set **Password** to `vlc`.
   (If you choose another password, change `VLC_PASSWORD` at the top of the script to match.)
6. Click **Save**, then close VLC completely and open it again.
7. To check it, open `http://127.0.0.1:8080` in your browser. Leave the user name empty and type the password. If you see the VLC web page, it works. You do not play files from the browser: keep using the VLC player, and the widget connects by itself in the background.


### Notes
- Sound waves follow the loudness of the system output (a peak meter), not a frequency spectrum.
- The live glass hides the widget from screenshots and screen sharing. To take a screenshot of it, right-click it and tick **Screenshot mode**.
- Windows only (it uses Windows media controls and Core Audio).
- Some antivirus tools flag PyInstaller executables by mistake. Building from source avoids that.

### License
MIT

---

## العربية

### المزايا
- يعمل مع كل برنامج يعلن عن نفسه لأدوات الوسائط في ويندوز (Spotify ويوتيوب في Chrome وEdge وتطبيق الأفلام والبرامج التلفزيونية…)، ومع **MPC-HC** و**VLC (حتى الإصدار 3)** عبر واجهاتهما.
- شكلان للكبسولة المنكمشة: **صغيرة** (ساعة وموجات صوت حية) أو **عادية** (صورة واسم وشريط تقدم). تتمدد عند تمرير الفأرة عليها.
- زجاج حي (تمويه حقيقي لما خلفها)، و8 ثيمات جاهزة، و**5 ثيمات مخصصة** محفوظة، وألوان لكل منطقة (علوي / سفلي / أيمن / أيسر).
- تشغيل وإيقاف، السابق والتالي، **الخلط**، **التكرار** (إيقاف / الكل / ملف واحد)، وشريط تقدم مع الوقت المنقضي والمدة الكلية.
- أيقونة صوت بثلاث درجات مع شريط أفقي، وعجلة الماوس تغيّر الصوت.
- الضغط المطوّل على **التالي** يقدّم الوقت بصمت (×2 ثم ×3 بعد 4 ثوانٍ)، ويعود الصوت عند الإفلات.
- تُسحب لأي مكان وتلتصق بحافة الشاشة، والحجم من الإعدادات، وأيقونة في شريط المهام، وتشغيل مع ويندوز، وعربي / إنجليزي.

### التشغيل
```
pip install -r requirements.txt
python sound_widget_overlay.py
```
لبناء ملف exe واحد شغّل `build_exe.bat`، والناتج `dist\Sound.Widget.Overlay.exe`.

### تجهيز MPC-HC
1. افتح MPC-HC ثم **View → Options → Player → Web Interface**.
2. فعّل **Listen on port** وأبقِ المنفذ `13579` ثم اضغط **OK**.
3. شغّل ملفاً. وإن لم يظهر شيء فافتح `http://127.0.0.1:13579` في المتصفح للتأكد.

إن لم تعمل أزرار الإيقاف المؤقت أو السابق أو التالي، فعدّل `MPC_CMD_PAUSE` و`MPC_CMD_PREV` و`MPC_CMD_NEXT` في أعلى الملف (جرّب `889` و`918` و`919`).
الخلط غير متاح مع MPC-HC، و«تكرار الكل» يعيد الملف الحالي فقط.

### تجهيز VLC (الإصدار 3 وما بعده)
VLC لا يعلن عن نفسه لأدوات الوسائط في ويندوز، لذلك تتصل الكبسولة به عبر واجهته المدمجة. افعل هذا مرة واحدة:

1. افتح VLC واضغط **Ctrl + P** (أو من قائمة الأدوات اختر التفضيلات).
2. في **أسفل اليسار**، أسفل «إظهار الإعدادات»، اختر **الكل**. تظهر شجرة الإعدادات الكاملة.
3. في الشجرة التي على **اليسار** (وليس اليمين) اضغط **الواجهة**، ثم **الواجهات الرئيسية**.
4. فعّل خيار **Web** فقط. يجب أن يصير النص في الخانة السفلية `http`.
   لا تفعّل **مفسّر لوا**، لأنه يفتح نافذة سوداء مزعجة.
5. أسفل **الواجهات الرئيسية** اضغط على **Lua** (لوا). في قسم **Lua HTTP** اكتب في **كلمة السر** القيمة `vlc`.
   (إن اخترت كلمة غيرها فعدّل `VLC_PASSWORD` في أعلى الملف لتطابقها.)
6. اضغط **حفظ**، ثم أغلق VLC نهائياً وافتحه من جديد.
7. للتأكد افتح `http://127.0.0.1:8080` في المتصفح، واترك اسم المستخدم فارغاً واكتب كلمة السر. إن ظهرت صفحة VLC فقد اشتغل. لا تشغّل ملفاتك من المتصفح: استمر باستخدام مشغّل VLC كالمعتاد، والكبسولة تتصل به وحدها في الخلفية.


### ملاحظات
- موجات الصوت تتبع شدة صوت النظام (قياس الذروة) وليست تحليل ترددات.
- الزجاج الحي يخفي الكبسولة من لقطات الشاشة ومشاركة الشاشة. لالتقاط صورة لها اضغط عليها كليك يمين وفعّل **وضع لقطة الشاشة**.
- يعمل على ويندوز فقط (يعتمد على أدوات الوسائط وCore Audio في ويندوز).
- بعض برامج الحماية تنبّه خطأً من ملفات PyInstaller، والبناء من الكود المصدري يتجنب ذلك.

### الترخيص
MIT
