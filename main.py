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
from db.database import init_db
from views.dashboard import DashboardView
from views.facturacion import FacturacionView
from views.clientes import ClientesView
from views.productos import ProductosView
from views.stock_alert import StockAlertBell
from views.cuenta_wasi import CuentaWasiView 

TABS = [
    ("Dashboard",        ft.icons.DASHBOARD_OUTLINED,       ft.icons.DASHBOARD),
    ("Facturacion",      ft.icons.RECEIPT_LONG_OUTLINED,    ft.icons.RECEIPT_LONG),
    ("Clientes",         ft.icons.PEOPLE_OUTLINED,          ft.icons.PEOPLE),
    ("Productos",        ft.icons.INVENTORY_2_OUTLINED,     ft.icons.INVENTORY_2),
    ("Cuenta",      ft.icons.ACCOUNT_BALANCE_WALLET_OUTLINED, ft.icons.ACCOUNT_BALANCE_WALLET),
]


def main(page: ft.Page):
    page.title = "MVP 1.0"
    page.window_width = 1280
    page.window_height = 740
    page.window_min_width = 980
    page.window_min_height = 620
    page.padding = 0

    page.theme_mode = ft.ThemeMode.DARK
    t = get_theme(page)
    page.bgcolor = t["bg_page"]
    page.theme = ft.Theme(
        color_scheme_seed=ft.colors.AMBER_700,
        use_material3=True,
        navigation_rail_theme=ft.NavigationRailTheme(
            indicator_color=t["accent"],
        ),
    )
    page.dark_theme = ft.Theme(
        color_scheme_seed=ft.colors.AMBER_700,
        use_material3=True,
    )

    log.info("init_db()")
    init_db()
    log.info("DB inicializada OK")

    content_area = ft.Container(expand=True)
    _views: dict[int, ft.Control] = {}
    current_tab = {"idx": 0}

    # ── Bell de alertas ────────────────────────────────────────────────────────
    bell = StockAlertBell(page, on_go_stock=lambda: _switch(3))

    def _error_view(title: str, error: Exception) -> ft.Control:
        detail = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        print("\n=== DEMO1 DEBUG ERROR ===")
        print(detail)
        log.error(f"VIEW ERROR — {title}:\n{detail}")
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=22, weight=ft.FontWeight.W_600, color=ft.colors.RED_700),
                    ft.Text(
                        "La pantalla falló al renderizar. El detalle completo también se imprimió en consola.",
                        color=ft.colors.GREY_700,
                    ),
                    ft.Container(
                        content=ft.Text(detail, selectable=True, size=12, color=ft.colors.WHITE),
                        bgcolor="#1F2937",
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
        # Refrescar stock en pantalla Productos si está cargada
        if 3 in _views:
            try:
                _views[3].refresh_data()
            except Exception:
                pass
        page.update()

    def _on_estado_changed(factura_id: int, nuevo_estado: str):
        log.debug(f"Estado cambiado: factura_id={factura_id} → {nuevo_estado}")
        _refresh_dashboard()

    def _build_view(idx: int) -> ft.Control:
        log.debug(f"_build_view({idx})")
        if idx == 0:
            return DashboardView(
                page,
                on_nueva_factura=lambda e: _switch(1),
                on_refresh=lambda e: _refresh_dashboard(),
                on_estado_changed=_on_estado_changed,
                on_switch_tab=_switch,
            )
        if idx == 1:
            return FacturacionView(
                page,
                on_factura_guardada=_refresh_dashboard,
                on_switch_tab=_switch,
            )
        if idx == 2:
            return ClientesView(page, t, on_switch_tab=_switch)
        if idx == 3:
            return ProductosView(page, on_switch_tab=_switch)
        if idx == 4:
            return CuentaWasiView(page, t, on_switch_tab=_switch)
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
            rail.selected_index = idx
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
                    ft.Text("Error de la aplicacion", size=22, weight=ft.FontWeight.W_600, color=ft.colors.RED_700),
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

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=t["sidebar_width"],
        bgcolor=t["bg_card"],
        indicator_color=t["accent"],
        leading=ft.Container(
            content=ft.Image(src="logo.svg", width=t["logo_size"], height=t["logo_size"]),
            padding=ft.padding.symmetric(vertical=12),
            width=t["sidebar_width"],
            alignment=ft.alignment.center,
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=icon_out,
                selected_icon=icon_sel,
                label=label,
            )
            for label, icon_out, icon_sel in TABS
        ],
        on_change=lambda e: _switch(e.control.selected_index),
        trailing=ft.Container(
            content=ft.Column(
                [
                    bell.control,
                    ft.Divider(height=1, color=t["border_light"]),
                    ft.TextButton(
                        "Cerrar sesion",
                        icon=ft.icons.LOGOUT,
                        style=ft.ButtonStyle(color=t["text_secondary"]),
                        on_click=lambda e: print("logout"),
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(bottom=12),
        ),
    )

    divider = ft.VerticalDivider(width=1, color=t["border_light"])
    content_area.content = _get_view(0)

    page.add(
        ft.Row(
            [rail, divider, content_area],
            expand=True,
            spacing=0,
        )
    )

if __name__ == "__main__":
    ft.app(main, assets_dir="assets")
