import logging
log = logging.getLogger("mvp10")

import flet as ft
from theme import get_theme


def NuevoProdTabView(page: ft.Page):
    t = get_theme(page)

    def _tf(hint, width=None, keyboard_type=None):
        return ft.TextField(
            hint_text=hint,
            border_radius=7,
            height=38,
            text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            width=width,
            expand=width is None,
            border_color=t["border"],
            focused_border_color=t["accent"],
            bgcolor=t["bg_input"],
            color=t["text_primary"],
            keyboard_type=keyboard_type,
        )

    def _dd(hint, options=None, width=None):
        return ft.Dropdown(
            hint_text=hint,
            options=options or [],
            border_radius=7,
            height=38,
            text_size=13,
            content_padding=ft.padding.symmetric(4, 10),
            width=width,
            expand=width is None,
            border_color=t["border"],
            focused_border_color=t["accent"],
            color=t["text_primary"],
            bgcolor=t["bg_input"],
            hint_style=ft.TextStyle(color=t["text_secondary"]),
        )

    tf_detalle = _tf("Nombre / descripcion del articulo")
    tf_detalle.expand = False

    dd_origen = _dd("Origen", [
        ft.dropdown.Option("proveedor", "Proveedor (stock via compras)"),
        ft.dropdown.Option("propio", "Propio (fabrica uds.)"),
    ])
    dd_origen.expand = False
    dd_origen.value = "proveedor"

    def _fake_variante_row(n):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(str(n), size=12, color=t["text_secondary"], width=20),
                    _dd("Color", options=[
                        ft.dropdown.Option("1", "Negro"),
                        ft.dropdown.Option("2", "Blanco"),
                    ], width=120),
                    _dd("Talla", options=[
                        ft.dropdown.Option("1", "S"),
                        ft.dropdown.Option("2", "M"),
                        ft.dropdown.Option("3", "L"),
                    ], width=100),
                    _tf("Precio venta", keyboard_type=ft.KeyboardType.NUMBER),
                    ft.IconButton(ft.icons.CLOSE, icon_size=14, icon_color=ft.colors.ERROR,
                                  style=ft.ButtonStyle(padding=ft.padding.all(2))),
                ],
                spacing=4,
            ),
            padding=ft.padding.symmetric(2, 0),
        )

    variantes_col = ft.ListView(spacing=4, expand=True)

    for i in range(1, 4):
        variantes_col.controls.append(_fake_variante_row(i))

    return ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.Text("Nuevo producto", size=18, weight=ft.FontWeight.W_500, expand=True),
                    ft.TextButton("<-- Volver al listado",
                                  style=ft.ButtonStyle(color=t["text_secondary"])),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1, color=t["border_light"]),
                ft.Text("Nombre del articulo *", size=12, color=t["text_secondary"]),
                tf_detalle,
                ft.Column([
                    ft.Text("Origen", size=12, color=t["text_secondary"]),
                    dd_origen,
                ]),
                ft.Divider(height=1, color=t["border_light"]),
                ft.Row(
                    [
                        ft.Text("Variantes", size=12, weight=ft.FontWeight.W_600,
                                color=t["text_secondary"], expand=True),
                        ft.TextButton("+ Agregar",
                                      style=ft.ButtonStyle(padding=ft.padding.symmetric(4, 8))),
                        ft.TextButton("Generar combinaciones",
                                      style=ft.ButtonStyle(padding=ft.padding.symmetric(4, 8))),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(
                                ft.Row(
                                    [
                                        ft.Container(width=20),
                                        ft.Text("Color", size=10, weight=ft.FontWeight.W_500,
                                                color=t["text_secondary"], width=120),
                                        ft.Text("Talla", size=10, weight=ft.FontWeight.W_500,
                                                color=t["text_secondary"], width=100),
                                        ft.Text("Precio venta", size=10, weight=ft.FontWeight.W_500,
                                                color=t["text_secondary"], expand=True),
                                        ft.Container(width=30),
                                    ],
                                    spacing=4,
                                ),
                                padding=ft.padding.symmetric(4, 0),
                            ),
                            variantes_col,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    border=ft.border.all(0.5, t["border"]),
                    border_radius=6,
                    padding=ft.padding.all(6),
                    expand=True,
                ),
                ft.Row(
                    [
                        ft.TextButton("Cancelar"),
                        ft.ElevatedButton(
                            "Guardar",
                            bgcolor=t["accent"],
                            color=t["accent_text"],
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
            ],
            spacing=8,
            expand=True,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        expand=True,
    )
