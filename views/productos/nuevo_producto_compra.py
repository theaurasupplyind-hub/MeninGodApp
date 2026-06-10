"""
nuevo_producto_compra.py
Modal rápido para crear producto durante el flujo de compra.
Solo Nombre, Precio venta, Colores y Talles.
"""

import flet as ft
from db.database import save_producto, save_variante, save_color, save_talla


def NuevoProductoCompraDialog(page: ft.Page, t: dict, on_created=None):
    tf_nombre = ft.TextField(
        label="Nombre *",
        hint_text="Ej: Remera Oversize",
        border_radius=7, height=42, text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        bgcolor=t["bg_input"], border_color=t["border"],
        focused_border_color=t["accent"], color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
        autofocus=True,
    )
    tf_precio = ft.TextField(
        label="Precio venta *",
        hint_text="Precio de venta al público (para Facturación)",
        border_radius=7, height=42, text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        bgcolor=t["bg_input"], border_color=t["border"],
        focused_border_color=t["accent"], color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    color_chips = ft.Row(spacing=6, wrap=True)
    talla_chips = ft.Row(spacing=6, wrap=True)

    tf_color_input = ft.TextField(
        hint_text="Agregar color",
        border_radius=7, height=36, text_size=12,
        content_padding=ft.padding.symmetric(6, 10),
        bgcolor=t["bg_input"], border_color=t["border"],
        focused_border_color=t["accent"], color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )
    tf_talle_input = ft.TextField(
        hint_text="Agregar talle",
        border_radius=7, height=36, text_size=12,
        content_padding=ft.padding.symmetric(6, 10),
        bgcolor=t["bg_input"], border_color=t["border"],
        focused_border_color=t["accent"], color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )

    def _make_chip(text, container):
        return ft.Container(
            content=ft.Row([
                ft.Text(text, size=12, color=t["text_primary"]),
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Icon(ft.Icons.CLOSE, size=14, color=t["text_secondary"]),
                        width=20, height=20,
                    ),
                    on_tap=lambda e, t=text, c=container: _remove_chip(t, c),
                ),
            ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=t["bg_selected"], border_radius=14,
            padding=ft.padding.symmetric(4, 10),
        )

    def _remove_chip(text, container):
        container.controls = [c for c in container.controls
                              if not (isinstance(c, ft.Container)
                                      and (c.content.controls[0].value or "") == text)]
        dlg.update()

    def _add_color(e):
        text = (tf_color_input.value or "").strip()
        if not text:
            return
        if any(
            isinstance(c, ft.Container) and (c.content.controls[0].value or "") == text
            for c in color_chips.controls
        ):
            return
        chip = _make_chip(text, color_chips)
        color_chips.controls = [*color_chips.controls, chip]
        tf_color_input.value = ""
        dlg.update()

    def _add_talle(e):
        text = (tf_talle_input.value or "").strip()
        if not text:
            return
        if any(
            isinstance(c, ft.Container) and (c.content.controls[0].value or "") == text
            for c in talla_chips.controls
        ):
            return
        chip = _make_chip(text, talla_chips)
        talla_chips.controls = [*talla_chips.controls, chip]
        tf_talle_input.value = ""
        dlg.update()

    tf_color_input.on_submit = lambda e: (_add_color(e), tf_color_input.focus())
    tf_talle_input.on_submit = lambda e: (_add_talle(e), tf_talle_input.focus())

    error_text = ft.Text("", size=12, color=ft.Colors.RED_400)

    def _crear_producto(colores, talles):
        nombre = (tf_nombre.value or "").strip()
        try:
            precio = float((tf_precio.value or "").strip().replace(",", "."))
        except (ValueError, AttributeError):
            return

        producto_id = save_producto({"detalle": nombre, "precio_unitario": precio})

        if colores and talles:
            for cn in colores:
                color_id = save_color(cn, "")
                for tn in talles:
                    talla_id = save_talla(tn)
                    save_variante(producto_id, {
                        "color_id": color_id,
                        "talla_id": talla_id,
                        "precio_unitario": precio,
                        "stock_actual": 0,
                        "stock_minimo": 0,
                        "precio_compra": 0,
                    })
        else:
            save_variante(producto_id, {
                "color_id": None,
                "talla_id": None,
                "precio_unitario": precio,
                "stock_actual": 0,
                "stock_minimo": 0,
                "precio_compra": 0,
            })

        page.close(dlg)
        if on_created:
            on_created({"id": producto_id, "detalle": nombre, "precio_unitario": precio})

    def _do_create(e):
        error_text.value = ""
        nombre = (tf_nombre.value or "").strip()
        try:
            precio = float((tf_precio.value or "").strip().replace(",", "."))
        except (ValueError, AttributeError):
            error_text.value = "Precio venta inválido."
            page.update()
            return
        if not nombre:
            error_text.value = "El nombre del producto es obligatorio."
            page.update()
            return

        colores = []
        for c in color_chips.controls:
            if isinstance(c, ft.Container) and c.content.controls:
                colores.append(c.content.controls[0].value or "")

        talles = []
        for t in talla_chips.controls:
            if isinstance(t, ft.Container) and t.content.controls:
                talles.append(t.content.controls[0].value or "")

        if colores and talles:
            _crear_producto(colores, talles)
        else:
            _crear_producto(colores, talles)
            page.open(ft.SnackBar(
                ft.Text("Producto creado sin variantes", color=ft.Colors.WHITE),
                bgcolor=t["accent"], duration=2500,
            ))

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=t["bg_card"],
        title=ft.Text("Nuevo Producto", size=16, weight=ft.FontWeight.W_500),
        content=ft.Container(
            content=ft.Column([
                tf_nombre,
                tf_precio,
                ft.Text("Colores", size=11, color=t["text_secondary"]),
                ft.Row([
                    tf_color_input,
                    ft.GestureDetector(
                        content=ft.Container(
                            content=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=22, color=t["accent"]),
                            width=36, height=36,
                        ),
                        on_tap=_add_color,
                    ),
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                color_chips,
                ft.Text("Talles", size=11, color=t["text_secondary"]),
                ft.Row([
                    tf_talle_input,
                    ft.GestureDetector(
                        content=ft.Container(
                            content=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=22, color=t["accent"]),
                            width=36, height=36,
                        ),
                        on_tap=_add_talle,
                    ),
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                talla_chips,
                ft.Text(
                    "* El precio de compra se define en cada fila al cargar la compra",
                    size=10, color=t["text_hint"], italic=True,
                ),
                error_text,
            ], spacing=8, expand=True, scroll=ft.ScrollMode.AUTO),
            width=380,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg)),
            ft.ElevatedButton(
                "Crear", icon=ft.Icons.CHECK,
                bgcolor=t["accent"], color=t["accent_text"],
                on_click=_do_create,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg