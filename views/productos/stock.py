import logging
log = logging.getLogger("mvp10")

import flet as ft
from theme import get_theme
from views.productos.nuevo_producto import build_form

from db.database import (
    get_productos, delete_producto,
    ajustar_stock, get_stock_bajo,
    get_variantes_by_producto,
)


def _fmt(val) -> str:
    try:
        return f"${int(float(val)):,}".replace(",", ".")
    except Exception:
        return "$0"


def _fmt_stock(val) -> str:
    try:
        v = float(val)
        return str(int(v)) if v == int(v) else f"{v:.1f}"
    except Exception:
        return "0"


def _parse_input_number(raw_val: str) -> float:
    val = (raw_val or "0").strip()
    if "," in val:
        val = val.replace(".", "")
        val = val.replace(",", ".")
    return float(val)


def _stock_badge(stock_actual: float, stock_minimo: float):
    try:
        actual = float(stock_actual or 0)
        minimo = float(stock_minimo or 0)
    except Exception:
        actual, minimo = 0, 0

    if actual <= 0:
        bg, fg, label = "#FCEBEB", "#A32D2D", "Sin stock"
    elif minimo > 0 and actual <= minimo:
        bg, fg, label = "#FAEEDA", "#854F0B", "Stock bajo"
    else:
        bg, fg, label = "#EAF3DE", "#3B6D11", "OK"

    return ft.Container(
        ft.Text(label, size=11, color=fg, weight=ft.FontWeight.W_600),
        bgcolor=bg,
        border_radius=20,
        padding=ft.padding.symmetric(3, 10),
    )


from views.flow_guide import HelpButton




def StockView(page: ft.Page, on_nueva_compra=None):
    t = get_theme(page)
    search_filter: dict[str, str] = {"value": ""}
    form_mode: dict[str, str | None] = {"value": None}

    def _close_dlg(dlg):
        page.close(dlg)

    def _show_message(text: str, color=t["accent"]):
        sb = ft.SnackBar(
            ft.Text(text, color=ft.colors.WHITE),
            bgcolor=color,
            duration=3200,
        )
        page.open(sb)

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

    tf_search       = _tf("Buscar producto...")

    table_col   = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)

    def _open_form(e=None, producto=None):
        main_container.content = build_form(
            page, t, producto=producto,
            on_saved=lambda: _close_form(),
            on_cancel=lambda: _close_form(),
        )
        form_mode["value"] = "active"
        if main_container.page:
            main_container.update()

    def _close_form():
        form_mode["value"] = None
        _render()
        _refresh_table()

    help_btn = HelpButton([
        {"text": "Creá un artículo base y agregale variantes (color/talla/precio/stock)"},
        {"text": "Las variantes se suman al stock total del artículo"},
        {"text": "Andá a Compras para registrar compras de insumos"},
    ], page)

    def _build_table_view():
        productos_all = get_productos()
        stock_bajo_count = len(get_stock_bajo())
        subtitle_parts = [f"{len(productos_all)} productos registrados"]
        if stock_bajo_count:
            subtitle_parts.append(f"  ⚠  {stock_bajo_count} con stock bajo")
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text("  |  ".join(subtitle_parts), size=13,
                                                color=t["accent"] if stock_bajo_count else t["text_secondary"]),
                                    ],
                                    spacing=2, expand=True,
                                ),
                                help_btn,
                                ft.ElevatedButton(
                                    "Nuevo producto", icon=ft.icons.ADD_CIRCLE_OUTLINE, on_click=_open_form,
                                    style=ft.ButtonStyle(bgcolor=t["accent"], color=t["accent_text"],
                                                         shape=ft.RoundedRectangleBorder(radius=8),
                                                         padding=ft.padding.symmetric(10, 18)),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ),
                    ft.Container(content=tf_search, margin=ft.margin.only(bottom=2)),
                    ft.Container(
                        content=table_col, expand=True,
                        border=ft.border.all(0.5, t["border"]), border_radius=12,
                        bgcolor=t["bg_card"], alignment=ft.Alignment(-1, -1),
                    ),
                ],
                spacing=6, expand=True,
            ),
            padding=ft.padding.only(top=8),
            expand=True,
        )

    def _render():
        main_container.content = _build_table_view()
        if main_container.page:
            main_container.update()

    def _open_ajuste(producto: dict):
        if producto.get("tipo_origen") == "proveedor":
            _show_message("El stock de productos de proveedor solo se modifica desde Compras.", t["accent"])
            return

        tf_delta = ft.TextField(
            hint_text="Ej: +10 o -5",
            border_radius=7,
            height=38,
            text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            border_color=t["border"],
            focused_border_color=t["accent"],
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def _do_ajuste(ev, d):
            try:
                delta = _parse_input_number(tf_delta.value)
            except ValueError:
                _show_message("Ingresá un número válido (ej: 10 o -5).", t["accent"])
                return
            ajustar_stock(producto["id"], delta)
            signo = "+" if delta >= 0 else ""
            _show_message(
                f"Stock de '{producto['detalle']}' ajustado ({signo}{int(delta)}).",
                ft.colors.GREEN_700,
            )
            page.close(d)
            _refresh_table()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ajuste de stock", size=16, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(producto.get("detalle", ""), size=14, weight=ft.FontWeight.W_600),
                        ft.Divider(height=10),
                        ft.Text("Cantidad a agregar o quitar", size=12, color=t["text_secondary"]),
                        tf_delta,
                        ft.Text("Usá números positivos para ingresar stock y negativos para dar de baja.", size=11, color=t["text_secondary"]),
                    ],
                    spacing=8,
                    tight=True,
                ),
                width=360,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: _close_dlg(dlg)),
                ft.ElevatedButton(
                    "Aplicar",
                    bgcolor=t["accent"],
                    color=t["accent_text"],
                    on_click=lambda ev: _do_ajuste(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _confirm_delete(producto):
        detalle = producto.get("detalle", "")

        def _do_delete(ev, d):
            delete_producto(producto["id"])
            _show_message(f"Producto '{detalle}' eliminado.", ft.colors.RED_700)
            page.close(d)
            _refresh_table()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar producto"),
            content=ft.Text(f"¿Seguro que querés eliminar '{detalle}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: _close_dlg(dlg)),
                ft.ElevatedButton(
                    "Eliminar",
                bgcolor=ft.colors.ERROR,
                color=t["accent_text"],
                    on_click=lambda ev: _do_delete(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _build_row(producto: dict, zebra: bool):
        variantes = get_variantes_by_producto(producto["id"])
        total_stock = sum(float(v.get("stock_actual", 0) or 0) for v in variantes)
        min_stock = min((float(v.get("stock_minimo", 0) or 0) for v in variantes), default=0)
        var_count = len(variantes)
        var_label = f" ({var_count} var)" if var_count else ""

        tipo_origen = producto.get("tipo_origen", "proveedor")
        cost_key = "precio_fabricacion" if tipo_origen == "propio" else "precio_compra"
        if tipo_origen == "propio":
            costo_total = sum(float(v.get("precio_fabricacion", 0) or 0) * float(v.get("stock_actual", 0) or 0) for v in variantes)
        else:
            costo_total = sum(float(v.get("precio_compra", 0) or 0) * float(v.get("stock_actual", 0) or 0) for v in variantes)

        if variantes:
            precios_venta = [float(v.get("precio_unitario", 0) or 0) for v in variantes if float(v.get("precio_unitario", 0) or 0) > 0]
            precio_venta_unit = sum(precios_venta) / len(precios_venta) if precios_venta else 0
            stock_con_costo = sum(
                float(v.get("stock_actual", 0) or 0)
                for v in variantes if float(v.get(cost_key, 0) or 0) > 0
            )
            if stock_con_costo > 0:
                costo_unit = sum(
                    float(v.get(cost_key, 0) or 0) * float(v.get("stock_actual", 0) or 0)
                    for v in variantes
                ) / stock_con_costo
            else:
                costos = [float(v.get(cost_key, 0) or 0) for v in variantes if float(v.get(cost_key, 0) or 0) > 0]
                costo_unit = sum(costos) / len(costos) if costos else 0
        else:
            precio_venta_unit = 0
            costo_unit = 0

        origen_badge = ft.Container(
            ft.Text("Propio" if tipo_origen == "propio" else "Proveedor", size=9,
                    weight=ft.FontWeight.W_600, color=t["text_secondary"]),
            bgcolor=t["border_light"],
            border_radius=8, padding=ft.padding.symmetric(1, 6),
        )

        # ── Expand/collapse state ──
        expanded = {"value": False}
        variant_details = ft.Column(spacing=0, visible=False)

        def _toggle_product(e):
            expanded["value"] = not expanded["value"]
            variant_details.visible = expanded["value"]
            chevron_btn.icon = ft.icons.KEYBOARD_ARROW_DOWN if expanded["value"] else ft.icons.KEYBOARD_ARROW_RIGHT
            if variant_details.page:
                variant_details.update()

        chevron_btn = ft.IconButton(
            icon=ft.icons.KEYBOARD_ARROW_RIGHT, icon_size=18,
            on_click=_toggle_product,
            style=ft.ButtonStyle(padding=ft.padding.all(2)),
        )

        # ── Group variants by color ──
        by_color: dict[str, list] = {}
        for v in variantes:
            by_color.setdefault(v.get("color") or "Sin color", []).append(v)

        color_sections: list[ft.Control] = []
        for cname in sorted(by_color.keys()):
            cvars = by_color[cname]
            col_exp = {"value": False}
            col_chevron = ft.Icon(ft.icons.KEYBOARD_ARROW_RIGHT, size=14, color=t["text_hint"])

            talla_rows = []
            for v in cvars:
                tname = v.get("talla") or "-"
                cost_val = v.get("precio_fabricacion") if tipo_origen == "propio" else v.get("precio_compra")
                talla_rows.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(width=16),
                            ft.Text(tname, size=12, width=60, color=t["text_primary"]),
                            ft.Text(_fmt(v["precio_unitario"]), size=12, width=80,
                                    text_align=ft.TextAlign.RIGHT, color=t["text_primary"]),
                            ft.Text(_fmt_stock(v["stock_actual"]), size=12, width=60,
                                    text_align=ft.TextAlign.CENTER,
                                    color=ft.colors.ERROR if float(v.get("stock_actual", 0) or 0) <= 0 else t["text_primary"]),
                            ft.Text(_fmt(cost_val or 0), size=12, width=80,
                                    text_align=ft.TextAlign.RIGHT, color=t["text_secondary"]),
                        ], spacing=4),
                        padding=ft.padding.symmetric(3, 14),
                    )
                )

            talla_container = ft.Column(talla_rows, spacing=1, visible=False)

            def _toggle_col(e, tc=talla_container, ce=col_exp, ch=col_chevron):
                ce["value"] = not ce["value"]
                tc.visible = ce["value"]
                ch.name = ft.icons.KEYBOARD_ARROW_DOWN if ce["value"] else ft.icons.KEYBOARD_ARROW_RIGHT
                if tc.page:
                    tc.update()

            color_sections.append(
                ft.Column([
                    ft.Container(
                        content=ft.Row([
                            col_chevron,
                            ft.Text(f"{cname} ({len(cvars)})", size=12, weight=ft.FontWeight.W_600,
                                    color=t["text_primary"]),
                        ], spacing=4),
                        on_click=_toggle_col,
                        padding=ft.padding.symmetric(6, 14),
                        bgcolor=t["bg_header"],
                        border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(width=16),
                                    ft.Text("Talle", size=10, weight=ft.FontWeight.W_500,
                                            color=t["text_secondary"], width=60),
                                    ft.Text("Precio", size=10, weight=ft.FontWeight.W_500,
                                            color=t["text_secondary"], width=80, text_align=ft.TextAlign.RIGHT),
                                    ft.Text("Stock", size=10, weight=ft.FontWeight.W_500,
                                            color=t["text_secondary"], width=60, text_align=ft.TextAlign.CENTER),
                                    ft.Text("Costo", size=10, weight=ft.FontWeight.W_500,
                                            color=t["text_secondary"], width=80, text_align=ft.TextAlign.RIGHT),
                                ], spacing=4),
                                padding=ft.padding.symmetric(4, 14),
                            ),
                            talla_container,
                        ], spacing=0),
                        padding=0,
                    ),
                ], spacing=0)
            )

        variant_details.controls = color_sections

        header = ft.Container(
            content=ft.Row(
                [
                    chevron_btn,
                    ft.Column([
                        ft.Text(f"{producto['detalle']}{var_label}", size=13,
                                weight=ft.FontWeight.W_500,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        origen_badge,
                    ], spacing=2, expand=True),
                    ft.Text(_fmt(costo_total), size=12, width=90, text_align=ft.TextAlign.RIGHT, color=t["text_secondary"]),
                    ft.Text(
                        _fmt_stock(total_stock), size=13, width=70, text_align=ft.TextAlign.CENTER,
                        color=ft.colors.ERROR if total_stock <= 0 else t["text_primary"],
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Text(_fmt_stock(min_stock), size=12, width=60, text_align=ft.TextAlign.CENTER, color=t["text_secondary"]),
                    ft.Text(_fmt(precio_venta_unit), size=12, width=80, text_align=ft.TextAlign.RIGHT, weight=ft.FontWeight.W_500),
                    ft.Text(_fmt(costo_unit), size=12, width=80, text_align=ft.TextAlign.RIGHT, color=t["text_secondary"]),
                    ft.Container(_stock_badge(total_stock, min_stock), width=80, alignment=ft.Alignment(0, 0)),
                    ft.Row(
                        [
                            ft.IconButton(ft.icons.ADD_CIRCLE_OUTLINE, icon_size=16, tooltip="Ajustar",
                                          icon_color=t["accent"],
                                          on_click=lambda e, p=producto: _open_ajuste(p),
                                          style=ft.ButtonStyle(padding=ft.padding.all(4))),
                            ft.IconButton(ft.icons.EDIT_OUTLINED, icon_size=16, tooltip="Editar",
                                          on_click=lambda e, p=producto: _open_form(producto=p),
                                          style=ft.ButtonStyle(padding=ft.padding.all(4))),
                            ft.IconButton(ft.icons.DELETE_OUTLINE, icon_size=16, tooltip="Eliminar",
                                          icon_color=ft.colors.ERROR,
                                          on_click=lambda e, p=producto: _confirm_delete(p),
                                          style=ft.ButtonStyle(padding=ft.padding.all(4))),
                        ],
                        spacing=0, width=96,
                    ),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(10, 14),
            bgcolor=t["bg_row_even"] if zebra else t["bg_row_odd"],
            border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
        )

        return ft.Column([header, variant_details], spacing=0)

    def _refresh_table():
        table_col.controls.clear()
        table_col.controls.append(
            ft.Container(
                ft.Row(
                    [
                        ft.Text("Articulo", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], expand=True),
                        ft.Text("Costo total", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=90, text_align=ft.TextAlign.RIGHT),
                        ft.Text("Stock", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=70, text_align=ft.TextAlign.CENTER),
                        ft.Text("Min.", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=60, text_align=ft.TextAlign.CENTER),
                        ft.Text("Precio venta", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=80, text_align=ft.TextAlign.RIGHT),
                        ft.Text("Compra/Fabri", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=80, text_align=ft.TextAlign.RIGHT),
                        ft.Text("Estado", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=80, text_align=ft.TextAlign.CENTER),
                        ft.Container(width=96),
                    ],
                    spacing=6,
                ),
                padding=ft.padding.symmetric(10, 14),
                bgcolor=t["bg_header"],
                border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border"])),
            )
        )

        productos = get_productos()
        query = search_filter["value"].lower()
        if query:
            productos = [p for p in productos if query in p.get("detalle", "").lower()]

        if not productos:
            table_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.INVENTORY_2_OUTLINED, size=42, color=t["text_hint"]),
                            ft.Text("No hay productos registrados.", size=15, weight=ft.FontWeight.W_500),
                        ],
                        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0), padding=ft.padding.all(40), expand=True,
                )
            )
        else:
            for i, p in enumerate(productos):
                table_col.controls.append(_build_row(p, i % 2 == 0))

        if table_col.parent:
            table_col.update()

    tf_search.on_change = lambda e: (search_filter.update({"value": (e.control.value or "").strip()}), _refresh_table())
    _refresh_table()

    main_container = ft.Container(expand=True)
    _render()

    main_container.refresh_data = _refresh_table
    main_container.open_new_form = lambda: _open_form()
    return main_container
