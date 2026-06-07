"""
whatsapp_service.py
Lógica de compartir por WhatsApp.
Intenta abrir la app de escritorio primero (whatsapp://).
Si no está instalada, abre WhatsApp Web como fallback.
"""
import io
import os
import subprocess
import webbrowser
from pathlib import Path
import logging
log = logging.getLogger("mvp10")
from PIL import Image

try:
    import win32clipboard
    import win32con
    _WIN32 = True
except ImportError:
    _WIN32 = False

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False


WHATSAPP_WEB_URL = "https://web.whatsapp.com"


def copy_image_to_clipboard(image_path: Path):
    """Copia la imagen al portapapeles (Windows). No-op en otras plataformas."""
    if not _WIN32:
        return
    with Image.open(image_path) as img:
        output = io.BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()


def open_whatsapp_desktop() -> bool:
    """
    Intenta abrir la app de escritorio de WhatsApp usando el protocolo whatsapp://.
    Retorna True si el sistema reconoció el protocolo, False si no.
    """
    try:
        if os.name == "nt":
            # En Windows usamos ShellExecute para el protocolo URI
            import ctypes
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "open", "whatsapp://", None, None, 1
            )
            log.debug(f"ShellExecute whatsapp:// result code: {result}")
            # ShellExecute retorna > 32 si tuvo éxito
            return int(result) > 32
        else:
            # macOS / Linux
            subprocess.Popen(["xdg-open", "whatsapp://"])
            return True
    except Exception:
        return False


def open_whatsapp_web():
    """Abre WhatsApp Web en el navegador predeterminado."""
    webbrowser.open(WHATSAPP_WEB_URL)


def paste_clipboard_image():
    """Intenta pegar el portapapeles con Ctrl+V en la ventana activa."""
    if not _PYAUTOGUI:
        return
    import time
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.4)
    pyautogui.press("enter")


def share_invoice(image_path: Path) -> dict:
    """
    Flujo completo:
    1. Copia la imagen al portapapeles
    2. Intenta abrir la app de escritorio de WhatsApp
    3. Si no está instalada, abre WhatsApp Web
    Retorna un dict con 'desktop_opened' (bool) y 'error' (str|None).
    """
    error = None
    desktop_opened = False
    try:
        copy_image_to_clipboard(image_path)
    except Exception as e:
        error = str(e)

    try:
        desktop_opened = open_whatsapp_desktop()
        if not desktop_opened:
            open_whatsapp_web()
    except Exception as e:
        error = str(e)
        open_whatsapp_web()

    return {"desktop_opened": desktop_opened, "error": error}

# Añade esto al final de services/whatsapp_service.py

def show_floating_paste_button():
    import tkinter as tk
    import threading
    import time

    def run_tk():
        def on_click():
            root.destroy()
            time.sleep(0.4)
            try:
                pyautogui.hotkey("ctrl", "v")
            except Exception as e:
                print("Error en pyautogui:", e)

        def on_close():
            root.destroy()

        root = tk.Tk()
        root.title("")
        root.attributes("-topmost", True)
        root.overrideredirect(True)

        # Colores
        BG       = "#ffffff"
        ACCENT   = "#1565C0"   # azul de la app
        ACCENT_H = "#0D47A1"
        TEXT     = "#111827"
        SUBTLE   = "#6B7280"
        BORDER   = "#E5E7EB"

        root.configure(bg=BORDER)  # borde exterior via bg + highlightthickness

        w, h = 280, 130
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x  = sw - w - 24
        y  = sh - h - 64
        root.geometry(f"{w}x{h}+{x}+{y}")

        # Marco interior blanco
        frame_outer = tk.Frame(root, bg=BG, padx=0, pady=0)
        frame_outer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Franja de color arriba (accent bar)
        accent_bar = tk.Frame(frame_outer, bg=ACCENT, height=4)
        accent_bar.pack(fill=tk.X)

        # Contenido
        inner = tk.Frame(frame_outer, bg=BG, padx=16, pady=12)
        inner.pack(fill=tk.BOTH, expand=True)

        # Título + botón cerrar
        top_row = tk.Frame(inner, bg=BG)
        top_row.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            top_row, text="Listo para pegar",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(side=tk.LEFT)

        btn_x = tk.Button(
            top_row, text="✕", command=on_close,
            bg=BG, fg=SUBTLE,
            font=("Segoe UI", 9),
            relief=tk.FLAT, cursor="hand2",
            bd=0, padx=4,
        )
        btn_x.pack(side=tk.RIGHT)

        tk.Label(
            inner,
            text="Abrí WhatsApp, elegí el contacto\ny presioná el botón.",
            bg=BG, fg=SUBTLE,
            font=("Segoe UI", 9),
            justify=tk.LEFT, anchor="w",
        ).pack(fill=tk.X, pady=(0, 10))

        # Botón principal
        btn = tk.Button(
            inner,
            text="  Pegar imagen  ↵",
            command=on_click,
            bg=ACCENT, fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, cursor="hand2",
            activebackground=ACCENT_H,
            activeforeground="white",
            bd=0, pady=7,
        )
        btn.pack(fill=tk.X)

        root.mainloop()

    threading.Thread(target=run_tk, daemon=True).start()