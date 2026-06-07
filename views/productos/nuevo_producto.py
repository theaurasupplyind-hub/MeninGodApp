import logging
log = logging.getLogger("mvp10")

import flet as ft

from db.database import (
    get_colores, save_color,
    get_tallas, save_talla,
    get_variantes_by_producto, save_variante,
    save_producto, update_producto,
    desactivar_variante,
)


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


def build_form(page, t, producto=None, on_saved=None, on_cancel=None):
    editing_id = {"value": None}

    def _show_message(text: str, color=None):
        sb = ft.SnackBar(
            ft.Text(text, color=ft.colors.WHITE),
            bgcolor=color or t["accent"],
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
            hint_style=ft.TextStyle(color=t["text_secondary"]),
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

    # Default fields for Propio (shared across all variants)
    tf_fabri_default = ft.TextField(
        value="", hint_text="Precio fabricacion (default)",
        border_radius=7, height=38, text_size=13,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=t["border"], focused_border_color=t["accent"],
        color=t["text_primary"], bgcolor=t["bg_input"],
    )
    tf_stock_default = ft.TextField(
        value="0", hint_text="Stock inicial (default)",
        border_radius=7, height=38, text_size=13,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=t["border"], focused_border_color=t["accent"],
        color=t["text_primary"], bgcolor=t["bg_input"],
    )
    default_fields_row = ft.Row([
        ft.Column([
            ft.Text("Precio fabri. (default)", size=12, color=t["text_secondary"]),
            tf_fabri_default,
        ]),
        ft.Column([
            ft.Text("Stock inicial (default)", size=12, color=t["text_secondary"]),
            tf_stock_default,
        ]),
    ], spacing=16, visible=False)

    variantes_rows: list[dict] = []
    variantes_col = ft.ListView(spacing=4, expand=True)

    dd_origen = ft.Dropdown(
        hint_text="Origen",
        options=[
            ft.dropdown.Option("proveedor", "Proveedor (stock via compras)"),
            ft.dropdown.Option("propio", "Propio (fabrica uds.)"),
        ],
        value="proveedor",
        border_radius=7, height=38, text_size=13,
        content_padding=ft.padding.symmetric(4, 10),
        border_color=t["border"],
        focused_border_color=t["accent"],
        color=t["text_primary"],
        bgcolor=t["bg_input"],
        hint_style=ft.TextStyle(color=t["text_secondary"]),
    )

    def _on_origen_change(e=None):
        es_propio = dd_origen.value == "propio"
        default_fields_row.visible = es_propio
        page.update()

    dd_origen.on_change = _on_origen_change

    def _build_variante_row(idx: int, data: dict | None = None):
        d = data or {}
        row_dd_color = _dd("Color")
        row_dd_talla = _dd("Talla")
        row_dd_color.width = 120
        row_dd_color.expand = False
        row_dd_talla.width = 100
        row_dd_talla.expand = False
        row_tf_precio = _tf("Precio venta", keyboard_type=ft.KeyboardType.NUMBER)

        colores = get_colores()
        tallas = get_tallas()
        row_dd_color.options = [ft.dropdown.Option("", "--")] + [
            ft.dropdown.Option(str(c["id"]), c["nombre"]) for c in colores
        ]
        row_dd_talla.options = [ft.dropdown.Option("", "--")] + [
            ft.dropdown.Option(str(ta["id"]), ta["nombre"]) for ta in tallas
        ]

        if d.get("color_id"):
            row_dd_color.value = str(d["color_id"])
        if d.get("talla_id"):
            row_dd_talla.value = str(d["talla_id"])
        if d.get("precio_unitario"):
            row_tf_precio.value = str(int(d["precio_unitario"]))

        row_data = {"color": row_dd_color, "talla": row_dd_talla,
                    "precio": row_tf_precio}

        def _remove(e):
            variantes_rows.remove(row_data)
            variantes_col.controls.remove(row_data["container"])
            _renumber_variantes()
            if variantes_col.page:
                variantes_col.update()

        controls = [
            ft.Text(str(idx), size=12, color=t["text_secondary"], width=20),
            row_dd_color, row_dd_talla, row_tf_precio,
            ft.IconButton(ft.icons.CLOSE, icon_size=14,
                          icon_color=ft.colors.ERROR,
                          on_click=_remove,
                          style=ft.ButtonStyle(padding=ft.padding.all(2))),
        ]

        row = ft.Container(
            content=ft.Row(controls, spacing=4),
            padding=ft.padding.symmetric(2, 0),
        )
        row_data["container"] = row
        return row_data

    def _renumber_variantes():
        for i, v in enumerate(variantes_rows, start=1):
            v["container"].content.controls[0].value = str(i)

    def _add_variante_row(e=None, data=None):
        idx = len(variantes_rows) + 1
        row_data = _build_variante_row(idx, data)
        variantes_rows.append(row_data)
        variantes_col.controls.append(row_data["container"])
        if variantes_col.page:
            variantes_col.update()

    def _generar_combinaciones(e):
        tf_cant_colores = ft.TextField(
            value="0", hint_text="0",
            border_radius=7, height=38, text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=t["border"], focused_border_color=t["accent"],
            color=t["text_primary"], bgcolor=t["bg_input"],
            width=90,
        )
        tf_cant_talles = ft.TextField(
            value="0", hint_text="0",
            border_radius=7, height=38, text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=t["border"], focused_border_color=t["accent"],
            color=t["text_primary"], bgcolor=t["bg_input"],
            width=90,
        )

        color_name_fields: list[ft.TextField] = []
        talla_name_fields: list[ft.TextField] = []
        colores_col = ft.Column(spacing=4)
        tallas_col = ft.Column(spacing=4)

        tf_precio_default = ft.TextField(
            value="", hint_text="Precio venta default",
            border_radius=7, height=38, text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=t["border"], focused_border_color=t["accent"],
            color=t["text_primary"], bgcolor=t["bg_input"],
        )

        def _rebuild(e=None):
            nonlocal color_name_fields, talla_name_fields
            try:
                c_count = max(0, int(tf_cant_colores.value or "0"))
            except ValueError:
                c_count = 0
            try:
                t_count = max(0, int(tf_cant_talles.value or "0"))
            except ValueError:
                t_count = 0

            while len(color_name_fields) < c_count:
                idx = len(color_name_fields) + 1
                f = ft.TextField(
                    hint_text=f"Color {idx}",
                    border_radius=7, height=38, text_size=13,
                    border_color=t["border"], focused_border_color=t["accent"],
                    color=t["text_primary"], bgcolor=t["bg_input"],
                )
                color_name_fields.append(f)
            while len(color_name_fields) > c_count:
                color_name_fields.pop()

            while len(talla_name_fields) < t_count:
                idx = len(talla_name_fields) + 1
                f = ft.TextField(
                    hint_text=f"Talle {idx}",
                    border_radius=7, height=38, text_size=13,
                    border_color=t["border"], focused_border_color=t["accent"],
                    color=t["text_primary"], bgcolor=t["bg_input"],
                )
                talla_name_fields.append(f)
            while len(talla_name_fields) > t_count:
                talla_name_fields.pop()

            colores_col.controls = list(color_name_fields)
            tallas_col.controls = list(talla_name_fields)
            if dlg_combinar.page:
                dlg_combinar.update()

        tf_cant_colores.on_change = lambda e: _rebuild()
        tf_cant_talles.on_change = lambda e: _rebuild()

        def _do_generar(ev):
            color_names = [f.value.strip() or f.hint_text for f in color_name_fields]
            talla_names = [f.value.strip() or f.hint_text for f in talla_name_fields]
            color_names = [n for n in color_names if n]
            talla_names = [n for n in talla_names if n]

            if not color_names or not talla_names:
                _show_message("Completa los nombres de colores y talles.", t["accent"])
                return

            precio_default = _parse_input_number(tf_precio_default.value or "0")
            if precio_default <= 0:
                _show_message("El precio venta debe ser mayor a 0.", t["accent"])
                return

            color_ids = [save_color(n) for n in color_names]
            talla_ids = [save_talla(n) for n in talla_names]

            for cid in color_ids:
                for tid in talla_ids:
                    _add_variante_row(data={
                        "color_id": cid,
                        "talla_id": tid,
                        "precio_unitario": precio_default,
                    })
            page.close(dlg_combinar)

        dlg_combinar = ft.AlertDialog(
            modal=True,
            title=ft.Text("Generar combinaciones", size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Column([ft.Text("Cant. colores", size=12, color=t["text_secondary"]),
                                    tf_cant_colores]),
                        ft.Column([ft.Text("Cant. talles", size=12, color=t["text_secondary"]),
                                    tf_cant_talles]),
                    ], spacing=16),
                    ft.Divider(height=8, color=t["border_light"]),
                    ft.Text("Nombres de colores", size=12, weight=ft.FontWeight.W_600,
                            color=t["text_secondary"]),
                    colores_col,
                    ft.Divider(height=8, color=t["border_light"]),
                    ft.Text("Nombres de talles", size=12, weight=ft.FontWeight.W_600,
                            color=t["text_secondary"]),
                    tallas_col,
                    ft.Divider(height=8, color=t["border_light"]),
                    ft.Text("Precio venta default *", size=12, color=t["text_secondary"]),
                    tf_precio_default,
                ], spacing=4, scroll=ft.ScrollMode.AUTO),
                width=400,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg_combinar)),
                ft.ElevatedButton("Generar", bgcolor=t["accent"], color=t["accent_text"],
                                  on_click=_do_generar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg_combinar)

    def _handle_save():
        detalle = (tf_detalle.value or "").strip()
        if not detalle:
            _show_message("El nombre del articulo es obligatorio.", t["accent"])
            return

        if not variantes_rows:
            _show_message("Agrega al menos una variante.", t["accent"])
            return

        origen = dd_origen.value or "proveedor"
        es_propio = origen == "propio"

        for v in variantes_rows:
            precio_venta = _parse_input_number(v["precio"].value or "0")
            if precio_venta <= 0:
                _show_message("El precio venta debe ser mayor a 0 en todas las variantes.", t["accent"])
                return

        if editing_id["value"]:
            update_producto(editing_id["value"], {
                "detalle": detalle,
                "precio_unitario": 0,
                "stock_actual": 0,
                "stock_minimo": 0,
                "tipo_origen": origen,
            })
            prod_id = editing_id["value"]
            existing = get_variantes_by_producto(prod_id)
            for v in existing:
                desactivar_variante(v["id"])
            msg = f"Articulo '{detalle}' actualizado."
        else:
            prod_id = save_producto({
                "detalle": detalle,
                "precio_unitario": 0,
                "stock_actual": 0,
                "stock_minimo": 0,
                "tipo_origen": origen,
            })
            msg = f"Articulo '{detalle}' creado."

        fabri_val = _parse_input_number(tf_fabri_default.value or "0") if es_propio else 0
        stock_val = _parse_input_number(tf_stock_default.value or "0") if es_propio else 0

        for v in variantes_rows:
            color_id = int(v["color"].value) if v["color"].value and v["color"].value != "" else None
            talla_id = int(v["talla"].value) if v["talla"].value and v["talla"].value != "" else None
            precio = _parse_input_number(v["precio"].value or "0")

            save_variante(prod_id, {
                "color_id": color_id,
                "talla_id": talla_id,
                "precio_unitario": precio,
                "stock_actual": stock_val,
                "stock_minimo": 0,
                "precio_fabricacion": fabri_val,
            })

        _show_message(msg, ft.colors.GREEN_700)
        if on_saved:
            on_saved()

    # ── Populate if editing ──
    if producto:
        editing_id["value"] = producto["id"]
        tf_detalle.value = producto.get("detalle", "")
        dd_origen.value = producto.get("tipo_origen", "proveedor")
        variantes = get_variantes_by_producto(producto["id"])
        for v in variantes:
            _add_variante_row(data=v)
        if variantes:
            first = variantes[0]
            if first.get("precio_fabricacion"):
                tf_fabri_default.value = _fmt_stock(first["precio_fabricacion"])
            if first.get("stock_actual"):
                tf_stock_default.value = _fmt_stock(first["stock_actual"])

    if not variantes_rows:
        _add_variante_row()

    # FIX 1: llamada explícita para sincronizar estado visual inicial
    _on_origen_change()

    # ── Build view ──
    return ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.Text("Editar producto" if producto else "Nuevo producto",
                            size=18, weight=ft.FontWeight.W_500, expand=True),
                    ft.TextButton("<-- Volver al listado",
                                  on_click=lambda e: on_cancel() if on_cancel else None,
                                  style=ft.ButtonStyle(color=t["text_secondary"])),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1, color=t["border_light"]),
                ft.Row([
                    ft.Column([
                        ft.Text("Nombre del articulo *", size=12, color=t["text_secondary"]),
                        tf_detalle,
                    ], expand=True),
                    ft.Column([
                        ft.Text("Origen", size=12, color=t["text_secondary"]),
                        dd_origen,
                    ]),
                ], spacing=16),
                default_fields_row,
                ft.Divider(height=1, color=t["border_light"]),
                ft.Row(
                    [
                        ft.Text("Variantes", size=12, weight=ft.FontWeight.W_600,
                                color=t["text_secondary"], expand=True),
                        ft.TextButton("+ Agregar", on_click=_add_variante_row,
                                      style=ft.ButtonStyle(padding=ft.padding.symmetric(4, 8))),
                        ft.TextButton("Generar combinaciones", on_click=_generar_combinaciones,
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
                        ft.TextButton("Cancelar",
                                      on_click=lambda e: on_cancel() if on_cancel else None),
                        ft.ElevatedButton(
                            "Guardar",
                            bgcolor=t["accent"],
                            color=t["accent_text"],
                            on_click=lambda e: _handle_save(),
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