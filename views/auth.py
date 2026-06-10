"""Login y Register dialogs — Flet 0.28.3"""

import json
import os
from pathlib import Path

import flet as ft
from theme import get_theme
from services.auth_service import AuthService


_REMEMBER_FILE = Path(os.getenv("APPDATA")) / "MVP 1.0" / "remember.json"


def _save_remembered(nombre: str):
    _REMEMBER_FILE.parent.mkdir(parents=True, exist_ok=True)
    _REMEMBER_FILE.write_text(json.dumps({"nombre": nombre}), encoding="utf-8")


def _load_remembered() -> str:
    try:
        return json.loads(_REMEMBER_FILE.read_text(encoding="utf-8")).get("nombre", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def _clear_remembered():
    _REMEMBER_FILE.unlink(missing_ok=True)


def _base_tf(t: dict, hint: str, **kwargs) -> ft.TextField:
    return ft.TextField(
        hint_text=hint,
        border_radius=7,
        height=38,
        text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        bgcolor=t["bg_input"],
        border_color=t["border"],
        focused_border_color=t["accent"],
        color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
        **kwargs,
    )


def LoginDialog(page: ft.Page, on_success=None) -> ft.AlertDialog:
    t = get_theme(page)
    auth = AuthService()
    error_text = ft.Text("", size=12, color=ft.Colors.RED_400)

    tf_nombre = _base_tf(t, "Nombre", width=260)
    tf_pin = _base_tf(
        t,
        "PIN (4 números)",
        password=True,
        max_length=4,
        keyboard_type=ft.KeyboardType.NUMBER,
        width=260,
    )
    cb_recordar = ft.Checkbox(
        label="Recordar usuario",
        value=False,
        check_color=t["accent"],
        label_style=ft.TextStyle(size=12, color=t["text_secondary"]),
    )

    remembered = _load_remembered()
    if remembered:
        tf_nombre.value = remembered
        cb_recordar.value = True

    def _do_login(e):
        error_text.value = ""
        print(f"[LoginDialog] _do_login — nombre='{tf_nombre.value}' pin='{'*'*len(tf_pin.value or '')}'")
        u = auth.login(tf_nombre.value or "", tf_pin.value or "")
        print(f"[LoginDialog] auth.login retornó: {u}")
        if u:
            print(f"[LoginDialog] Login exitoso, cerrando diálogo...")
            if cb_recordar.value:
                _save_remembered(tf_nombre.value.strip())
            else:
                _clear_remembered()
            page.close(dlg)
            if on_success:
                print(f"[LoginDialog] Llamando on_success...")
                on_success()
        else:
            print(f"[LoginDialog] Login falló")
            error_text.value = "Usuario o PIN incorrecto. ¿Querés registrarte?"
            page.update()

    def _go_register(e):
        page.close(dlg)
        page.open(RegisterDialog(page, on_success=on_success))

    tf_pin.on_submit = _do_login

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=t["bg_card"],
        title=ft.Text("Iniciar sesión", size=16, weight=ft.FontWeight.W_500),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Tu nombre", size=12, color=t["text_secondary"]),
                    tf_nombre,
                    ft.Text("PIN", size=12, color=t["text_secondary"]),
                    tf_pin,
                    cb_recordar,
                    error_text,
                ],
                spacing=6,
                tight=True,
            ),
            width=300,
        ),
        actions=[
            ft.TextButton("Registrarse", on_click=_go_register),
            ft.ElevatedButton(
                "Ingresar",
                icon=ft.Icons.LOGIN,
                bgcolor=t["accent"],
                color=t["accent_text"],
                on_click=_do_login,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def RegisterDialog(page: ft.Page, on_success=None) -> ft.AlertDialog:
    t = get_theme(page)
    auth = AuthService()
    error_text = ft.Text("", size=12, color=ft.Colors.RED_400)
    ok_text = ft.Text("", size=12, color=ft.Colors.GREEN_400)

    tf_nombre = _base_tf(t, "Nombre (mínimo 2 caracteres)", width=260)
    tf_pin = _base_tf(
        t,
        "PIN (4 números)",
        password=True,
        max_length=4,
        keyboard_type=ft.KeyboardType.NUMBER,
        width=260,
    )
    tf_pin_confirm = _base_tf(
        t,
        "Confirmar PIN",
        password=True,
        max_length=4,
        keyboard_type=ft.KeyboardType.NUMBER,
        width=260,
    )

    def _do_register(e):
        error_text.value = ""
        ok_text.value = ""
        pin = (tf_pin.value or "").strip()
        pin2 = (tf_pin_confirm.value or "").strip()
        if pin != pin2:
            error_text.value = "Los PINes no coinciden."
            page.update()
            return
        ok, msg = auth.register(tf_nombre.value or "", pin)
        if ok:
            auth.login(tf_nombre.value or "", pin)
            page.close(dlg)
            if on_success:
                on_success()
        else:
            error_text.value = msg
            page.update()

    def _go_login(e):
        page.close(dlg)
        page.open(LoginDialog(page, on_success=on_success))

    tf_pin_confirm.on_submit = _do_register

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=t["bg_card"],
        title=ft.Text("Registrarse", size=16, weight=ft.FontWeight.W_500),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Tu nombre", size=12, color=t["text_secondary"]),
                    tf_nombre,
                    ft.Text("PIN (4 números)", size=12, color=t["text_secondary"]),
                    tf_pin,
                    ft.Text("Confirmar PIN", size=12, color=t["text_secondary"]),
                    tf_pin_confirm,
                    error_text,
                    ok_text,
                ],
                spacing=6,
                tight=True,
            ),
            width=300,
        ),
        actions=[
            ft.TextButton("Ya tengo cuenta", on_click=_go_login),
            ft.ElevatedButton(
                "Crear cuenta",
                icon=ft.Icons.PERSON_ADD,
                bgcolor=t["accent"],
                color=t["accent_text"],
                on_click=_do_register,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg
