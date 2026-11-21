# -*- coding: utf-8 -*-
"""
Sound Widget Overlay
====================
Floating glass "dynamic island" bubble for Windows media / volume control.
كبسولة زجاجية عائمة للتحكم بالميديا والصوت على ويندوز.

Requirements : pip install PyQt6 winsdk      (nothing else)
Run          : python sound_widget_overlay.py
Build exe    : build_exe.bat

License: MIT
"""

import sys
import os
import re
import io
import json
import math
import time
import html
import ctypes
import asyncio
import locale
import random
import threading
import traceback
import urllib.request
from ctypes import wintypes
from datetime import datetime

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, pyqtProperty, QTimer, QPropertyAnimation,
    QParallelAnimationGroup, QEasingCurve, QRect, QRectF, QPointF, QPoint,
    QSettings,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPainterPath, QLinearGradient, QRadialGradient, QPen,
    QBrush, QFont, QFontMetricsF, QPixmap, QImage, QPolygonF, QCursor,
    QGuiApplication, QAction, QIcon,
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMenu, QDialog, QFormLayout, QSlider, QComboBox,
    QPushButton, QCheckBox, QColorDialog, QSystemTrayIcon, QLabel,
    QHBoxLayout, QVBoxLayout, QTabWidget,
)

if sys.platform != "win32":
    sys.exit("Windows only / يعمل على Windows فقط.")

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
    from winsdk.windows.storage.streams import Buffer, InputStreamOptions, DataReader
except ImportError:  # pragma: no cover
    sys.exit("winsdk is not installed.  Run:  pip install winsdk")

try:
    from winsdk.windows.media import MediaPlaybackAutoRepeatMode as _RepeatMode
except Exception:  # pragma: no cover
    _RepeatMode = None


# ═════════════════════════════ ثوابت ═════════════════════════════
APP_NAME = "Sound Widget Overlay"
ORG_NAME = "SoundWidgetOverlay"
SIZES = {"mini": (176, 36), "normal": (270, 56)}     # الحجم المنكمش لكل نمط
EXPAND_W, EXPAND_H = 380, 140                         # الحجم الموسّع
SLOT_COUNT = 5
SESSION_GRACE_SEC = 10.0
POSITION_TICK_MS = 200
MARQUEE_GAP = 46
MARQUEE_SPEED = 38.0
DEFAULT_ACCENT = QColor(124, 172, 255)
HOLD_MS = 420                  # مدة الضغط المطوّل على "التالي"
FF_BOOST_AFTER = 4.0           # بعد 4 ثوانٍ يتحول x2 إلى x3

# ── MPC-HC (Options > Player > Web Interface > Listen on port 13579) ──
MPC_BASE = "http://127.0.0.1:13579"
MPC_CMD_PLAY = 887
MPC_CMD_PAUSE = 888            # إن لم يعمل جرّب 889
MPC_CMD_PREV = 920             # إن لم يعمل جرّب 918
MPC_CMD_NEXT = 921             # إن لم يعمل جرّب 919
MPC_CMD_SHUFFLE = 0            # 0 = غير مدعوم (الزر يبقى باهتاً مع MPC-HC)
MPC_CMD_FIRST_ITEM = 0         # 0 = غير مدعوم (يُعاد تشغيل الملف الحالي عند "تكرار الكل")

AUDIO_EXT = {".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus", ".wma", ".m4b", ".ape", ".mka"}


# ═════════════════════════════ اللغات ═════════════════════════════
STR = {
    "en": {
        "idle_title": "Nothing playing", "idle_sub": "Play something and it will show up here",
        "untitled": "(Untitled)", "toast_mute": "Mute toggled",
        "menu_settings": "Settings & themes…", "menu_themes": "Themes",
        "menu_pin": "Keep expanded", "menu_reset": "Reset position",
        "menu_hide": "Hide (stays in tray)", "menu_close": "Quit",
        "tray_toggle": "Show / Hide", "custom": "Custom {n}",
        "set_title": "Sound Widget Overlay — Settings",
        "tab_general": "General", "tab_look": "Appearance", "tab_regions": "Colors by region",
        "language": "Language", "layout": "Collapsed style",
        "layout_mini": "Small (clock + sound waves)", "layout_normal": "Normal (cover + title + progress)",
        "size": "Size %", "clock24": "24-hour clock", "autostart": "Start with Windows",
        "theme": "Theme", "blur": "Glass (blur)", "blur_off": "Off", "blur_blur": "Blur",
        "blur_acrylic": "Acrylic (frosted)", "opacity": "Opacity", "brightness": "Brightness",
        "radius": "Corner radius", "softness": "Region edge softness", "tint": "Glass color",
        "text_color": "Text color", "accent": "Accent color",
        "accent_auto": "Auto accent from cover", "reset_slot": "Reset this theme",
        "region_top": "Top half", "region_bottom": "Bottom half",
        "region_left": "Left half", "region_right": "Right half",
        "region_hint": "Tick a region to color only that half. Colors blend smoothly at the middle.",
        "mini_color": "Small notch color (solid)", "mini_text": "Small notch text color",
        "pick_color": "Pick a color",
    },
    "ar": {
        "idle_title": "لا توجد وسائط قيد التشغيل", "idle_sub": "شغّل شيئاً وسيظهر هنا",
        "untitled": "(بدون عنوان)", "toast_mute": "كتم / إلغاء الكتم",
        "menu_settings": "الإعدادات والثيمات…", "menu_themes": "الثيمات",
        "menu_pin": "تثبيت الحجم الموسّع", "menu_reset": "إعادة الموضع",
        "menu_hide": "إخفاء (يبقى في شريط المهام)", "menu_close": "إغلاق",
        "tray_toggle": "إظهار / إخفاء", "custom": "مخصص {n}",
        "set_title": "Sound Widget Overlay — الإعدادات",
        "tab_general": "عام", "tab_look": "المظهر", "tab_regions": "ألوان المناطق",
        "language": "اللغة", "layout": "شكل الكبسولة المنكمشة",
        "layout_mini": "صغيرة (ساعة + موجات صوت)", "layout_normal": "عادية (صورة + اسم + تقدم)",
        "size": "الحجم %", "clock24": "ساعة 24 ساعة", "autostart": "تشغيل مع ويندوز",
        "theme": "الثيم", "blur": "الزجاج (Blur)", "blur_off": "بدون", "blur_blur": "Blur",
        "blur_acrylic": "Acrylic (زجاج مصنفر)", "opacity": "العتامة", "brightness": "السطوع",
        "radius": "استدارة الزوايا", "softness": "نعومة حدّ المناطق", "tint": "لون الزجاج",
        "text_color": "لون النص", "accent": "لون التمييز",
        "accent_auto": "لون تلقائي من الغلاف", "reset_slot": "استعادة هذا الثيم",
        "region_top": "النصف العلوي", "region_bottom": "النصف السفلي",
        "region_left": "النصف الأيسر", "region_right": "النصف الأيمن",
        "region_hint": "فعّل المنطقة لتلوين ذلك النصف فقط. تمتزج الألوان بنعومة عند المنتصف.",
        "mini_color": "لون النوتش الصغيرة (لون واحد)", "mini_text": "لون نص النوتش الصغيرة",
        "pick_color": "اختر اللون",
    },
}
LANG = "en"


def T(key, **kw):
    s = STR.get(LANG, STR["en"]).get(key) or STR["en"].get(key, key)
    return s.format(**kw) if kw else s


def detect_language():
    try:
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return "ar" if (lid & 0x3FF) == 0x01 else "en"       # 0x01 = Arabic
    except Exception:
        return "en"


# ═════════════════════════════ دوال مساعدة ═════════════════════════════
VK_VOLUME_MUTE, VK_VOLUME_DOWN, VK_VOLUME_UP = 0xAD, 0xAE, 0xAF
KEYEVENTF_KEYUP = 0x0002


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t, lo=0.35):
    return max(0.0, min(1.0, (t - lo) / (1.0 - lo)))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp_rect(a, b, t):
    return QRectF(lerp(a.x(), b.x(), t), lerp(a.y(), b.y(), t),
                  lerp(a.width(), b.width(), t), lerp(a.height(), b.height(), t))


def fmt_time(sec):
    sec = int(max(0, sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def press_media_key(vk):
    try:
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


def app_id_of(session):
    try:
        return session.source_app_user_model_id or ""
    except Exception:
        return ""


def pretty_app(app_id):
    name = (app_id or "").split("!")[-1].split("\\")[-1]
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name


def mix_color(a, b, k):
    k = clamp(k, 0.0, 1.0)
    return QColor(int(a.red() + (b.red() - a.red()) * k),
                  int(a.green() + (b.green() - a.green()) * k),
                  int(a.blue() + (b.blue() - a.blue()) * k))


def draw_shadowed(p, rect, flags, text, color):
    """نص مع ظل خفيف ليبقى مقروءاً فوق الزجاج."""
    if color.lightness() > 128:
        p.setPen(QColor(10, 14, 30, int(90 * color.alphaF())))
        p.drawText(rect.translated(0, 1), flags, text)
    p.setPen(color)
    p.drawText(rect, flags, text)


# ═════════════════════════════ الثيمات (قوالب + 5 مخصصة) ═════════════════════════════
DEFAULT_LOOK = {
    "tint": "#6070a0", "text": "#ffffff", "opacity": 55, "brightness": 10,
    "radius": 18, "blur": "acrylic", "accent": "auto", "softness": 10,
    "zone_top": None, "zone_bottom": None, "zone_left": None, "zone_right": None,
    "mini_color": "#000000", "mini_text": "#ffffff",
}


def _look(**kw):
    d = dict(DEFAULT_LOOK)
    d.update(kw)
    return d


PRESETS = {
    "Frost Glass": _look(),
    "Dark Glass": _look(tint="#12141c", opacity=62, brightness=0),
    "Clear Glass": _look(tint="#ffffff", opacity=38, brightness=0, text="#1c2030"),
    "Midnight": _look(tint="#141e46", opacity=70, brightness=0),
    "Rose": _look(tint="#8c3c5a", opacity=62, brightness=5),
    "Emerald": _look(tint="#145a46", opacity=62, brightness=5),
    "Sunset": _look(tint="#964f28", opacity=62, brightness=5),
    "Solid Black": _look(tint="#0b0b0f", opacity=96, brightness=0, blur="off"),
}


def slot_label(key):
    if key.startswith("slot:"):
        return T("custom", n=key.split(":")[1])
    return key.split(":", 1)[1]


class ThemeStore:
    """يحفظ الثيم النشط وخمس خانات مخصصة في QSettings."""

    def __init__(self, settings):
        self.s = settings
        try:
            self.slots = json.loads(settings.value("slots", "{}", type=str))
        except Exception:
            self.slots = {}
        for i in range(1, SLOT_COUNT + 1):
            self.slots[str(i)] = _look(**{k: v for k, v in self.slots.get(str(i), {}).items()
                                          if k in DEFAULT_LOOK})
        self.active = settings.value("active", "preset:Frost Glass", type=str)
        self.last_slot = settings.value("last_slot", 1, type=int)
        if self.active not in self.keys():
            self.active = "preset:Frost Glass"

    def keys(self):
        return ["preset:" + n for n in PRESETS] + [f"slot:{i}" for i in range(1, SLOT_COUNT + 1)]

    def look(self, key=None):
        key = key or self.active
        if key.startswith("slot:"):
            return dict(self.slots[key.split(":")[1]])
        return dict(PRESETS.get(key.split(":", 1)[1], PRESETS["Frost Glass"]))

    def save(self):
        self.s.setValue("slots", json.dumps(self.slots))
        self.s.setValue("active", self.active)
        self.s.setValue("last_slot", self.last_slot)

    def activate(self, key):
        if key in self.keys():
            self.active = key
            if key.startswith("slot:"):
                self.last_slot = int(key.split(":")[1])
            self.save()
        return self.look()

    def edit(self, look):
        """أي تعديل على ثيم جاهز يُنسخ إلى آخر خانة مخصصة مستخدمة."""
        if not self.active.startswith("slot:"):
            self.active = f"slot:{self.last_slot}"
        n = self.active.split(":")[1]
        self.slots[n] = _look(**look)
        self.last_slot = int(n)
        self.save()
        return self.active

    def reset_active(self):
        if self.active.startswith("slot:"):
            self.slots[self.active.split(":")[1]] = _look()
            self.save()
        return self.look()


# ═════════════════════════════ ويندوز: زجاج، شكل النافذة، تشغيل تلقائي ═════════════════════════════
class _ACCENT(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class _WCA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t)]


def set_blur(hwnd, mode, tint, alpha):
    state = {"off": 0, "blur": 3, "acrylic": 4}.get(mode, 0)
    try:
        f = ctypes.windll.user32.SetWindowCompositionAttribute
        f.argtypes = [wintypes.HWND, ctypes.POINTER(_WCA)]
        grad = (alpha << 24) | (tint.blue() << 16) | (tint.green() << 8) | tint.red()
        acc = _ACCENT(state, 2 if state else 0, grad, 0)
        data = _WCA(19, ctypes.cast(ctypes.pointer(acc), ctypes.c_void_p), ctypes.sizeof(acc))
        f(int(hwnd), ctypes.byref(data))
    except Exception:
        pass


def disable_dwm_rounding(hwnd):
    """يمنع ويندوز 11 من تدوير الزوايا بنفسه (DWMWCP_DONOTROUND) كي لا يتعارض مع شكلنا."""
    try:
        v = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(int(hwnd)), 33,
                                                   ctypes.byref(v), ctypes.sizeof(v))
    except Exception:
        pass


def set_window_round(hwnd, w_px, h_px, r_px):
    """يقصّ النافذة الأصلية (والزجاج خلفها) بزوايا دائرية بالبكسل الفعلي، فلا تظهر زوايا حادة."""
    try:
        gdi, user = ctypes.windll.gdi32, ctypes.windll.user32
        gdi.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 6
        gdi.CreateRoundRectRgn.restype = ctypes.c_void_p
        user.SetWindowRgn.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_int]
        if w_px <= 0:
            user.SetWindowRgn(int(hwnd), None, True)
            return
        d = max(2, int(2 * r_px))
        rgn = gdi.CreateRoundRectRgn(0, 0, int(w_px) + 1, int(h_px) + 1, d, d)
        user.SetWindowRgn(int(hwnd), rgn, True)       # النظام يتملّك المنطقة
    except Exception:
        pass


_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_NAME = "SoundWidgetOverlay"
_RUN_OLD = "IslandMusicWidget"


def autostart_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _RUN_NAME)
        return True
    except Exception:
        return False


def set_autostart(enabled):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            for name in (_RUN_OLD,):
                try:
                    winreg.DeleteValue(k, name)
                except FileNotFoundError:
                    pass
            if enabled:
                if getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}"'
                else:
                    py = sys.executable.replace("python.exe", "pythonw.exe")
                    cmd = f'"{py}" "{os.path.abspath(__file__)}"'
                winreg.SetValueEx(k, _RUN_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, _RUN_NAME)
                except FileNotFoundError:
                    pass
    except Exception:
        traceback.print_exc()


def make_app_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(0, 0, 64, 64)
    g.setColorAt(0.0, QColor(124, 172, 255))
    g.setColorAt(1.0, QColor(160, 116, 255))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(g))
    p.drawRoundedRect(QRectF(3, 14, 58, 36), 14, 14)
    p.setBrush(QColor(255, 255, 255, 240))
    for i, hh in enumerate((10, 18, 12)):
        p.drawRoundedRect(QRectF(20 + i * 9, 32 - hh / 2, 5, hh), 2.5, 2.5)
    p.end()
    return QIcon(pm)


# ═════════════════════════════ الأغلفة (مضمّنة في الملف / بجانبه) ═════════════════════════════
def _find_image(buf):
    c = [i for i in (buf.find(b"\xff\xd8\xff"), buf.find(b"\x89PNG\r\n\x1a\n")) if i >= 0]
    return bytes(buf[min(c):]) if c else b""


def _syncsafe(b):
    return ((b[0] & 0x7F) << 21) | ((b[1] & 0x7F) << 14) | ((b[2] & 0x7F) << 7) | (b[3] & 0x7F)


def _id3_cover(f):
    hdr = f.read(10)
    if len(hdr) < 10 or hdr[:3] != b"ID3":
        return b""
    ver = hdr[3]
    size = min(_syncsafe(hdr[6:10]), 24 * 1024 * 1024)
    tag = f.read(size)
    pos = 0
    if hdr[5] & 0x40 and ver >= 3 and len(tag) >= 4:
        pos = _syncsafe(tag[0:4]) if ver == 4 else int.from_bytes(tag[0:4], "big") + 4
    idlen, hlen = (3, 6) if ver == 2 else (4, 10)
    while pos + hlen <= len(tag):
        fid = tag[pos:pos + idlen]
        if not fid or fid[0] == 0:
            break
        if ver == 2:
            fsize = int.from_bytes(tag[pos + 3:pos + 6], "big")
        elif ver == 4:
            fsize = _syncsafe(tag[pos + 4:pos + 8])
        else:
            fsize = int.from_bytes(tag[pos + 4:pos + 8], "big")
        body = tag[pos + hlen:pos + hlen + fsize]
        pos += hlen + fsize
        if fid in (b"APIC", b"PIC"):
            img = _find_image(body)
            if img:
                return img
        if fsize <= 0:
            break
    return b""


def _flac_cover(f):
    data = f.read(24 * 1024 * 1024)
    if data[:4] != b"fLaC":
        return b""
    pos = 4
    while pos + 4 <= len(data):
        h = data[pos]
        ln = int.from_bytes(data[pos + 1:pos + 4], "big")
        if (h & 0x7F) == 6:
            img = _find_image(data[pos + 4:pos + 4 + ln])
            if img:
                return img
        pos += 4 + ln
        if h & 0x80:
            break
    return b""


def _mp4_cover(f, size):
    chunk = 6 * 1024 * 1024
    for off in (0, max(0, size - chunk)):
        f.seek(off)
        buf = f.read(chunk)
        i = buf.find(b"covr")
        if i >= 0:
            img = _find_image(buf[i + 4:i + 4 + 8 * 1024 * 1024])
            if img:
                return img
        if size <= chunk:
            break
    return b""


def embedded_cover(path):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(12)
            f.seek(0)
            if head[:3] == b"ID3":
                return _id3_cover(f)
            if head[:4] == b"fLaC":
                return _flac_cover(f)
            if head[4:8] == b"ftyp" or os.path.splitext(path)[1].lower() in (".m4a", ".m4b", ".mp4"):
                return _mp4_cover(f, size)
    except Exception:
        pass
    return b""


def find_local_cover(filepath):
    try:
        d, fn = os.path.split(filepath)
        base = os.path.splitext(fn)[0]
        for n in (base, "cover", "folder", "poster", "thumb", "front", "albumart", "AlbumArtSmall"):
            for ext in (".jpg", ".jpeg", ".png", ".webp"):
                fp = os.path.join(d, n + ext)
                if os.path.isfile(fp):
                    with open(fp, "rb") as fh:
                        return fh.read()
    except Exception:
        pass
    return b""


def resolve_cover(filepath):
    if not filepath or not os.path.isfile(filepath):
        return b""
    return embedded_cover(filepath) or find_local_cover(filepath)


# ═════════════════════════════ MPC-HC عبر Web Interface ═════════════════════════════
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http_get(path, timeout=0.8):
    with _NO_PROXY.open(MPC_BASE + path, timeout=timeout) as r:
        return r.read()


def mpc_fetch_vars():
    text = _http_get("/variables.html").decode("utf-8", "replace")
    return {k: html.unescape(v).strip()
            for k, v in re.findall(r'<p id="(\w+)">(.*?)</p>', text, re.S)}


def mpc_fetch_snapshot():
    data = _http_get("/snapshot.jpg", timeout=1.5)
    return data if data[:2] == b"\xff\xd8" else b""


def mpc_send(wm_command, position=None):
    q = f"/command.html?wm_command={int(wm_command)}"
    if position is not None:
        s = int(max(0, position))
        q += f"&position={s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
    _http_get(q, timeout=1.5)


_KEEP = object()     # فشل مؤقت: أبقِ الواجهة كما هي


# ═════════════════════════════ Core Audio (الصوت + قياس الموجات) عبر ctypes ═════════════════════════════
class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]


def _guid(s):
    import uuid
    u = uuid.UUID(s)
    g = GUID()
    g.Data1, g.Data2, g.Data3 = u.time_low, u.time_mid, u.time_hi_version
    g.Data4 = (ctypes.c_ubyte * 8)(*(bytes([u.clock_seq_hi_variant, u.clock_seq_low]) + u.node.to_bytes(6, "big")))
    return g


_CLSID_ENUM = _guid("BCDE0395-E52F-467C-8E3D-C4579291692E")
_IID_ENUM = _guid("A95664D2-9614-4F35-A746-DE8DB63617E6")
_IID_METER = _guid("C02216F6-8C67-4B5B-9D00-D008E73E0064")
_IID_VOLUME = _guid("5CDF2C82-841E-4546-9722-0CF74078229A")


def _vcall(ptr, idx, argtypes, *args):
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    fn = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(vtbl[idx])
    return fn(ptr, *args)


class AudioEndpoint:
    """جهاز الإخراج الافتراضي: مستوى الصوت + الكتم + قياس الذروة. يُستخدم داخل خيط واحد فقط."""

    def __init__(self):
        self.ok = False
        self._ptrs = []
        self.vol = self.meter = None
        self._open()

    def _open(self):
        try:
            ole = ctypes.windll.ole32
            ole.CoCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
                                             ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
            ole.CoCreateInstance.restype = ctypes.c_long
            enum = ctypes.c_void_p()
            if ole.CoCreateInstance(ctypes.byref(_CLSID_ENUM), None, 23,
                                    ctypes.byref(_IID_ENUM), ctypes.byref(enum)) != 0 or not enum.value:
                return
            self._ptrs.append(enum.value)
            dev = ctypes.c_void_p()
            if _vcall(enum.value, 4, [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)],
                      0, 1, ctypes.byref(dev)) != 0 or not dev.value:
                return
            self._ptrs.append(dev.value)
            for iid, attr in ((_IID_VOLUME, "vol"), (_IID_METER, "meter")):
                out = ctypes.c_void_p()
                hr = _vcall(dev.value, 3, [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
                                           ctypes.POINTER(ctypes.c_void_p)],
                            ctypes.byref(iid), 23, None, ctypes.byref(out))
                if hr == 0 and out.value:
                    self._ptrs.append(out.value)
                    setattr(self, attr, out.value)
            self.ok = bool(self.vol or self.meter)
        except Exception:
            traceback.print_exc()
            self.ok = False

    def close(self):
        for p in reversed(self._ptrs):
            try:
                _vcall(p, 2, [])
            except Exception:
                pass
        self._ptrs = []
        self.vol = self.meter = None
        self.ok = False

    def peak(self):
        if not self.meter:
            return None
        v = ctypes.c_float()
        try:
            if _vcall(self.meter, 3, [ctypes.POINTER(ctypes.c_float)], ctypes.byref(v)) != 0:
                return None
        except Exception:
            return None
        return float(v.value)

    def get_volume(self):
        if not self.vol:
            return -1.0
        v = ctypes.c_float()
        try:
            if _vcall(self.vol, 9, [ctypes.POINTER(ctypes.c_float)], ctypes.byref(v)) == 0:
                return float(v.value)
        except Exception:
            pass
        return -1.0

    def set_volume(self, v):
        if self.vol:
            try:
                _vcall(self.vol, 7, [ctypes.c_float, ctypes.c_void_p], ctypes.c_float(clamp(v, 0.0, 1.0)), None)
            except Exception:
                pass

    def get_mute(self):
        if not self.vol:
            return False
        v = ctypes.c_int()
        try:
            if _vcall(self.vol, 15, [ctypes.POINTER(ctypes.c_int)], ctypes.byref(v)) == 0:
                return bool(v.value)
        except Exception:
            pass
        return False

    def set_mute(self, m):
        if self.vol:
            try:
                _vcall(self.vol, 14, [ctypes.c_int, ctypes.c_void_p], 1 if m else 0, None)
            except Exception:
                pass


class AudioWorker(QThread):
    """يقيس شدة الصوت الفعلية (للموجات) ومستوى الصوت 40 مرة في الثانية دون لمس الواجهة."""
    levels = pyqtSignal(float, float, bool)     # peak (-1 = غير متاح), volume (-1 = مجهول), muted

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._lock = threading.Lock()
        self._set_vol = None
        self._toggle = False

    def set_volume(self, v):
        with self._lock:
            self._set_vol = float(v)

    def toggle_mute(self):
        with self._lock:
            self._toggle = True

    def shutdown(self):
        self._running = False
        self.wait(2000)

    def run(self):
        com_ok = False
        try:
            com_ok = ctypes.windll.ole32.CoInitializeEx(None, 0) in (0, 1)
        except Exception:
            pass
        ep = AudioEndpoint()
        last_open, fails, tick, vol, muted = time.monotonic(), 0, 0, -1.0, False
        try:
            while self._running:
                now = time.monotonic()
                if (not ep.ok and now - last_open > 2.0) or now - last_open > 20.0 or fails >= 5:
                    ep.close()
                    ep = AudioEndpoint()
                    last_open, fails = now, 0
                with self._lock:
                    sv, self._set_vol = self._set_vol, None
                    tg, self._toggle = self._toggle, False
                if ep.ok:
                    if sv is not None:
                        ep.set_volume(sv)
                    if tg:
                        ep.set_mute(not ep.get_mute())
                    pk = ep.peak()
                    if pk is None:
                        fails += 1
                        pk = 0.0
                    else:
                        fails = 0
                    if tick % 4 == 0 or sv is not None or tg:
                        vol, muted = ep.get_volume(), ep.get_mute()
                    self.levels.emit(pk, vol, muted)
                else:
                    self.levels.emit(-1.0, -1.0, False)
                tick += 1
                self.msleep(25)
        finally:
            ep.close()
            if com_ok:
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass


# ═════════════════════════════ خيط الميديا (SMTC + MPC-HC) ═════════════════════════════
def _g(obj, name, default=None):
    try:
        v = getattr(obj, name)
        return default if v is None else v
    except Exception:
        return default


class MediaWorker(QThread):
    """QThread فيه Event Loop مستمر لـ asyncio. يرسل لقطات الحالة للواجهة عبر الإشارة state_changed."""
    state_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop = None
        self._dirty = None
        self._running = True

        self._manager = None            # مرجع دائم (يمنع الـ Garbage Collector)
        self._mgr_tokens = []
        self._session = None
        self._bound = None
        self._sess_tokens = []
        self._last_app = None
        self._none_since = None
        self._force_rebind = False
        self._sent_empty = False

        self._track_key = None
        self._thumb_bytes = b""
        self._thumb_retries = 0
        self._last_playing = False
        self._cb = self._on_event       # مرجع قوي للـ delegate

        self._source = None            # "smtc" أو "mpc"
        self._mpc_alive = False
        self._mpc_last_try = 0.0
        self._mpc_key = None
        self._mpc_thumb = b""
        self._mpc_snap_tries = 0
        self._mpc_snap_at = 0.0
        self._mpc_cover_done = False
        self._mpc_is_audio = False
        self._mpc_playing = False
        self._mpc_repeat = 0            # 0 إيقاف، 1 ملف واحد، 2 الكل
        self._mpc_prev_state = -1
        self._mpc_last_pos = 0.0
        self._mpc_last_dur = 0.0

    # ───── دورة حياة الخيط ─────
    def run(self):
        com_ok = False
        try:
            com_ok = ctypes.windll.ole32.CoInitializeEx(None, 0) in (0, 1)
        except Exception:
            pass
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._main())
        except Exception:
            traceback.print_exc()
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
            self._loop = None
            if com_ok:
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass

    def shutdown(self):
        self._running = False
        loop, dirty = self._loop, self._dirty
        if loop is not None and dirty is not None:
            try:
                loop.call_soon_threadsafe(dirty.set)
            except Exception:
                pass
        self.wait(3000)

    async def _main(self):
        self._dirty = asyncio.Event()
        try:
            self._manager = await MediaManager.request_async()
        except Exception:
            traceback.print_exc()
            self._emit_empty()
            return
        self._mgr_tokens = [
            ("sessions_changed", self._manager.add_sessions_changed(self._cb)),
            ("current_session_changed", self._manager.add_current_session_changed(self._cb)),
        ]
        self._dirty.set()
        try:
            while self._running:
                try:
                    await asyncio.wait_for(self._dirty.wait(), timeout=1.0 if self._mpc_alive else 2.0)
                except asyncio.TimeoutError:
                    pass
                if not self._running:
                    break
                self._dirty.clear()
                await asyncio.sleep(0.03)
                try:
                    await self._refresh()
                except Exception:
                    traceback.print_exc()
        finally:
            self._unbind_session()
            for name, token in self._mgr_tokens:
                try:
                    getattr(self._manager, "remove_" + name)(token)
                except Exception:
                    pass
            self._mgr_tokens = []

    def _on_event(self, sender, args):
        loop, dirty = self._loop, self._dirty
        if loop is not None and dirty is not None:
            try:
                loop.call_soon_threadsafe(dirty.set)
            except Exception:
                pass

    # ───── ربط الأحداث ─────
    def _bind(self, session):
        self._unbind_session()
        self._session = session
        self._force_rebind = False
        if session is None:
            return
        app = app_id_of(session)
        if app:
            self._last_app = app
        self._bound = session
        self._sess_tokens = []
        for name in ("media_properties_changed", "playback_info_changed", "timeline_properties_changed"):
            try:
                self._sess_tokens.append((name, getattr(session, "add_" + name)(self._cb)))
            except Exception:
                pass

    def _unbind_session(self):
        if self._bound is not None:
            for name, tok in self._sess_tokens:
                try:
                    getattr(self._bound, "remove_" + name)(tok)
                except Exception:
                    pass
        self._sess_tokens = []
        self._bound = None
        self._session = None

    def _pick_session(self):
        mgr = self._manager
        cur = None
        try:
            cur = mgr.get_current_session()
        except Exception:
            pass
        if cur is not None:
            self._none_since = None
            return cur
        sessions = []
        try:
            sessions = list(mgr.get_sessions())
        except Exception:
            pass
        if sessions:
            self._none_since = None
            for s in sessions:
                try:
                    if s.get_playback_info().playback_status == PlaybackStatus.PLAYING:
                        return s
                except Exception:
                    pass
            for s in sessions:
                if self._last_app and app_id_of(s) == self._last_app:
                    return s
            return sessions[0]
        now = time.monotonic()
        if self._none_since is None:
            self._none_since = now
        if self._session is not None and (now - self._none_since) < SESSION_GRACE_SEC:
            return self._session
        return None

    # ───── التحديث ─────
    async def _refresh(self):
        smtc = await self._refresh_smtc()
        mpc = await self._poll_mpc()
        data = self._choose(smtc, mpc)
        if data is _KEEP:
            return
        if data is None:
            self._emit_empty()
            return
        self._sent_empty = False
        self.state_changed.emit(data)

    async def _refresh_smtc(self):
        sess = self._pick_session()
        if sess is None:
            self._unbind_session()
            return None
        if (self._session is None or self._force_rebind
                or app_id_of(sess) != app_id_of(self._session)):
            self._bind(sess)
        for _ in range(2):
            try:
                return await self._read(self._session)
            except Exception:
                self._force_rebind = True
                fresh = self._pick_session()
                if fresh is None or fresh is self._session:
                    return _KEEP
                self._bind(fresh)
        return _KEEP

    async def _read(self, s):
        app = app_id_of(s)
        props = await s.try_get_media_properties_async()
        title = (props.title or "").strip()
        artist = (props.artist or props.album_artist or "").strip()
        album = (props.album_title or "").strip()

        key = (app, title, artist, album)
        thumb = None
        if key != self._track_key:
            self._track_key = key
            self._thumb_retries = 0
            self._thumb_bytes = await self._read_thumbnail(props)
            thumb = self._thumb_bytes
        elif not self._thumb_bytes and self._thumb_retries < 3:
            self._thumb_retries += 1
            data = await self._read_thumbnail(props)
            if data:
                self._thumb_bytes = data
                thumb = data

        pb = s.get_playback_info()
        playing = pb.playback_status == PlaybackStatus.PLAYING
        self._last_playing = playing
        ctl = pb.controls
        try:
            rate = float(pb.playback_rate) if pb.playback_rate else 1.0
        except Exception:
            rate = 1.0
        shuffle = bool(_g(pb, "is_shuffle_active", False))
        try:
            repeat = int(_g(pb, "auto_repeat_mode", 0))
        except Exception:
            repeat = 0

        tl = s.get_timeline_properties()
        start = tl.start_time.total_seconds()
        end = tl.end_time.total_seconds()
        position = tl.position.total_seconds() - start
        duration = max(0.0, end - start)
        now = time.time()
        try:
            updated = tl.last_updated_time.timestamp()
        except Exception:
            updated = now
        if updated < 1e9 or updated > now + 5:
            updated = now

        return {
            "has_session": True, "app": app, "title": title, "artist": artist,
            "playing": playing, "position": max(0.0, position), "duration": duration,
            "start": start, "updated": updated, "rate": rate if rate > 0 else 1.0,
            "can_seek": bool(ctl.is_playback_position_enabled) and duration > 0,
            "can_prev": bool(ctl.is_previous_enabled), "can_next": bool(ctl.is_next_enabled),
            "can_shuffle": bool(_g(ctl, "is_shuffle_enabled", True)),
            "can_repeat": bool(_g(ctl, "is_repeat_enabled", True)),
            "shuffle": shuffle, "repeat": repeat if repeat in (0, 1, 2) else 0,
            "thumb": thumb,
        }

    async def _read_thumbnail(self, props):
        ref = props.thumbnail
        if ref is None:
            return b""
        try:
            async def _go():
                stream = await ref.open_read_async()
                size = int(stream.size)
                if size <= 0:
                    return b""
                buf = Buffer(size)
                await stream.read_async(buf, buf.capacity, InputStreamOptions.READ_AHEAD)
                data = bytearray(buf.length)
                DataReader.from_buffer(buf).read_bytes(data)
                try:
                    stream.close()
                except Exception:
                    pass
                return bytes(data)
            return await asyncio.wait_for(_go(), timeout=3.0)
        except Exception:
            return b""

    # ───── جسر MPC-HC ─────
    async def _poll_mpc(self):
        now = time.monotonic()
        if not self._mpc_alive and now - self._mpc_last_try < 2.0:
            return None
        self._mpc_last_try = now
        loop = asyncio.get_running_loop()
        try:
            v = await loop.run_in_executor(None, mpc_fetch_vars)
            state = int(v.get("state", "-1") or -1)
            name = v.get("file", "")
            dur = float(v.get("duration", "0") or 0) / 1000.0
            pos = float(v.get("position", "0") or 0) / 1000.0
            try:
                rate = float(v.get("playbackrate", "1") or 1)
            except ValueError:
                rate = 1.0
        except Exception:
            self._mpc_alive = False
            return None
        self._mpc_alive = True

        if not name or state < 0:
            self._mpc_key = None
            self._mpc_thumb = b""
            return None

        # تكرار ملف واحد/الكل: نكتشف نهاية الملف ونعيد التشغيل
        ended = (self._mpc_prev_state == 2 and state != 2 and self._mpc_last_dur > 0
                 and self._mpc_last_pos >= self._mpc_last_dur - 3.0 and name == self._mpc_key)
        if ended and self._mpc_repeat in (1, 2):
            try:
                if self._mpc_repeat == 2 and MPC_CMD_FIRST_ITEM:
                    await loop.run_in_executor(None, mpc_send, MPC_CMD_FIRST_ITEM)
                await loop.run_in_executor(None, mpc_send, MPC_CMD_PLAY)
            except Exception:
                pass
        self._mpc_prev_state, self._mpc_last_pos, self._mpc_last_dur = state, pos, dur
        self._mpc_playing = (state == 2)

        thumb = None
        fp = v.get("filepath", "")
        if name != self._mpc_key:
            self._mpc_key = name
            self._mpc_thumb = b""
            self._mpc_snap_tries = 0
            self._mpc_cover_done = False
            self._mpc_is_audio = os.path.splitext(fp or name)[1].lower() in AUDIO_EXT
            thumb = b""
        if not self._mpc_thumb and not self._mpc_cover_done:
            self._mpc_cover_done = True
            cov = await loop.run_in_executor(None, resolve_cover, fp)
            if cov:
                self._mpc_thumb = thumb = cov
        if (not self._mpc_thumb and not self._mpc_is_audio and self._mpc_snap_tries < 40
                and state == 2 and pos > 1.5 and now - self._mpc_snap_at > 3.0):
            self._mpc_snap_tries += 1
            self._mpc_snap_at = now
            try:
                snap = await loop.run_in_executor(None, mpc_fetch_snapshot)
            except Exception:
                snap = b""
            if snap:
                self._mpc_thumb = thumb = snap

        return {
            "has_session": True, "app": "MPC-HC",
            "title": os.path.splitext(name)[0], "artist": "MPC-HC",
            "playing": state == 2, "position": max(0.0, pos), "duration": max(0.0, dur),
            "start": 0.0, "updated": time.time(), "rate": rate if rate > 0 else 1.0,
            "can_seek": dur > 0, "can_prev": True, "can_next": True,
            "can_shuffle": bool(MPC_CMD_SHUFFLE), "can_repeat": True,
            "shuffle": False, "repeat": self._mpc_repeat, "thumb": thumb,
        }

    def _choose(self, smtc, mpc):
        s = smtc if isinstance(smtc, dict) else None
        if smtc is _KEEP and self._source == "smtc" and not (mpc and mpc["playing"]):
            return _KEEP
        if mpc and mpc["playing"]:
            src, data = "mpc", mpc
        elif s and s["playing"]:
            src, data = "smtc", s
        elif mpc and (self._source == "mpc" or not s):
            src, data = "mpc", mpc
        elif s:
            src, data = "smtc", s
        else:
            return None
        if src != self._source:
            self._source = src
            if data.get("thumb") is None:
                data["thumb"] = self._mpc_thumb if src == "mpc" else self._thumb_bytes
        return data

    def _emit_empty(self):
        if self._sent_empty:
            return
        self._sent_empty = True
        self._source = None
        self._track_key = None
        self._thumb_bytes = b""
        self._mpc_key = None
        self._mpc_thumb = b""
        self.state_changed.emit({"has_session": False})

    # ───── أوامر من الواجهة ─────
    def command(self, name, arg=None):
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self._do(name, arg), loop)

    async def _do(self, name, arg):
        steps = [("seek", arg), ("play", None)] if name == "seek_play" else [(name, arg)]
        try:
            for nm, ar in steps:                      # تنفيذ متسلسل: التقديم ثم التشغيل
                if self._source == "mpc":
                    await self._do_mpc(nm, ar)
                else:
                    await self._do_smtc(nm, ar)
        except Exception:
            traceback.print_exc()
        if self._dirty is not None:
            self._dirty.set()

    async def _do_mpc(self, name, arg):
        loop = asyncio.get_running_loop()
        run = lambda *a: loop.run_in_executor(None, mpc_send, *a)
        if name == "play_pause":
            cmd = MPC_CMD_PAUSE if self._mpc_playing else MPC_CMD_PLAY
            self._mpc_playing = not self._mpc_playing
            await run(cmd)
        elif name == "play":
            self._mpc_playing = True
            await run(MPC_CMD_PLAY)
        elif name == "pause":
            self._mpc_playing = False
            await run(MPC_CMD_PAUSE)
        elif name == "prev":
            await run(MPC_CMD_PREV)
        elif name == "next":
            await run(MPC_CMD_NEXT)
        elif name == "seek":
            await run(-1, float(arg))
        elif name == "repeat":
            self._mpc_repeat = int(arg)
        elif name == "shuffle" and MPC_CMD_SHUFFLE:
            await run(MPC_CMD_SHUFFLE)

    async def _do_smtc(self, name, arg):
        s = self._session
        if s is None:
            return
        if name == "play_pause":
            if not await s.try_toggle_play_pause_async():
                await (s.try_pause_async() if self._last_playing else s.try_play_async())
        elif name == "play":
            await s.try_play_async()
        elif name == "pause":
            await s.try_pause_async()
        elif name == "prev":
            await s.try_skip_previous_async()
        elif name == "next":
            await s.try_skip_next_async()
        elif name == "seek":
            await s.try_change_playback_position_async(int(float(arg) * 10_000_000))
        elif name == "shuffle":
            await s.try_change_shuffle_active_async(bool(arg))
        elif name == "repeat" and _RepeatMode is not None:
            mode = {0: _RepeatMode.NONE, 1: _RepeatMode.TRACK, 2: _RepeatMode.LIST}[int(arg)]
            await s.try_change_auto_repeat_mode_async(mode)


# ═════════════════════════════ واجهة الكبسولة ═════════════════════════════
class IslandBubble(QWidget):
    def __init__(self, worker, audio, store, settings):
        super().__init__()
        self._worker = worker
        self._audio = audio
        self.store = store
        self._settings = settings
        self.look = store.look()
        self._text = QColor(self.look["text"])
        self._accent_custom = None if self.look["accent"] == "auto" else QColor(self.look["accent"])
        self._accent_cover = QColor(DEFAULT_ACCENT)

        self._mode = settings.value("mode", "mini", type=str)
        if self._mode not in SIZES:
            self._mode = "mini"
        self._scale = clamp(float(settings.value("scale", 1.0, type=float)), 0.6, 2.2)
        self._clock24 = settings.value("clock24", False, type=bool)
        self._pinned = settings.value("pinned", False, type=bool)

        # ─ حالة الميديا ─
        self._has = False
        self._title = ""
        self._artist = ""
        self._app = ""
        self._playing = False
        self._pos = 0.0
        self._updated = time.time()
        self._duration = 0.0
        self._start = 0.0
        self._rate = 1.0
        self._can_seek = False
        self._can_prev = True
        self._can_next = True
        self._can_shuffle = True
        self._can_repeat = True
        self._shuffle = False
        self._repeat = 0
        self._ctl_hold_until = 0.0
        self._cover = None

        # ─ الصوت ─
        self._peak = -1.0
        self._volume = -1.0
        self._muted = False
        self._vol_drag = False
        self._vol_panel = False
        self._vp = 0.0
        self._bars = [0.0] * 5
        self._wave_last = time.monotonic()

        # ─ تقديم بالضغط المطوّل ─
        self._ff = False
        self._ff_pos = 0.0
        self._ff_t0 = 0.0
        self._ff_last = 0.0
        self._ff_speed = 2
        self._ff_resume = False

        # ─ حالة الواجهة ─
        self._p = 0.0
        self._expanded = False
        self._hover = None
        self._press_btn = None
        self._dragging = False
        self._drag_off = QPoint()
        self._seeking = False
        self._seek_frac = 0.0
        self._hold_until = 0.0
        self._out_ticks = 0
        self._menu_open = False
        self._resizing = False
        self._rs = None
        self._dlg = None
        self._toast = ""
        self._toast_until = 0.0
        self._last_clock = ""
        self._marq_off = 0.0
        self._marq_wait = 1.4
        self._marq_last = time.monotonic()

        self._setup_window()
        self._setup_animations()
        self._setup_timers()
        self._restore_position()

        if self._pinned:
            self._p = 1.0
            self._expanded = True
        self.setGeometry(self._target_rect(self._expanded))

    # ───────── الثيم ─────────
    def accent(self):
        return self._accent_custom or self._accent_cover

    def _fg(self, a=255):
        c = QColor(self._text)
        c.setAlpha(int(clamp(a, 0, 255)))
        return c

    def apply_look(self, look):
        self.look = dict(look)
        self._text = QColor(look["text"])
        self._accent_custom = None if look["accent"] == "auto" else QColor(look["accent"])
        self.apply_blur()
        self.update()

    def update_look(self, look):
        key = self.store.edit(look)
        self.apply_look(self.store.look())
        return key

    def activate_theme(self, key):
        look = self.store.activate(key)
        self.apply_look(look)
        return look

    def reset_theme(self):
        look = self.store.reset_active()
        self.apply_look(look)
        return look

    def apply_blur(self):
        if not self.isVisible():
            return
        t = self.look
        alpha = max(6, int(t["opacity"] * 0.3 * 2.55))
        hwnd = int(self.winId())
        disable_dwm_rounding(hwnd)
        set_blur(hwnd, t["blur"], QColor(t["tint"]), alpha)
        self._update_region()

    def _cur_radius(self):
        r = self.look["radius"]
        comp = min(r, 14) if self._mode == "mini" else r
        return lerp(comp, r + 6, self._p)

    def _update_region(self):
        if not self.isVisible():
            return
        hwnd = int(self.winId())
        if self.look["blur"] == "off":
            set_window_round(hwnd, 0, 0, 0)
            return
        dpr = self.devicePixelRatioF()
        set_window_round(hwnd, round(self.width() * dpr), round(self.height() * dpr),
                         self._cur_radius() * self._scale * dpr)

    def showEvent(self, e):
        super().showEvent(e)
        self.apply_blur()
        self._sync_timers()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._sync_timers()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_region()
        self._ensure_marquee()

    # ───────── إعدادات عامة ─────────
    def set_scale(self, s):
        self._scale = clamp(float(s), 0.6, 2.2)
        self._settings.setValue("scale", self._scale)
        self._set_expanded(self._expanded, force=True)

    def set_mode(self, mode):
        if mode in SIZES and mode != self._mode:
            self._mode = mode
            self._settings.setValue("mode", mode)
            self._set_expanded(self._expanded, force=True)
            self._text_changed()

    def set_clock24(self, flag):
        self._clock24 = bool(flag)
        self._settings.setValue("clock24", self._clock24)
        self.update()

    def set_language(self, code):
        global LANG
        LANG = code if code in STR else "en"
        self._settings.setValue("lang", LANG)
        self._text_changed()

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def open_settings(self):
        if self._dlg is not None and self._dlg.isVisible():
            self._dlg.raise_()
            self._dlg.activateWindow()
            return
        self._dlg = SettingsDialog(self)
        self._dlg.show()
        self._dlg.raise_()
        self._dlg.activateWindow()

    def reopen_settings(self):
        if self._dlg is not None:
            self._dlg.close()
            self._dlg = None
        self.open_settings()

    # ───────── النافذة والحركة ─────────
    def _setup_window(self):
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)

    def _setup_animations(self):
        self._anim_geo = QPropertyAnimation(self, b"geometry", self)
        self._anim_p = QPropertyAnimation(self, b"expandProgress", self)
        for a in (self._anim_geo, self._anim_p):
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._group = QParallelAnimationGroup(self)
        self._group.addAnimation(self._anim_geo)
        self._group.addAnimation(self._anim_p)
        self._anim_vp = QPropertyAnimation(self, b"volPanel", self)
        self._anim_vp.setDuration(180)
        self._anim_vp.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_timers(self):
        def mk(ms, slot, start=False, precise=False):
            t = QTimer(self)
            if precise:
                t.setTimerType(Qt.TimerType.PreciseTimer)
            t.setInterval(ms)
            t.timeout.connect(slot)
            if start:
                t.start()
            return t
        self._pos_timer = mk(POSITION_TICK_MS, self._tick_position, True)
        self._marq_timer = mk(16, self._tick_marquee, precise=True)
        self._wave_timer = mk(16, self._tick_wave, precise=True)
        self._hover_timer = mk(110, self._hover_check, True)
        self._raise_timer = mk(3000, self._keep_on_top, True)
        self._ff_timer = mk(40, self._tick_ff, precise=True)
        self._vol_close = QTimer(self)
        self._vol_close.setSingleShot(True)
        self._vol_close.timeout.connect(lambda: self._show_vol_panel(False))
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._begin_ff)

    def _sync_timers(self):
        want = self.isVisible() and self._mode == "mini" and self._p < 0.98
        if want and not self._wave_timer.isActive():
            self._wave_last = time.monotonic()
            self._wave_timer.start()
        elif not want:
            self._wave_timer.stop()

    def _get_p(self):
        return self._p

    def _set_p(self, v):
        self._p = float(v)
        self.update()

    expandProgress = pyqtProperty(float, _get_p, _set_p)

    def _get_vp(self):
        return self._vp

    def _set_vp(self, v):
        self._vp = float(v)
        self.update()

    volPanel = pyqtProperty(float, _get_vp, _set_vp)

    def _show_vol_panel(self, flag, auto_ms=3200):
        if flag == self._vol_panel and not flag:
            return
        self._vol_panel = flag
        self._anim_vp.stop()
        self._anim_vp.setStartValue(self._vp)
        self._anim_vp.setEndValue(1.0 if flag else 0.0)
        self._anim_vp.start()
        if flag:
            self._vol_close.start(auto_ms)
        else:
            self._vol_close.stop()

    # ───────── الموضع والشاشة ─────────
    def _screen_geo(self, pt=None):
        scr = QGuiApplication.screenAt(pt) if pt is not None else None
        return (scr or QGuiApplication.primaryScreen()).availableGeometry()

    def _restore_position(self):
        ag = self._screen_geo()
        cx = self._settings.value("cx", -99999, type=int)
        top = self._settings.value("top", -99999, type=int)
        if cx == -99999 or top == -99999 or not ag.adjusted(-50, -50, 50, 50).contains(QPoint(cx, top)):
            cx, top = ag.center().x(), ag.top() + 12
        self._anchor_cx, self._top = cx, top

    def _save_position(self):
        self._settings.setValue("cx", self._anchor_cx)
        self._settings.setValue("top", self._top)

    def _target_rect(self, expanded):
        bw, bh = (EXPAND_W, EXPAND_H) if expanded else SIZES[self._mode]
        W, H = int(bw * self._scale), int(bh * self._scale)
        ag = self._screen_geo(QPoint(self._anchor_cx, self._top))
        x = clamp(self._anchor_cx - W // 2, ag.left() + 6, max(ag.left() + 6, ag.right() - W - 5))
        y = clamp(self._top, ag.top(), max(ag.top(), ag.bottom() - H))
        return QRect(int(x), int(y), W, H)

    def _reset_position(self):
        ag = self._screen_geo()
        self._anchor_cx, self._top = ag.center().x(), ag.top() + 12
        self._save_position()
        self._set_expanded(self._expanded, force=True)

    def _keep_on_top(self):
        if self.isVisible() and not self._menu_open:
            self.raise_()

    def _set_expanded(self, flag, force=False):
        if flag == self._expanded and not force:
            return
        self._expanded = flag
        self._group.stop()
        dur = 340 if flag else 290
        self._anim_geo.setDuration(dur)
        self._anim_p.setDuration(dur)
        self._anim_geo.setStartValue(self.geometry())
        self._anim_geo.setEndValue(self._target_rect(flag))
        self._anim_p.setStartValue(self._p)
        self._anim_p.setEndValue(1.0 if flag else 0.0)
        self._group.start()
        if not flag:
            self._show_vol_panel(False)
        self._sync_timers()

    def enterEvent(self, e):
        self._out_ticks = 0
        if not self._dragging and not self._resizing:
            self._set_expanded(True)
        super().enterEvent(e)

    def _hover_check(self):
        if self._dragging or self._seeking or self._menu_open or self._resizing or self._ff or self._vol_drag:
            self._out_ticks = 0
            return
        if self.frameGeometry().contains(QCursor.pos()):
            self._out_ticks = 0
            if not self._expanded:
                self._set_expanded(True)
        elif self._expanded and not self._pinned:
            self._out_ticks += 1
            if self._out_ticks >= 3:
                self._out_ticks = 0
                self._hover = None
                self._set_expanded(False)

    # ───────── استقبال البيانات ─────────
    def on_state(self, d):
        if not d.get("has_session"):
            self._has = False
            self._playing = False
            self._duration = 0.0
            self._pos = 0.0
            self._cover = None
            self._accent_cover = QColor(DEFAULT_ACCENT)
            self._text_changed()
            return
        self._has = True
        self._app = pretty_app(d["app"])
        self._title = d["title"] or T("untitled")
        self._artist = d["artist"] or self._app
        self._duration = d["duration"]
        self._start = d["start"]
        self._rate = d["rate"]
        self._can_seek = d["can_seek"]
        self._can_prev = d["can_prev"]
        self._can_next = d["can_next"]
        self._can_shuffle = d.get("can_shuffle", True)
        self._can_repeat = d.get("can_repeat", True)
        now = time.time()
        if now >= self._ctl_hold_until:
            self._shuffle = d.get("shuffle", False)
            self._repeat = d.get("repeat", 0)
        if not self._ff:
            self._playing = d["playing"]
            if now >= self._hold_until:
                self._pos = d["position"]
                self._updated = d["updated"]
        if d.get("thumb") is not None:
            self._set_cover(d["thumb"])
        self._text_changed()

    def on_levels(self, peak, vol, muted):
        self._peak = peak
        changed = False
        if vol >= 0 and not self._vol_drag and abs(vol - self._volume) > 0.001:
            self._volume, changed = vol, True
        if muted != self._muted:
            self._muted, changed = muted, True
        if changed and (self._p > 0.5 or self._vp > 0):
            self.update()

    def _set_cover(self, data):
        self._cover = None
        self._accent_cover = QColor(DEFAULT_ACCENT)
        if not data:
            return
        pm = QPixmap()
        if not pm.loadFromData(data) or pm.isNull():
            return
        side = min(pm.width(), pm.height())
        pm = pm.copy((pm.width() - side) // 2, (pm.height() - side) // 2, side, side)
        self._cover = pm.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
        c = self._cover.toImage().scaled(1, 1, Qt.AspectRatioMode.IgnoreAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation).pixelColor(0, 0)
        h, s, l, _ = c.getHslF()
        if s < 0.08 or h < 0:
            self._accent_cover = QColor(236, 236, 242)
        else:
            self._accent_cover = QColor.fromHslF(h, min(1.0, max(s, 0.4)), max(l, 0.62), 1.0)

    # ───────── الوقت ─────────
    def _current_position(self):
        if self._ff:
            return self._ff_pos
        pos = self._pos
        if self._has and self._playing:
            pos += (time.time() - self._updated) * self._rate
        if self._duration > 0:
            pos = min(pos, self._duration)
        return max(0.0, pos)

    def _clock_text(self):
        n = datetime.now()
        if self._clock24:
            return n.strftime("%H:%M")
        return n.strftime("%I:%M %p").lstrip("0")

    def _tick_position(self):
        if not self.isVisible():
            return
        clock = self._clock_text()
        if clock != self._last_clock:
            self._last_clock = clock
            self.update()
        elif (self._has and self._playing and not self._seeking
              and (self._mode == "normal" or self._p > 0.05)):
            self.update()

    # ───────── النصوص والمارکي ─────────
    def _title_text(self):
        if time.time() < self._toast_until:
            return self._toast
        return self._title if self._has else T("idle_title")

    def _artist_text(self):
        if self._ff:
            return f"⏩ ×{self._ff_speed}"
        if time.time() < self._toast_until:
            return ""
        return self._artist if self._has else T("idle_sub")

    def _title_font(self):
        f = QFont("Segoe UI")
        f.setPointSizeF(lerp(9.5, 10.5, self._p))
        f.setWeight(QFont.Weight.DemiBold)
        return f

    def _artist_font(self):
        f = QFont("Segoe UI")
        f.setPointSizeF(9.0)
        return f

    def _small_font(self):
        f = QFont("Segoe UI")
        f.setPointSizeF(8.0)
        return f

    def _title_overflows(self):
        fm = QFontMetricsF(self._title_font())
        return fm.horizontalAdvance(self._title_text()) > self._layout()["title"].width() + 0.5

    def _text_changed(self):
        self._marq_off = 0.0
        self._marq_wait = 1.4
        self._ensure_marquee()
        self.update()

    def _ensure_marquee(self):
        if self._title_overflows():
            if not self._marq_timer.isActive():
                self._marq_last = time.monotonic()
                self._marq_timer.start()
        else:
            self._marq_off = 0.0
            self._marq_timer.stop()

    def _tick_marquee(self):
        now = time.monotonic()
        dt = min(0.1, now - self._marq_last)
        self._marq_last = now
        tw = QFontMetricsF(self._title_font()).horizontalAdvance(self._title_text())
        if tw <= self._layout()["title"].width() + 0.5:
            self._marq_off = 0.0
            self._marq_timer.stop()
            self.update()
            return
        if self._marq_wait > 0:
            self._marq_wait -= dt
            return
        self._marq_off += MARQUEE_SPEED * dt
        if self._marq_off >= tw + MARQUEE_GAP:
            self._marq_off = 0.0
            self._marq_wait = 1.4
        self.update()

    def _show_toast(self, text, ms=900):
        self._toast = text
        self._toast_until = time.time() + ms / 1000.0
        self._text_changed()
        QTimer.singleShot(ms + 30, lambda: self._text_changed() if time.time() >= self._toast_until else None)

    # ───────── موجات الصوت (تتبع الصوت الفعلي) ─────────
    def _tick_wave(self):
        now = time.monotonic()
        dt = min(0.05, now - self._wave_last)
        self._wave_last = now
        if self._peak >= 0:
            lvl = min(1.0, (self._peak ** 0.55) * 1.4)
        elif self._playing:
            lvl = 0.45 + 0.2 * math.sin(now * 2.3)          # بديل إن تعذّر قياس الصوت
        else:
            lvl = 0.0
        for i in range(len(self._bars)):
            mod = 0.55 + 0.45 * math.sin(now * (3.1 + i * 0.83) + i * 1.7)
            target = lvl * (0.3 + 0.7 * mod)
            cur = self._bars[i]
            cur += (target - cur) * min(1.0, (24.0 if target > cur else 9.0) * dt)
            self._bars[i] = cur
        self.update()

    # ───────── التخطيط ─────────
    def _layout(self):
        s = self._scale
        w, h = self.width() / s, self.height() / s
        t = self._p
        ox = (w - EXPAND_W) / 2            # يبقي المحتوى الكبير في منتصف الشاشة أثناء التمدد

        def R(x, y, wd, ht):
            return QRectF(x + ox, y, wd, ht)

        def Bt(cx, cy, sz):
            return QRectF(cx + ox - sz / 2, cy - sz / 2, sz, sz)

        B = {
            "cover": R(14, 12, 48, 48), "title": R(74, 15, 290, 22),
            "artist": R(74, 36, 290, 20), "bar": R(66, 117.5, 248, 5),
        }
        if self._mode == "normal":
            C = {"cover": QRectF(11, 6, 34, 34), "title": QRectF(54, 12, 200, 22),
                 "artist": QRectF(54, 30, 200, 20), "bar": QRectF(14, 44, 242, 3)}
            L = {k: lerp_rect(C[k], B[k], t) for k in B}
        else:
            L = dict(B)
        L.update({
            "w": w, "h": h, "ox": ox,
            "time_l": R(14, 111, 48, 18), "time_r": R(318, 111, 48, 18),
            "prev": Bt(138, 88, 32), "play": Bt(190, 88, 40), "next": Bt(242, 88, 32),
            "shuffle": Bt(30, 88, 30), "repeat": Bt(64, 88, 30), "volume": Bt(350, 88, 30),
            "vtrack": R(24, 85.5, 252, 5), "vslider": R(18, 76, 266, 24), "vpct": R(284, 78, 40, 20),
            "m_icon": QRectF(10, 7, 22, 22), "m_clock": QRectF(38, 0, 86, 36),
            "m_wave": QRectF(128, 8, 34, 20),
        })
        return L

    def _bar_visible(self):
        return self._mode == "normal" or self._p > 0.7

    def _hit(self, pos):
        pos = QPointF(pos.x() / self._scale, pos.y() / self._scale)
        L = self._layout()
        if self._p > 0.7:
            if self._vp > 0.5:
                if L["volume"].adjusted(-4, -4, 4, 4).contains(pos):
                    return "volume"
                if L["vslider"].contains(pos):
                    return "vslider"
            else:
                for name in ("prev", "play", "next", "shuffle", "repeat", "volume"):
                    if L[name].adjusted(-3, -3, 3, 3).contains(pos):
                        return name
        if self._has and self._can_seek and self._duration > 0 and self._bar_visible():
            if L["bar"].adjusted(-4, -6, 4, 8).contains(pos):
                return "bar"
        return None

    def _frac_from_x(self, x):
        bar = self._layout()["bar"]
        return clamp((x / self._scale - bar.left()) / bar.width(), 0.0, 1.0)

    def _vol_from_x(self, x):
        tr = self._layout()["vtrack"]
        return clamp((x / self._scale - tr.left()) / tr.width(), 0.0, 1.0)

    # ───────── الرسم ─────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
                         | QPainter.RenderHint.SmoothPixmapTransform)
        s = self._scale
        p.scale(s, s)
        w, h = self.width() / s, self.height() / s
        t = self._p
        mini = self._mode == "mini"
        L = self._layout()

        self._paint_glass(p, w, h, t, mini)

        a_ctl = smooth(t, 0.5)
        a_main = a_ctl if mini else 1.0
        a_mini = max(0.0, 1.0 - t * 2.4) if mini else 0.0
        if a_mini > 0.01:
            self._draw_mini(p, L, a_mini)
        if a_main > 0.01:
            p.setOpacity(a_main)
            self._draw_cover(p, L["cover"])
            self._draw_texts(p, L)
            self._draw_progress(p, L)
            p.setOpacity(1.0)
        if a_ctl > 0.02:
            self._draw_controls(p, L, a_ctl)
        p.end()

    def _zone_brush(self, w, h, side, col, soft):
        c1, c0 = QColor(col), QColor(col)
        c0.setAlpha(0)
        g = QLinearGradient(0, 0, 0, h) if side in ("top", "bottom") else QLinearGradient(0, 0, w, 0)
        sw = max(0.0005, clamp(soft, 0, 100) / 100.0 * 0.5)
        lo, hi = 0.5 - sw, 0.5 + sw
        if side in ("top", "left"):
            g.setColorAt(0.0, c1)
            g.setColorAt(lo, c1)
            g.setColorAt(hi, c0)
            g.setColorAt(1.0, c0)
        else:
            g.setColorAt(0.0, c0)
            g.setColorAt(lo, c0)
            g.setColorAt(hi, c1)
            g.setColorAt(1.0, c1)
        return QBrush(g)

    def _paint_glass(self, p, w, h, t, mini):
        th = self.look
        radius = self._cur_radius()
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
        k = th["opacity"] / 100.0
        b = th["brightness"] / 100.0
        gfac = t if mini else 1.0

        if gfac > 0.01:
            p.save()
            p.setOpacity(gfac)
            base = mix_color(QColor(th["tint"]), QColor(255, 255, 255) if b > 0 else QColor(0, 0, 0),
                             abs(b) * 0.7)
            base.setAlpha(int(255 * k * (0.62 if th["blur"] != "off" else 1.0)))
            p.fillPath(path, base)

            g = QLinearGradient(0, 0, 0, h)
            g.setColorAt(0.0, QColor(255, 255, 255, min(255, int(120 * k * (1 + max(b, 0))))))
            g.setColorAt(1.0, QColor(232, 238, 255, min(255, int(40 * k))))
            p.fillPath(path, QBrush(g))

            rg = QRadialGradient(QPointF(w * 0.16, h * 0.4), w * 0.7)
            c1 = QColor(self.accent())
            c1.setAlpha(46)
            c0 = QColor(self.accent())
            c0.setAlpha(0)
            rg.setColorAt(0.0, c1)
            rg.setColorAt(1.0, c0)
            p.fillPath(path, QBrush(rg))

            # ألوان المناطق (نصف علوي / سفلي / أيمن / أيسر)
            p.setClipPath(path)
            for side in ("top", "bottom", "left", "right"):
                zc = th.get("zone_" + side)
                if zc:
                    col = QColor(zc)
                    col.setAlpha(int(255 * min(1.0, k + 0.1)))
                    p.fillRect(QRectF(0, 0, w, h), self._zone_brush(w, h, side, col, th["softness"]))
            p.setClipping(False)

            gloss = QLinearGradient(0, 0, 0, h * 0.5)
            gloss.setColorAt(0.0, QColor(255, 255, 255, 60))
            gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillPath(path, QBrush(gloss))

            bg = QLinearGradient(0, 0, 0, h)
            bg.setColorAt(0.0, QColor(255, 255, 255, 190))
            bg.setColorAt(1.0, QColor(255, 255, 255, 70))
            p.setPen(QPen(QBrush(bg), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.restore()

        if mini:                                   # النوتش الصغيرة: لون واحد صلب بلا تدرج
            a = clamp(1.0 - t * 1.5, 0.0, 1.0)
            if a > 0.0:
                c = QColor(th["mini_color"])
                c.setAlpha(int(255 * a))
                p.fillPath(path, c)

    # ── النوتش الصغيرة: أيقونة + ساعة + موجات ──
    def _draw_mini(self, p, L, a):
        col = QColor(self.look["mini_text"])
        p.save()
        p.setOpacity(a)
        r = L["m_icon"]
        acc = self.accent()
        if self._cover is not None:
            clip = QPainterPath()
            clip.addEllipse(r)
            p.save()
            p.setClipPath(clip)
            p.drawPixmap(r, self._cover, QRectF(self._cover.rect()))
            p.restore()
            p.setPen(QPen(acc, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(r)
        else:
            p.setPen(QPen(acc, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(r.adjusted(1, 1, -1, -1))
            c = r.center()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(acc)
            if self._playing:
                p.drawRoundedRect(QRectF(c.x() - 3.6, c.y() - 4.5, 2.6, 9), 1, 1)
                p.drawRoundedRect(QRectF(c.x() + 1.0, c.y() - 4.5, 2.6, 9), 1, 1)
            else:
                p.drawPolygon(QPolygonF([QPointF(c.x() - 2.8, c.y() - 4.8), QPointF(c.x() - 2.8, c.y() + 4.8),
                                         QPointF(c.x() + 4.8, c.y())]))
        f = QFont("Segoe UI")
        f.setPointSizeF(10.5)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(col)
        p.drawText(L["m_clock"], Qt.AlignmentFlag.AlignCenter, self._clock_text())

        wr = L["m_wave"]
        bw, gap, n = 3.0, 3.5, len(self._bars)
        x0 = wr.right() - (n * bw + (n - 1) * gap)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        for i, v in enumerate(self._bars):
            bh = 3.0 + clamp(v, 0.0, 1.0) * 15.0
            p.drawRoundedRect(QRectF(x0 + i * (bw + gap), wr.center().y() - bh / 2, bw, bh), 1.5, 1.5)
        p.restore()

    # ── الجزء الكبير ──
    def _draw_cover(self, p, r):
        rad = lerp(8, 12, self._p) if self._mode == "normal" else 12
        clip = QPainterPath()
        clip.addRoundedRect(r, rad, rad)
        p.save()
        p.setClipPath(clip)
        if self._cover is not None:
            p.drawPixmap(r, self._cover, QRectF(self._cover.rect()))
        else:
            gg = QLinearGradient(r.topLeft(), r.bottomRight())
            gg.setColorAt(0.0, QColor(90, 96, 124))
            gg.setColorAt(1.0, QColor(38, 40, 56))
            p.fillRect(r, QBrush(gg))
            f = QFont("Segoe UI Symbol")
            f.setPixelSize(int(r.height() * 0.5))
            p.setFont(f)
            p.setPen(QColor(255, 255, 255, 190))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "▶" if self._app == "MPC-HC" else "♪")
        if self._has and not self._playing:
            p.fillRect(r, QColor(0, 0, 0, 80))
        p.restore()
        p.setPen(QPen(QColor(255, 255, 255, 110), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, rad, rad)

    def _draw_texts(self, p, L):
        self._draw_marquee(p, L["title"], self._title_text(), self._title_font(), self._fg(245))
        a = smooth(self._p, 0.45)
        txt = self._artist_text()
        if a > 0.02 and txt:
            f = self._artist_font()
            el = QFontMetricsF(f).elidedText(txt, Qt.TextElideMode.ElideRight, L["artist"].width())
            p.setFont(f)
            draw_shadowed(p, L["artist"], Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                          el, self._fg(215 * a))

    def _draw_marquee(self, p, rect, text, font, color):
        fm = QFontMetricsF(font)
        tw = fm.horizontalAdvance(text)
        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        if tw <= rect.width() + 0.5:
            p.setFont(font)
            draw_shadowed(p, rect, flags, text, color)
            return
        dpr = self.devicePixelRatioF() * self._scale
        img = QImage(max(1, int(rect.width() * dpr)), max(1, int(rect.height() * dpr)),
                     QImage.Format.Format_ARGB32_Premultiplied)
        img.setDevicePixelRatio(dpr)
        img.fill(Qt.GlobalColor.transparent)
        ip = QPainter(img)
        ip.setRenderHints(QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.Antialiasing)
        ip.setFont(font)
        x = -self._marq_off
        draw_shadowed(ip, QRectF(x, 0, tw + 4, rect.height()), flags, text, color)
        draw_shadowed(ip, QRectF(x + tw + MARQUEE_GAP, 0, tw + 4, rect.height()), flags, text, color)
        ip.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        fw = min(0.2, 16.0 / rect.width())
        mask = QLinearGradient(0, 0, rect.width(), 0)
        mask.setColorAt(0.0, QColor(0, 0, 0, 0 if self._marq_off > 1 else 255))
        mask.setColorAt(fw, QColor(0, 0, 0, 255))
        mask.setColorAt(1.0 - fw, QColor(0, 0, 0, 255))
        mask.setColorAt(1.0, QColor(0, 0, 0, 0))
        ip.fillRect(QRectF(0, 0, rect.width(), rect.height()), QBrush(mask))
        ip.end()
        p.drawImage(rect.topLeft(), img)

    def _draw_progress(self, p, L):
        bar = L["bar"]
        pos = self._seek_frac * self._duration if self._seeking else self._current_position()
        frac = clamp(pos / self._duration, 0.0, 1.0) if self._duration > 0 else 0.0
        r = bar.height() / 2
        acc = self.accent()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._fg(70))
        p.drawRoundedRect(bar, r, r)
        if frac > 0:
            fill = QRectF(bar.left(), bar.top(), max(bar.height(), bar.width() * frac), bar.height())
            gr = QLinearGradient(fill.topLeft(), fill.topRight())
            gr.setColorAt(0.0, acc)
            gr.setColorAt(1.0, QColor(acc).lighter(125))
            p.setBrush(QBrush(gr))
            p.drawRoundedRect(fill, r, r)
        active = self._seeking or self._hover == "bar"
        if self._has and self._duration > 0 and (self._p > 0.6 or active):
            kx = bar.left() + bar.width() * frac
            p.setBrush(self._fg(255 if active else 255 * smooth(self._p, 0.5)))
            kr = 5.0 if active else 4.0
            p.drawEllipse(QPointF(kx, bar.center().y()), kr, kr)
        a = smooth(self._p, 0.5)
        if a > 0.02 and self._has:                  # الوقت المنقضي يساراً والمدة الكلية يميناً
            p.setFont(self._small_font())
            p.setPen(self._fg(225 * a))
            p.drawText(L["time_l"], Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, fmt_time(pos))
            if self._duration > 0:
                p.drawText(L["time_r"], Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           fmt_time(self._duration))

    # ── الأزرار ──
    def _draw_controls(self, p, L, a):
        vp = self._vp
        cp = a * (1.0 - vp)
        acc = self.accent()
        dim = 105
        p.setPen(Qt.PenStyle.NoPen)
        if cp > 0.02:
            for name in ("prev", "play", "next", "shuffle", "repeat"):
                r = L[name]
                enabled = self._has and {"prev": self._can_prev, "next": self._can_next,
                                         "shuffle": self._can_shuffle, "repeat": self._can_repeat}.get(name, True)
                if self._hover == name and enabled:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(self._fg(36 * cp))
                    p.drawEllipse(r)
                al = cp * (1.0 if enabled else 0.3)
                c = r.center()
                if name in ("prev", "next", "play"):
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(self._fg(255 * al))
                    self._glyph(p, name, c)
                elif name == "shuffle":
                    col = QColor(acc) if self._shuffle else self._fg(dim)
                    col.setAlpha(int(col.alpha() * al))
                    self._draw_shuffle(p, c, col)
                else:
                    col = QColor(acc) if self._repeat else self._fg(dim)
                    col.setAlpha(int(col.alpha() * al))
                    self._draw_repeat(p, c, col, self._repeat == 1)
        # أيقونة الصوت (تبقى في مكانها وتتحول إلى زر إغلاق للشريط)
        vr = L["volume"]
        if self._hover == "volume":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._fg(36 * a))
            p.drawEllipse(vr)
        self._draw_speaker(p, vr.center(), self._volume, self._muted, self._fg(235 * a))
        if vp > 0.02:                                # شريط الصوت الأفقي
            pa = a * vp
            tr = L["vtrack"]
            v = self._volume if self._volume >= 0 else 0.5
            rr = tr.height() / 2
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._fg(70 * pa))
            p.drawRoundedRect(tr, rr, rr)
            fc = QColor(acc)
            fc.setAlpha(int(255 * pa))
            p.setBrush(fc)
            p.drawRoundedRect(QRectF(tr.left(), tr.top(), max(tr.height(), tr.width() * v), tr.height()), rr, rr)
            p.setBrush(self._fg(255 * pa))
            p.drawEllipse(QPointF(tr.left() + tr.width() * v, tr.center().y()), 6.0, 6.0)
            p.setFont(self._small_font())
            p.setPen(self._fg(230 * pa))
            p.drawText(L["vpct"], Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       "0%" if self._muted else f"{int(round(v * 100))}%")

    def _glyph(self, p, name, c):
        x, y = c.x(), c.y()
        if name == "prev":
            p.drawRoundedRect(QRectF(x - 9, y - 7.5, 3.2, 15), 1.2, 1.2)
            p.drawPolygon(QPolygonF([QPointF(x + 8, y - 8), QPointF(x + 8, y + 8), QPointF(x - 5, y)]))
        elif name == "next":
            p.drawRoundedRect(QRectF(x + 5.8, y - 7.5, 3.2, 15), 1.2, 1.2)
            p.drawPolygon(QPolygonF([QPointF(x - 8, y - 8), QPointF(x - 8, y + 8), QPointF(x + 5, y)]))
        elif self._playing:
            p.drawRoundedRect(QRectF(x - 7, y - 9, 5.2, 18), 1.6, 1.6)
            p.drawRoundedRect(QRectF(x + 1.8, y - 9, 5.2, 18), 1.6, 1.6)
        else:
            p.drawPolygon(QPolygonF([QPointF(x - 6.5, y - 10), QPointF(x - 6.5, y + 10), QPointF(x + 10, y)]))

    @staticmethod
    def _pen(col, w=1.9):
        pen = QPen(col, w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def _draw_shuffle(self, p, c, col):
        x, y = c.x(), c.y()
        p.setPen(self._pen(col))
        p.setBrush(Qt.BrushStyle.NoBrush)
        a = QPainterPath()
        a.moveTo(x - 8, y - 4.5)
        a.cubicTo(x - 1, y - 4.5, x - 1, y + 4.5, x + 5.5, y + 4.5)
        b = QPainterPath()
        b.moveTo(x - 8, y + 4.5)
        b.cubicTo(x - 1, y + 4.5, x - 1, y - 4.5, x + 5.5, y - 4.5)
        p.drawPath(a)
        p.drawPath(b)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawPolygon(QPolygonF([QPointF(x + 9.5, y + 4.5), QPointF(x + 5.5, y + 1.3), QPointF(x + 5.5, y + 7.7)]))
        p.drawPolygon(QPolygonF([QPointF(x + 9.5, y - 4.5), QPointF(x + 5.5, y - 7.7), QPointF(x + 5.5, y - 1.3)]))

    def _draw_repeat(self, p, c, col, one):
        x, y, r = c.x(), c.y(), 6.4
        p.setPen(self._pen(col))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(x - r, y - r, 2 * r, 2 * r), 115 * 16, 305 * 16)
        th = math.radians(60)                         # نهاية القوس
        pt = QPointF(x + r * math.cos(th), y - r * math.sin(th))
        d = QPointF(-math.sin(th), -math.cos(th))
        n = QPointF(-d.y(), d.x())
        tip = QPointF(pt.x() + d.x() * 3.4, pt.y() + d.y() * 3.4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawPolygon(QPolygonF([tip, QPointF(pt.x() + n.x() * 3.3, pt.y() + n.y() * 3.3),
                                 QPointF(pt.x() - n.x() * 3.3, pt.y() - n.y() * 3.3)]))
        if one:
            f = QFont("Segoe UI")
            f.setPointSizeF(6.5)
            f.setBold(True)
            p.setFont(f)
            p.setPen(col)
            p.drawText(QRectF(x - 4, y - 5, 8, 10), Qt.AlignmentFlag.AlignCenter, "1")

    def _draw_speaker(self, p, c, vol, muted, col):
        x, y = c.x() - 3, c.y()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawPolygon(QPolygonF([QPointF(x - 7, y - 3.2), QPointF(x - 3.5, y - 3.2), QPointF(x + 1, y - 7),
                                 QPointF(x + 1, y + 7), QPointF(x - 3.5, y + 3.2), QPointF(x - 7, y + 3.2)]))
        p.setPen(self._pen(col))
        p.setBrush(Qt.BrushStyle.NoBrush)
        v = vol if vol >= 0 else 0.5
        if muted or v <= 0.005:
            p.drawLine(QPointF(x + 4.5, y - 4), QPointF(x + 10.5, y + 4))
            p.drawLine(QPointF(x + 10.5, y - 4), QPointF(x + 4.5, y + 4))
        else:
            level = 1 if v < 0.34 else 2 if v < 0.67 else 3
            for n in range(1, level + 1):
                rr = 3.2 + n * 3.0
                p.drawArc(QRectF(x + 1 - rr, y - rr, 2 * rr, 2 * rr), -45 * 16, 90 * 16)

    # ───────── الصوت ─────────
    def _audio_ok(self):
        return self._peak >= 0

    def _apply_volume(self, v):
        v = clamp(v, 0.0, 1.0)
        self._volume = v
        self._muted = False
        if self._audio_ok():
            self._audio.set_volume(v)
        self.update()

    def _step_volume(self, steps):
        if self._audio_ok():
            base = self._volume if self._volume >= 0 else 0.5
            self._apply_volume(base + steps * 0.04)
        else:                                   # بديل: مفاتيح الوسائط
            for _ in range(int(abs(steps)) * 2 or 2):
                press_media_key(VK_VOLUME_UP if steps > 0 else VK_VOLUME_DOWN)

    def _toggle_mute(self):
        if self._audio_ok():
            self._audio.toggle_mute()
        else:
            press_media_key(VK_VOLUME_MUTE)
        self._show_toast(T("toast_mute"))

    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if dy == 0:
            return
        self._step_volume(dy / 120.0)
        self._show_vol_panel(True, 1800)
        e.accept()

    # ───────── التقديم بالضغط المطوّل على "التالي" ─────────
    def _begin_ff(self):
        if self._press_btn != "next" or not (self._has and self._can_seek and self._duration > 0):
            return
        self._ff_resume = self._playing
        self._ff_pos = self._current_position()
        self._ff = True
        self._ff_t0 = self._ff_last = time.monotonic()
        self._ff_speed = 2
        if self._ff_resume:
            self._worker.command("pause")           # كتم الصوت أثناء التقديم: نوقف التشغيل ونحرّك الوقت فقط
        self._ff_timer.start()
        self._text_changed()

    def _tick_ff(self):
        now = time.monotonic()
        dt = now - self._ff_last
        self._ff_last = now
        self._ff_speed = 3 if now - self._ff_t0 >= FF_BOOST_AFTER else 2
        self._ff_pos = min(self._duration, self._ff_pos + dt * self._ff_speed)
        self.update()

    def _end_ff(self):
        self._ff_timer.stop()
        target = min(self._ff_pos, max(0.0, self._duration - 1.0))
        self._ff = False
        self._pos = target
        self._updated = time.time()
        self._hold_until = time.time() + 1.5
        if self._ff_resume:
            self._playing = True
            self._worker.command("seek_play", self._start + target)
        else:
            self._worker.command("seek", self._start + target)
        self._text_changed()

    # ───────── الماوس ─────────
    def mousePressEvent(self, e):
        pos = e.position()
        if e.button() == Qt.MouseButton.LeftButton:
            corner = self._corner_at(pos)
            if corner:
                self._group.stop()
                self._resizing = True
                self._rs = (corner, e.globalPosition().toPoint(), self.geometry(), self._scale)
                e.accept()
                return
            hit = self._hit(pos)
            if hit == "bar":
                self._group.stop()
                self._seeking = True
                self._seek_frac = self._frac_from_x(pos.x())
                self.update()
            elif hit == "vslider":
                self._vol_drag = True
                self._vol_close.stop()
                self._apply_volume(self._vol_from_x(pos.x()))
            elif hit in ("prev", "play", "next", "shuffle", "repeat", "volume"):
                self._press_btn = hit
                if hit == "next":
                    self._hold_timer.start(HOLD_MS)
            else:
                self._group.stop()
                self._dragging = True
                self._drag_off = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept()
        elif e.button() == Qt.MouseButton.MiddleButton:
            self._toggle_mute()
            e.accept()

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._resizing:
            self._do_resize(e.globalPosition().toPoint())
            return
        if self._seeking:
            self._seek_frac = self._frac_from_x(pos.x())
            self.update()
        elif self._vol_drag:
            self._apply_volume(self._vol_from_x(pos.x()))
        elif self._dragging:
            self.move(e.globalPosition().toPoint() - self._drag_off)
        else:
            corner = self._corner_at(pos)
            if corner:
                diag = corner in (("r", "b"), ("l", "t"))
                self.setCursor(Qt.CursorShape.SizeFDiagCursor if diag else Qt.CursorShape.SizeBDiagCursor)
                if self._hover:
                    self._hover = None
                    self.update()
                return
            hit = self._hit(pos)
            if hit != self._hover:
                self._hover = hit
                self.setCursor(Qt.CursorShape.PointingHandCursor if hit else Qt.CursorShape.ArrowCursor)
                self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pos = e.position()
        if self._resizing:
            self._resizing = False
            self._rs = None
            self._settings.setValue("scale", self._scale)
            self._finish_drag()
        elif self._seeking:
            self._seeking = False
            target = self._frac_from_x(pos.x()) * self._duration
            self._pos = target
            self._updated = time.time()
            self._hold_until = time.time() + 1.3
            self._worker.command("seek", self._start + target)
            self.update()
        elif self._vol_drag:
            self._vol_drag = False
            self._vol_close.start(2500)
        elif self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._finish_drag()
        elif self._press_btn:
            btn, self._press_btn = self._press_btn, None
            self._hold_timer.stop()
            if btn == "next" and self._ff:
                self._end_ff()
            elif self._hit(pos) == btn:
                self._click(btn)

    def _click(self, btn):
        now = time.time()
        if btn == "play":
            self._worker.command("play_pause")
            if self._has:
                self._pos = self._current_position()
                self._updated = now
                self._playing = not self._playing
                self._hold_until = now + 0.8
            self.update()
        elif btn in ("prev", "next"):
            self._worker.command(btn)
        elif btn == "shuffle" and self._has and self._can_shuffle:
            self._shuffle = not self._shuffle
            self._ctl_hold_until = now + 1.5
            self._worker.command("shuffle", self._shuffle)
            self.update()
        elif btn == "repeat" and self._has and self._can_repeat:
            self._repeat = {0: 2, 2: 1, 1: 0}[self._repeat]     # إيقاف ← الكل ← ملف واحد ← إيقاف
            self._ctl_hold_until = now + 1.5
            self._worker.command("repeat", self._repeat)
            self.update()
        elif btn == "volume":
            self._show_vol_panel(not self._vol_panel)

    def _corner_at(self, pos):
        m = 10
        x, y = pos.x(), pos.y()
        hx = "l" if x < m else "r" if x > self.width() - m else None
        vy = "t" if y < m else "b" if y > self.height() - m else None
        return (hx, vy) if hx and vy else None

    def _do_resize(self, gp):
        (hx, vy), start, geo, s0 = self._rs
        dx = (gp.x() - start.x()) * (1 if hx == "r" else -1)
        s = clamp(s0 * max(60, geo.width() + dx) / geo.width(), 0.6, 2.2)
        self._scale = s
        bw, bh = (EXPAND_W, EXPAND_H) if self._expanded else SIZES[self._mode]
        W, H = int(bw * s), int(bh * s)
        x = geo.x() if hx == "r" else geo.right() + 1 - W
        y = geo.y() if vy == "b" else geo.bottom() + 1 - H
        self.setGeometry(x, y, W, H)
        self.update()

    def _finish_drag(self):
        g = self.geometry()
        ag = self._screen_geo(g.center())
        x = clamp(g.x(), ag.left() + 4, max(ag.left() + 4, ag.right() - g.width() - 3))
        y = clamp(g.y(), ag.top(), max(ag.top(), ag.bottom() - g.height()))
        if x != g.x() or y != g.y():
            self.move(int(x), int(y))
        self._anchor_cx = int(x) + g.width() // 2
        self._top = int(y)
        self._save_position()

    # ───────── قائمة الكليك يمين ─────────
    def contextMenuEvent(self, e):
        menu = make_menu(self)
        act_set = menu.addAction(T("menu_settings"))
        add_theme_menu(menu, self)
        act_pin = menu.addAction(T("menu_pin"))
        act_pin.setCheckable(True)
        act_pin.setChecked(self._pinned)
        act_reset = menu.addAction(T("menu_reset"))
        act_hide = menu.addAction(T("menu_hide"))
        menu.addSeparator()
        act_close = menu.addAction(T("menu_close"))

        self._menu_open = True
        chosen = menu.exec(e.globalPos())
        self._menu_open = False
        if chosen is act_set:
            self.open_settings()
        elif chosen is act_pin:
            self._pinned = act_pin.isChecked()
            self._settings.setValue("pinned", self._pinned)
            self._set_expanded(True if self._pinned else self.frameGeometry().contains(QCursor.pos()), force=True)
        elif chosen is act_reset:
            self._reset_position()
        elif chosen is act_hide:
            self.hide()
        elif chosen is act_close:
            QApplication.quit()

    def notify_dialog(self):
        if self._dlg is not None and self._dlg.isVisible():
            self._dlg.sync_from_store()

    def closeEvent(self, e):
        self._save_position()
        super().closeEvent(e)


def make_menu(parent=None):
    menu = QMenu(parent)
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint
                        | Qt.WindowType.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft if LANG == "ar" else Qt.LayoutDirection.LeftToRight)
    menu.setStyleSheet("""
        QMenu { background-color: rgba(24,25,31,238); color: #f2f2f6;
                border: 1px solid rgba(255,255,255,46); border-radius: 14px; padding: 6px;
                font-family: 'Segoe UI'; font-size: 13px; }
        QMenu::item { padding: 8px 24px 8px 26px; border-radius: 9px; }
        QMenu::item:selected { background-color: rgba(255,255,255,30); }
        QMenu::separator { height: 1px; background: rgba(255,255,255,32); margin: 5px 8px; }
    """)
    return menu


def add_theme_menu(menu, bubble):
    sub = menu.addMenu(T("menu_themes"))
    sub.setLayoutDirection(menu.layoutDirection())
    first_slot = True
    for key in bubble.store.keys():
        if key.startswith("slot:") and first_slot:
            sub.addSeparator()
            first_slot = False
        act = sub.addAction(slot_label(key))
        act.setCheckable(True)
        act.setChecked(key == bubble.store.active)
        act.triggered.connect(lambda _=False, k=key: (bubble.activate_theme(k), bubble.notify_dialog()))
    return sub


# ═════════════════════════════ نافذة الإعدادات ═════════════════════════════
class ColorButton(QPushButton):
    changed = pyqtSignal()

    def __init__(self, color="#ffffff", parent=None):
        super().__init__(parent)
        self._c = color
        self.clicked.connect(self._pick)
        self._paint()

    def color(self):
        return self._c

    def set_color(self, c):
        self._c = c or "#ffffff"
        self._paint()

    def _paint(self):
        fg = "#000" if QColor(self._c).lightness() > 128 else "#fff"
        self.setText(self._c)
        self.setStyleSheet(f"background:{self._c}; color:{fg}; padding:5px 10px; "
                           "border:1px solid #888; border-radius:6px;")

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._c), self.window(), T("pick_color"))
        if c.isValid():
            self._c = c.name()
            self._paint()
            self.changed.emit()


class SettingsDialog(QDialog):
    """كل تغيير يُطبَّق فوراً ويُحفظ تلقائياً في الثيم النشط (أو في آخر خانة مخصصة)."""

    def __init__(self, bubble):
        super().__init__(None)
        self.b = bubble
        self._loading = True
        self.setWindowTitle(T("set_title"))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if LANG == "ar" else Qt.LayoutDirection.LeftToRight)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(460)
        tabs = QTabWidget()
        root = QVBoxLayout(self)
        root.addWidget(tabs)

        # ── عام ──
        g = QWidget()
        gf = QFormLayout(g)
        self.cb_lang = QComboBox()
        self.cb_lang.addItem("English", "en")
        self.cb_lang.addItem("العربية", "ar")
        self.cb_lang.setCurrentIndex(max(0, self.cb_lang.findData(LANG)))
        self.cb_mode = QComboBox()
        self.cb_mode.addItem(T("layout_mini"), "mini")
        self.cb_mode.addItem(T("layout_normal"), "normal")
        self.cb_mode.setCurrentIndex(max(0, self.cb_mode.findData(bubble._mode)))
        self.s_size = self._slider(60, 220, int(round(bubble._scale * 100)))
        self.chk_24 = QCheckBox(T("clock24"))
        self.chk_24.setChecked(bubble._clock24)
        self.chk_start = QCheckBox(T("autostart"))
        self.chk_start.setChecked(autostart_enabled())
        gf.addRow(T("language"), self.cb_lang)
        gf.addRow(T("layout"), self.cb_mode)
        gf.addRow(T("size"), self.s_size)
        gf.addRow("", self.chk_24)
        gf.addRow("", self.chk_start)
        tabs.addTab(g, T("tab_general"))

        # ── المظهر ──
        l = QWidget()
        lf = QFormLayout(l)
        self.cb_theme = QComboBox()
        for key in bubble.store.keys():
            self.cb_theme.addItem(slot_label(key), key)
        self.cb_blur = QComboBox()
        for label, key in ((T("blur_off"), "off"), (T("blur_blur"), "blur"), (T("blur_acrylic"), "acrylic")):
            self.cb_blur.addItem(label, key)
        self.s_opacity = self._slider(5, 100, 55)
        self.s_bright = self._slider(-50, 50, 0)
        self.s_radius = self._slider(6, 30, 18)
        self.s_soft = self._slider(0, 100, 10)
        self.btn_tint = ColorButton()
        self.btn_text = ColorButton()
        self.btn_accent = ColorButton("#7cacff")
        self.chk_auto = QCheckBox(T("accent_auto"))
        btn_reset = QPushButton(T("reset_slot"))
        lf.addRow(T("theme"), self.cb_theme)
        lf.addRow(T("blur"), self.cb_blur)
        lf.addRow(T("opacity"), self.s_opacity)
        lf.addRow(T("brightness"), self.s_bright)
        lf.addRow(T("radius"), self.s_radius)
        lf.addRow(T("tint"), self.btn_tint)
        lf.addRow(T("text_color"), self.btn_text)
        lf.addRow(T("accent"), self.btn_accent)
        lf.addRow("", self.chk_auto)
        lf.addRow("", btn_reset)
        tabs.addTab(l, T("tab_look"))

        # ── ألوان المناطق ──
        r = QWidget()
        rf = QFormLayout(r)
        hint = QLabel(T("region_hint"))
        hint.setWordWrap(True)
        rf.addRow(hint)
        self.zones = {}
        for side in ("top", "bottom", "left", "right"):
            chk, btn = QCheckBox(), ColorButton()
            row = QHBoxLayout()
            row.addWidget(chk)
            row.addWidget(btn, 1)
            self.zones[side] = (chk, btn)
            rf.addRow(T("region_" + side), row)
            chk.toggled.connect(self._changed)
            btn.changed.connect(self._changed)
        rf.addRow(T("softness"), self.s_soft)
        self.btn_mini = ColorButton("#000000")
        self.btn_mini_text = ColorButton("#ffffff")
        rf.addRow(T("mini_color"), self.btn_mini)
        rf.addRow(T("mini_text"), self.btn_mini_text)
        tabs.addTab(r, T("tab_regions"))

        # ── الربط ──
        self.cb_lang.currentIndexChanged.connect(self._lang_changed)
        self.cb_mode.currentIndexChanged.connect(lambda *_: None if self._loading else
                                                 self.b.set_mode(self.cb_mode.currentData()))
        self.s_size.valueChanged.connect(lambda v: None if self._loading else self.b.set_scale(v / 100.0))
        self.chk_24.toggled.connect(lambda f: None if self._loading else self.b.set_clock24(f))
        self.chk_start.toggled.connect(lambda f: None if self._loading else set_autostart(f))
        self.cb_theme.currentIndexChanged.connect(self._theme_selected)
        self.cb_blur.currentIndexChanged.connect(self._changed)
        for s in (self.s_opacity, self.s_bright, self.s_radius, self.s_soft):
            s.valueChanged.connect(self._changed)
        for btn in (self.btn_tint, self.btn_text, self.btn_accent, self.btn_mini, self.btn_mini_text):
            btn.changed.connect(self._changed)
        self.chk_auto.toggled.connect(self._changed)
        btn_reset.clicked.connect(self._reset)

        self.sync_from_store()

    @staticmethod
    def _slider(lo, hi, val):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(int(val))
        return s

    def _load_look(self, look):
        self._loading = True
        self.cb_blur.setCurrentIndex(max(0, self.cb_blur.findData(look["blur"])))
        self.s_opacity.setValue(int(look["opacity"]))
        self.s_bright.setValue(int(look["brightness"]))
        self.s_radius.setValue(int(look["radius"]))
        self.s_soft.setValue(int(look["softness"]))
        self.btn_tint.set_color(look["tint"])
        self.btn_text.set_color(look["text"])
        auto = look["accent"] == "auto"
        self.chk_auto.setChecked(auto)
        self.btn_accent.set_color("#7cacff" if auto else look["accent"])
        for side, (chk, btn) in self.zones.items():
            c = look.get("zone_" + side)
            chk.setChecked(bool(c))
            btn.set_color(c or "#7cacff")
        self.btn_mini.set_color(look["mini_color"])
        self.btn_mini_text.set_color(look["mini_text"])
        self._loading = False

    def sync_from_store(self):
        self._loading = True
        self.cb_theme.setCurrentIndex(max(0, self.cb_theme.findData(self.b.store.active)))
        self._loading = False
        self._load_look(self.b.store.look())

    def _collect(self):
        look = {
            "tint": self.btn_tint.color(), "text": self.btn_text.color(),
            "opacity": self.s_opacity.value(), "brightness": self.s_bright.value(),
            "radius": self.s_radius.value(), "blur": self.cb_blur.currentData(),
            "accent": "auto" if self.chk_auto.isChecked() else self.btn_accent.color(),
            "softness": self.s_soft.value(),
            "mini_color": self.btn_mini.color(), "mini_text": self.btn_mini_text.color(),
        }
        for side, (chk, btn) in self.zones.items():
            look["zone_" + side] = btn.color() if chk.isChecked() else None
        return look

    def _changed(self, *_):
        if self._loading:
            return
        key = self.b.update_look(self._collect())      # أي تعديل على ثيم جاهز يُنسخ إلى خانة مخصصة
        self._loading = True
        self.cb_theme.setCurrentIndex(max(0, self.cb_theme.findData(key)))
        self._loading = False

    def _theme_selected(self, *_):
        if self._loading:
            return
        look = self.b.activate_theme(self.cb_theme.currentData())
        self._load_look(look)

    def _reset(self):
        self._load_look(self.b.reset_theme())

    def _lang_changed(self, *_):
        if self._loading:
            return
        self.b.set_language(self.cb_lang.currentData())
        QTimer.singleShot(0, self.b.reopen_settings)


# ═════════════════════════════ نقطة الدخول ═════════════════════════════
def main():
    global LANG
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    _mutex = k32.CreateMutexW(None, False, "Local\\SoundWidgetOverlayMutex")   # noqa: F841 (يبقى حياً)
    if ctypes.get_last_error() == 183:                        # ERROR_ALREADY_EXISTS: نسخة واحدة فقط
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(make_app_icon())
    app.setQuitOnLastWindowClosed(False)

    settings = QSettings(ORG_NAME, "Overlay")
    LANG = settings.value("lang", "", type=str) or detect_language()
    if LANG not in STR:
        LANG = "en"
    store = ThemeStore(settings)

    worker = MediaWorker()
    audio = AudioWorker()
    bubble = IslandBubble(worker, audio, store, settings)
    worker.state_changed.connect(bubble.on_state, Qt.ConnectionType.QueuedConnection)
    audio.levels.connect(bubble.on_levels, Qt.ConnectionType.QueuedConnection)
    app.aboutToQuit.connect(worker.shutdown)
    app.aboutToQuit.connect(audio.shutdown)

    worker.start()
    audio.start()
    bubble.show()

    # أيقونة شريط المهام (عند السهم)
    tray = QSystemTrayIcon(make_app_icon(), app)
    tray.setToolTip(APP_NAME)
    tray_menu = make_menu()

    def rebuild_tray_menu():
        tray_menu.clear()
        tray_menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft if LANG == "ar"
                                     else Qt.LayoutDirection.LeftToRight)
        tray_menu.addAction(T("tray_toggle")).triggered.connect(bubble.toggle_visible)
        tray_menu.addAction(T("menu_settings")).triggered.connect(bubble.open_settings)
        add_theme_menu(tray_menu, bubble)
        tray_menu.addAction(T("menu_reset")).triggered.connect(bubble._reset_position)
        tray_menu.addSeparator()
        tray_menu.addAction(T("menu_close")).triggered.connect(app.quit)

    tray_menu.aboutToShow.connect(rebuild_tray_menu)
    rebuild_tray_menu()
    tray.setContextMenu(tray_menu)
    tray.activated.connect(lambda reason: bubble.toggle_visible()
                           if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
