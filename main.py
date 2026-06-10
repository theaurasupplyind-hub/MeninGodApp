import traceback
import logging
from pathlib import Path

# ── Logging de debug ──────────────────────────────────────────────────────────
import os
_log_path = Path(os.getenv("APPDATA")) / "MVP 1.0" / "mvp10_debug.log"
_log_path.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(_log_path),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)
log = logging.getLogger("mvp10")
log.info("=== Demo 1 iniciando ===")


import flet as ft

from theme import get_theme
from db.database import init_db, get_usuarios
from views.dashboard import DashboardView
from views.facturacion import FacturacionView
from views.clientes import ClientesView
from views.productos import ProductosView
from views.stock_alert import StockAlertBell
from views.cuenta_wasi import CuentaWasiView
from views.auth import LoginDialog, RegisterDialog
from services.auth_service import AuthService

TABS = [
    ("Dashboard",        ft.Icons.DASHBOARD_OUTLINED,       ft.Icons.DASHBOARD),
    ("Facturacion",      ft.Icons.RECEIPT_LONG_OUTLINED,    ft.Icons.RECEIPT_LONG),
    ("Clientes",         ft.Icons.PEOPLE_OUTLINED,          ft.Icons.PEOPLE),
    ("Productos",        ft.Icons.INVENTORY_2_OUTLINED,     ft.Icons.INVENTORY_2),
    ("Cuenta",      ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, ft.Icons.ACCOUNT_BALANCE_WALLET),
]

TITLE_BAR_HEIGHT = 36
STEPS_TOTAL = 6


def main(page: ft.Page):
    page.title = "MVP 1.0"
    page.window.maximized = True
    page.window.min_width = 980
    page.window.min_height = 620
    page.window.icon = "icon.ico"
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = True
    page.padding = 0

    init_db()

    page.theme_mode = ft.ThemeMode.DARK
    t = get_theme(page)
    page.bgcolor = t["bg_page"]
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.AMBER_700,
        use_material3=True,
        navigation_rail_theme=ft.NavigationRailTheme(
            indicator_color=t["accent"],
        ),
    )
    page.dark_theme = ft.Theme(
        color_scheme_seed=ft.Colors.AMBER_700,
        use_material3=True,
    )

    auth = AuthService()

    # ── Loading overlay controls ──────────────────────────────────────────────
    load_bar = ft.ProgressBar(
        width=320, height=6,
        color=t["accent"],
        bgcolor=t["bg_input"],
        value=0,
    )
    load_status = ft.Text("Cargando...", size=14, color=t["text_secondary"])

    overlay = ft.Container(
        content=ft.Column(
            [
                ft.Image(src="logo.svg", width=100, height=100),
                load_status,
                load_bar,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
            spacing=16,
        ),
        alignment=ft.alignment.center,
        bgcolor=t["bg_page"],
        expand=True,
    )

    def _load_step(pct: float, msg: str):
        load_bar.value = pct
        load_status.value = msg
        page.update()

    # ── Main app UI (built flat in main()) ────────────────────────────────────
    content_area = ft.Container(expand=True)
    _views: dict[int, ft.Control] = {}
    current_tab = {"idx": 0}

    bell = StockAlertBell(page, on_go_stock=lambda: _switch(3))

    def _error_view(title: str, error: Exception) -> ft.Control:
        detail = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        print("\n=== DEMO1 DEBUG ERROR ===")
        print(detail)
        log.error(f"VIEW ERROR — {title}:\n{detail}")
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=22, weight=ft.FontWeight.W_600, color=ft.Colors.RED_700),
                    ft.Text(
                        "La pantalla falló al renderizar.",
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Container(
                        content=ft.Text(detail, selectable=True, size=12, color=ft.Colors.ON_SURFACE),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        padding=16,
                        border_radius=8,
                    ),
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=24,
            expand=True,
        )

    def _invalidate_view(idx: int):
        _views.pop(idx, None)

    def _refresh_dashboard():
        _invalidate_view(0)
        if current_tab["idx"] == 0:
            content_area.content = _get_view(0)
        if 3 in _views:
            try:
                _views[3].refresh_data()
            except Exception:
                pass
        page.update()

    def _build_view(idx: int) -> ft.Control:
        log.debug(f"_build_view({idx})")
        if idx == 0:
            return DashboardView(
                page,
                on_nueva_factura=lambda e: _switch(1),
                on_refresh=lambda e: _refresh_dashboard(),
                on_switch_tab=_switch,
                on_toggle_fullscreen=_toggle_fullscreen,
            )
        if idx == 1:
            return FacturacionView(
                page,
                on_factura_guardada=_refresh_dashboard,
                on_switch_tab=_switch,
            )
        if idx == 2:
            return ClientesView(page, get_theme(page), on_switch_tab=_switch)
        if idx == 3:
            return ProductosView(page, on_switch_tab=_switch)
        if idx == 4:
            return CuentaWasiView(page, get_theme(page), on_switch_tab=_switch)
        raise ValueError(f"Tab no soportada: {idx}")

    def _get_view(idx: int) -> ft.Control:
        if idx == 0:
            _invalidate_view(0)
        if idx not in _views:
            try:
                _views[idx] = _build_view(idx)
            except Exception as error:
                _views[idx] = _error_view(f"Error al abrir {TABS[idx][0]}", error)
        return _views[idx]

    def _switch(idx: int):
        try:
            current_tab["idx"] = idx
            if rail_ref["c"]:
                rail_ref["c"].selected_index = idx
            current_view = _get_view(idx)
            content_area.content = current_view
            if hasattr(current_view, "refresh_data"):
                current_view.refresh_data()
            bell.refresh()
            page.update()
        except Exception as error:
            content_area.content = _error_view("Error al cambiar de pantalla", error)
            page.update()

    def _page_error(e):
        log.error(f"PAGE ERROR: {e.data}")
        print("\n=== DEMO1 PAGE ERROR ===")
        print(e.data)
        content_area.content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Error de la aplicacion", size=22, weight=ft.FontWeight.W_600, color=ft.Colors.RED_700),
                    ft.Text(str(e.data), selectable=True),
                ],
                spacing=12,
                expand=True,
            ),
            padding=24,
            expand=True,
        )
        page.update()

    page.on_error = _page_error

    # ── Profile / sidebar ─────────────────────────────────────────────────────
    user_dot = ft.Container(width=8, height=8, bgcolor=ft.Colors.GREEN_400, border_radius=4)
    user_name = ft.Text(auth.usuario_nombre, size=12, weight=ft.FontWeight.W_500, color=t["text_primary"])
    user_label = ft.Row(
        [user_dot, user_name],
        spacing=6,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    def _update_profile():
        user_name.value = auth.usuario_nombre
        if user_name.page:
            user_name.update()

    def _show_user_modal(e):
        _t = get_theme(page)
        def _cambiar(e):
            page.close(dlg)
            auth.logout()
            _update_profile()
            _open_login_dialog()
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_t["bg_card"],
            title=ft.Row(
                [
                    ft.Text(auth.usuario_nombre, size=15, weight=ft.FontWeight.W_500, expand=True),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=18,
                        icon_color=_t["text_secondary"],
                        on_click=lambda e: page.close(dlg),
                    ),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[
                ft.TextButton("Cambiar usuario", icon=ft.Icons.SWAP_HORIZ, on_click=_cambiar),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        page.open(dlg)

    sidebar_ref = {"c": None}
    rail_ref = {"c": None}
    toggle_theme_btn = {"c": None}

    def _build_sidebar(t: dict) -> ft.Container:
        rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=t["sidebar_width"],
            bgcolor=t["bg_card"],
            indicator_color=t["accent"],
            destinations=[
                ft.NavigationRailDestination(
                    icon=icon_out,
                    selected_icon=icon_sel,
                    label=label,
                )
                for label, icon_out, icon_sel in TABS
            ],
            on_change=lambda e: _switch(e.control.selected_index),
        )
        rail_ref["c"] = rail

        toggle_btn = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.DARK_MODE,
            icon_size=18,
            icon_color=t["text_secondary"],
            tooltip="Cambiar tema claro/oscuro",
            style=ft.ButtonStyle(padding=ft.padding.all(6)),
        )
        toggle_theme_btn["c"] = toggle_btn

        sidebar = ft.Container(
            width=t["sidebar_width"],
            bgcolor=t["bg_card"],
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Image(src="logo.svg", width=t["logo_size"], height=t["logo_size"]),
                        padding=ft.padding.symmetric(vertical=12),
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(content=rail, expand=True),
                    bell.control,
                    toggle_btn,
                    ft.Divider(height=1, thickness=0.5, color=t["border"]),
                    ft.Container(
                        content=user_label,
                        padding=ft.padding.only(bottom=12),
                        alignment=ft.alignment.center,
                        ink=True,
                        on_click=_show_user_modal,
                    ),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
        )
        sidebar_ref["c"] = sidebar
        return sidebar

    divider_ref = {"c": None}

    def _rebuild_divider(t: dict) -> ft.VerticalDivider:
        d = ft.VerticalDivider(width=1, color=t["border_light"])
        divider_ref["c"] = d
        return d

    sidebar = _build_sidebar(t)
    divider = _rebuild_divider(t)

    # ── Title bar ─────────────────────────────────────────────────────────────
    def _minimize(e):
        page.window.minimized = True
        page.update()

    def _maximize(e):
        page.window.maximized = not page.window.maximized
        page.update()

    def _close(e):
        page.window.close()

    def _toggle_fullscreen(e=None):
        page.window.full_screen = not page.window.full_screen
        page.update()

    def _toggle_theme(e=None):
        page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        t2 = get_theme(page)
        page.bgcolor = t2["bg_page"]

        sidebar_ref["c"].bgcolor = t2["bg_card"]
        rail_ref["c"].bgcolor = t2["bg_card"]
        rail_ref["c"].indicator_color = t2["accent"]
        user_name.color = t2["text_primary"]
        divider_ref["c"].color = t2["border_light"]
        toggle_theme_btn["c"].icon = ft.Icons.LIGHT_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.DARK_MODE
        toggle_theme_btn["c"].icon_color = t2["text_secondary"]

        old_title = title_bar_ref["c"]
        idx = page.controls[0].controls.index(old_title)
        new_title = _build_title_bar(t2)
        page.controls[0].controls[idx] = new_title

        _views.clear()
        _switch(current_tab["idx"])

        overlay.bgcolor = t2["bg_page"]
        load_bar.color = t2["accent"]
        load_bar.bgcolor = t2["bg_input"]
        load_status.color = t2["text_secondary"]

        page.update()

    if toggle_theme_btn["c"]:
        toggle_theme_btn["c"].on_click = _toggle_theme

    title_bar_ref = {"c": None}
    def _build_title_bar(t: dict) -> ft.Container:
        title_bar = ft.Container(
            height=TITLE_BAR_HEIGHT,
            bgcolor=t["bg_titlebar"],
            padding=0,
            content=ft.Stack(
                [
                    ft.WindowDragArea(
                        ft.Container(expand=True),
                        left=0, right=0, top=0, bottom=0,
                        maximizable=True,
                    ),
                    ft.Container(
                        content=ft.Text(
                            "Gestion M.I.G.",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=t["text_primary"],
                        ),
                        alignment=ft.Alignment(0, 0),
                        left=0, right=0, top=0, bottom=0,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.MINIMIZE,
                                    icon_size=16,
                                    icon_color=t["text_primary"],
                                    on_click=_minimize,
                                    style=ft.ButtonStyle(
                                        padding=ft.padding.symmetric(horizontal=12, vertical=0),
                                        shape={},
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CROP_SQUARE,
                                    icon_size=14,
                                    icon_color=t["text_primary"],
                                    on_click=_maximize,
                                    style=ft.ButtonStyle(
                                        padding=ft.padding.symmetric(horizontal=12, vertical=0),
                                        shape={},
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.FULLSCREEN,
                                    icon_size=14,
                                    icon_color=t["text_primary"],
                                    on_click=_toggle_fullscreen,
                                    tooltip="Pantalla completa (F11)",
                                    style=ft.ButtonStyle(
                                        padding=ft.padding.symmetric(horizontal=12, vertical=0),
                                        shape={},
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=16,
                                    icon_color=t["text_primary"],
                                    on_click=_close,
                                    style=ft.ButtonStyle(
                                        padding=ft.padding.symmetric(horizontal=14, vertical=0),
                                        shape={},
                                    ),
                                ),
                            ],
                            spacing=0,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        right=0, top=0, bottom=0,
                    ),
                ],
            ),
        )
        title_bar_ref["c"] = title_bar
        return title_bar

    title_bar = _build_title_bar(t)

    main_ui = ft.Row(
        [sidebar, divider, content_area],
        expand=True,
        spacing=0,
    )

    # ── Global keyboard shortcuts ─────────────────────────────────────────────
    _prev_kb = page.on_keyboard_event

    def _global_kb(e: ft.KeyboardEvent):
        if e.key == "F11":
            _toggle_fullscreen()
        elif _prev_kb:
            try:
                _prev_kb(e)
            except Exception:
                pass

    page.on_keyboard_event = _global_kb

    # ── Login / logout helpers ────────────────────────────────────────────────
    def _on_login_success():
        print("[login] _on_login_success: overlay.visible=False, switching to Dashboard")
        overlay.visible = False
        _update_profile()
        try:
            _switch(0)
        except Exception as ex:
            print(f"[login] Error en _switch(0): {ex}")
        page.update()

    def _open_login_dialog():
        import asyncio
        users = get_usuarios()
        print(f"[main] _open_login_dialog — usuarios encontrados: {len(users)}")
        if not users:
            print(f"[main] No hay usuarios → abriendo RegisterDialog")
            dlg = RegisterDialog(page, on_success=_on_login_success)
            page.open(dlg)
        else:
            print(f"[main] Hay usuarios → abriendo LoginDialog")
            dlg = LoginDialog(page, on_success=_on_login_success)
            page.open(dlg)
            async def _focus():
                await asyncio.sleep(0.15)
                page.update()
            page.run_task(_focus)

    def _on_logout(e):
        auth.logout()
        overlay.visible = True
        _update_profile()
        page.update()
        _open_login_dialog()

    # ── Build page: title_bar always visible + content with overlay ─────────────
    page.add(
        ft.Column(
            [
                title_bar,
                ft.Stack(
                    [
                        main_ui,
                        overlay,
                    ],
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
    )

    # ── Loading sequence with real progress ───────────────────────────────────
    _load_step(0.05, "Iniciando aplicación...")
    import time
    time.sleep(0.15)

    _load_step(0.20, "Inicializando base de datos...")
    time.sleep(0.1)

    _load_step(0.45, "Cargando facturación...")
    time.sleep(0.15)

    _load_step(0.65, "Cargando productos...")
    time.sleep(0.15)

    _load_step(0.85, "Preparando interfaz...")
    time.sleep(0.15)

    _load_step(1.0, "Listo")
    time.sleep(0.2)

    _open_login_dialog()


if __name__ == "__main__":
    ft.app(main, assets_dir="assets")
