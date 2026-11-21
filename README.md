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
## MPC-HC setup

Sound Widget Overlay talks to MPC-HC through its built-in Web Interface. This is a one-time setup.

1. Open MPC-HC and go to **View → Options** (or press `O`).
2. Select **Player → Web Interface** in the left tree.
3. Tick **Listen on port** and keep the default port `13579`.
4. Click **OK**. If Windows Firewall asks, allow access for private networks only.
5. Play any file. The widget will detect it within a second or two.

To check that it works, open `http://127.0.0.1:13579` in your browser. You should see the MPC-HC web page.

**Troubleshooting**
- The widget shows nothing: make sure the port is `13579` and MPC-HC is running.
- Play/Pause, Previous or Next does nothing: your MPC-HC version may use different command numbers. Edit `MPC_CMD_PAUSE`, `MPC_CMD_PREV` and `MPC_CMD_NEXT` at the top of `sound_widget_overlay.py` (try `889`, `918`, `919`).
- No cover image: for audio files the widget reads the embedded cover (MP3, M4A, FLAC) or an image next to the file named `cover.jpg` or `folder.jpg`. For videos it takes a frame snapshot after a few seconds.
- Shuffle is dimmed and "Repeat all" only restarts the current file in MPC-HC. This is an MPC-HC limitation of the web interface.

## Notes
- Sound waves follow the system output loudness (peak meter), not a frequency spectrum.
- Windows only (uses WinRT media controls + Core Audio).
- Antivirus tools sometimes flag PyInstaller executables; building from source avoids that.

## License
MIT
