# Sound Widget Overlay

A floating glass "dynamic island" for Windows that controls media and volume.
كبسولة زجاجية عائمة للتحكم بالميديا والصوت على ويندوز.

## Features / المزايا
- Works with anything that reports to Windows media controls (Spotify, browsers, Movies & TV…) + **MPC-HC** via its Web Interface.
- Two collapsed styles: **Small** (clock + live sound waves) or **Normal** (cover + title + progress). Expands on hover.
- Real acrylic/blur glass, 8 built-in themes + **5 saved custom themes**, per-region colors (top/bottom/left/right).
- Play/Pause, Prev/Next, **Shuffle**, **Repeat (off / all / one)**, seek bar with elapsed/total time.
- Volume icon (3 levels) with horizontal slider; mouse wheel changes volume.
- Hold **Next** = silent fast-forward (x2, x3 after 4 s), audio resumes on release.
- Drag anywhere, resize from the corners, tray icon, start with Windows, English / العربية.

## Run
```
pip install -r requirements.txt
python sound_widget_overlay.py
```
Build a single exe: run `build_exe.bat` → `dist\Sound.Widget.Overlay.exe`.

## MPC-HC setup
Options → Player → Web Interface → tick **Listen on port** (13579).
If Prev/Next/Pause do not work in your version, adjust the `MPC_CMD_*` constants at the top of the script.

## Notes
- Sound waves follow the system output loudness (peak meter), not a frequency spectrum.
- Windows only (uses WinRT media controls + Core Audio).
- Antivirus tools sometimes flag PyInstaller executables; building from source avoids that.

## License
MIT
