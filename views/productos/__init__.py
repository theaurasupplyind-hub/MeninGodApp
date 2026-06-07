"""
productos/__init__.py
Pantalla principal de Productos con selector de modo:
  [Stock] [Compras] [Proveedores]
"""
import flet as ft
from theme import get_theme
from views.productos.stock import StockView
from views.productos.compras import ComprasView
from views.productos.proveedores import ProveedoresView


def ProductosView(page: ft.Page, on_switch_tab=None):
    t = get_theme(page)
    mode = {"value": "stock"}

    content_area = ft.Container(expand=True)

    def _get_view(m: str):
        if m == "stock":
            return StockView(page, on_nueva_compra=lambda: _switch("compras"))
        if m == "compras":
            return ComprasView(page, on_switch_tab=on_switch_tab)
        if m == "proveedores":
            return ProveedoresView(page, on_switch_tab=on_switch_tab)
        return StockView(page)

    def _switch(m: str):
        mode["value"] = m
        btn_stock.style = _btn_style(m == "stock")
        btn_compras.style = _btn_style(m == "compras")
        btn_proveedores.style = _btn_style(m == "proveedores")
        try:
            content_area.content = _get_view(m)
            if hasattr(content_area.content, "refresh_data"):
                content_area.content.refresh_data()
            page.update()
        except Exception as ex:
            print(f"Error switching to {m}: {ex}")
            import traceback
            traceback.print_exc()

    def _btn_style(active: bool):
        return ft.ButtonStyle(
            bgcolor=t["accent"] if active else t["bg_row_odd"],
            color=t["accent_text"] if active else t["text_secondary"],
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(10, 20),
        )

    btn_stock = ft.ElevatedButton(
        "Stock", icon=ft.icons.INVENTORY_2_OUTLINED,
        style=_btn_style(True), on_click=lambda e: _switch("stock"),
    )
    btn_compras = ft.ElevatedButton(
        "Compras", icon=ft.icons.SHOPPING_CART_OUTLINED,
        style=_btn_style(False), on_click=lambda e: _switch("compras"),
    )
    btn_proveedores = ft.ElevatedButton(
        "Proveedores", icon=ft.icons.PEOPLE_OUTLINED,
        style=_btn_style(False), on_click=lambda e: _switch("proveedores"),
    )

    content_area.content = _get_view("stock")

    view = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Productos", size=22, weight=ft.FontWeight.W_500),
                        ft.Row([btn_stock, btn_compras, btn_proveedores], spacing=8),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                content_area,
            ],
            spacing=12,
            expand=True,
        ),
        padding=28,
        expand=True,
    )

    view.refresh_data = lambda: (
        hasattr(content_area.content, "refresh_data") and
        content_area.content.refresh_data()
    )
    return view
