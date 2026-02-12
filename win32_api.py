"""Win32 API: 截屏、按键注入、窗口操作。"""
import io
import time
import hashlib
import ctypes
import ctypes.wintypes
import logging

from PIL import Image

logger = logging.getLogger("bedcode")

# ── Win32 常量 ────────────────────────────────────────────────────
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
PW_RENDERFULLCONTENT = 0x00000002
BI_RGB = 0
DIB_RGB_COLORS = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D
VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_BACK = 0x08
VK_SPACE = 0x20


# ── Win32 结构体 ──────────────────────────────────────────────────
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.wintypes.DWORD),
        ("biWidth", ctypes.wintypes.LONG),
        ("biHeight", ctypes.wintypes.LONG),
        ("biPlanes", ctypes.wintypes.WORD),
        ("biBitCount", ctypes.wintypes.WORD),
        ("biCompression", ctypes.wintypes.DWORD),
        ("biSizeImage", ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed", ctypes.wintypes.DWORD),
        ("biClrImportant", ctypes.wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", ctypes.wintypes.DWORD * 3),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


# ── 截屏 ─────────────────────────────────────────────────────────
def capture_window_screenshot(handle: int) -> bytes | None:
    """使用 PrintWindow API 截屏 — 不需要激活窗口，不打断思考。"""
    try:
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(handle, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width <= 0 or height <= 0:
            return None

        wnd_dc = user32.GetWindowDC(handle)
        if not wnd_dc:
            return None

        try:
            mem_dc = gdi32.CreateCompatibleDC(wnd_dc)
            bitmap = gdi32.CreateCompatibleBitmap(wnd_dc, width, height)
            old_bmp = gdi32.SelectObject(mem_dc, bitmap)

            result = user32.PrintWindow(handle, mem_dc, PW_RENDERFULLCONTENT)
            if not result:
                result = user32.PrintWindow(handle, mem_dc, 0)

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = BI_RGB

            buf_size = width * height * 4
            buf = ctypes.create_string_buffer(buf_size)
            gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), DIB_RGB_COLORS)

            gdi32.SelectObject(mem_dc, old_bmp)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)

            img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)
            img = img.convert("RGB")

            max_w = 1280
            if img.width > max_w:
                ratio = max_w / img.width
                img = img.resize((max_w, int(img.height * ratio)))

            out = io.BytesIO()
            img.save(out, format="JPEG", quality=75)
            out.seek(0)
            return out.getvalue()
        finally:
            user32.ReleaseDC(handle, wnd_dc)
    except Exception as e:
        logger.exception(f"截屏失败: {e}")
        return None


def _image_hash(img_bytes: bytes) -> str:
    return hashlib.md5(img_bytes).hexdigest()


# ── 窗口标题 ─────────────────────────────────────────────────────
def get_window_title(handle: int) -> str:
    """获取窗口标题 — 不需要激活窗口。"""
    try:
        length = user32.GetWindowTextLengthW(handle)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buf, length + 1)
        return buf.value
    except Exception:
        return ""


def get_foreground_window() -> int:
    return user32.GetForegroundWindow()


# ── 按键注入 ─────────────────────────────────────────────────────
def _make_key_input(vk: int = 0, scan: int = 0, flags: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    return inp


def _send_vk(vk: int) -> None:
    inputs = (INPUT * 2)(
        _make_key_input(vk=vk),
        _make_key_input(vk=vk, flags=KEYEVENTF_KEYUP),
    )
    user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def _send_unicode_char(char: str) -> None:
    code = ord(char)
    inputs = (INPUT * 2)(
        _make_key_input(scan=code, flags=KEYEVENTF_UNICODE),
        _make_key_input(scan=code, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
    )
    user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def _activate_window(handle: int) -> bool:
    try:
        user32.SetForegroundWindow(handle)
    except Exception:
        pass
    time.sleep(0.3)
    fg = user32.GetForegroundWindow()
    if fg != handle:
        try:
            user32.SetForegroundWindow(handle)
        except Exception:
            pass
        time.sleep(0.3)
        fg = user32.GetForegroundWindow()
    return fg == handle


def send_keys_to_window(handle: int, text: str) -> bool:
    """向窗口发送文本 + 回车。优先 pywinauto，失败回退剪贴板粘贴。"""
    if not _activate_window(handle):
        logger.warning(f"无法激活窗口 {handle}，但仍尝试发送")

    try:
        from pywinauto import Application as PwaApp
        app = PwaApp(backend="uia").connect(handle=handle)
        win = app.window(handle=handle)

        safe = text.replace("{", "{{").replace("}", "}}")
        safe = safe.replace("+", "{+}").replace("^", "{^}")
        safe = safe.replace("%", "{%}").replace("~", "{~}")

        win.type_keys(safe, with_spaces=True, with_tabs=True, pause=0.02)
        time.sleep(0.2)
        _activate_window(handle)
        try:
            win.type_keys("{ENTER}")
        except Exception:
            pass
        time.sleep(0.1)
        _send_vk(VK_RETURN)
        logger.info(f"注入成功(pywinauto): {text[:50]}")
        return True
    except Exception as e:
        logger.warning(f"pywinauto失败: {e}, 回退剪贴板粘贴")

    try:
        import subprocess as _sp
        _sp.run(["clip.exe"], input=text.encode("utf-16le"), check=True,
                creationflags=0x08000000)
        time.sleep(0.3)
        if not _activate_window(handle):
            logger.warning(f"无法激活窗口 {handle}，但仍尝试粘贴")
        VK_CONTROL = 0x11
        VK_V = 0x56
        inputs = (INPUT * 4)(
            _make_key_input(vk=VK_CONTROL),
            _make_key_input(vk=VK_V),
            _make_key_input(vk=VK_V, flags=KEYEVENTF_KEYUP),
            _make_key_input(vk=VK_CONTROL, flags=KEYEVENTF_KEYUP),
        )
        user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        time.sleep(0.3)
        _send_vk(VK_RETURN)
        logger.info(f"注入成功(剪贴板): {text[:50]}")
        return True
    except Exception as e2:
        logger.exception(f"剪贴板粘贴也失败: {e2}")
        return False


VK_MAP = {
    "上": VK_UP, "up": VK_UP, "↑": VK_UP,
    "下": VK_DOWN, "down": VK_DOWN, "↓": VK_DOWN,
    "左": VK_LEFT, "left": VK_LEFT, "←": VK_LEFT,
    "右": VK_RIGHT, "right": VK_RIGHT, "→": VK_RIGHT,
    "回车": VK_RETURN, "enter": VK_RETURN,
    "tab": VK_TAB,
    "退格": VK_BACK, "backspace": VK_BACK,
    "esc": VK_ESCAPE, "取消": VK_ESCAPE,
    "空格": VK_SPACE, "space": VK_SPACE,
}


def send_raw_keys(handle: int, key_parts: list[str]) -> bool:
    try:
        if not _activate_window(handle):
            logger.warning(f"无法激活窗口 {handle}，但仍尝试发送")
        for p in key_parts:
            p_lower = p.lower()
            if p_lower in VK_MAP:
                _send_vk(VK_MAP[p_lower])
            elif len(p) == 1:
                _send_unicode_char(p)
            else:
                for ch in p:
                    _send_unicode_char(ch)
            time.sleep(0.05)
        logger.info(f"按键发送: {' '.join(key_parts)}")
        return True
    except Exception as e:
        logger.exception(f"按键发送失败: {e}")
        return False
