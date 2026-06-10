import logging
log = logging.getLogger("mvp10")
from datetime import datetime

import flet as ft
from theme import get_theme
from views.productos.nuevo_producto import build_form

from db.database import (
    get_productos, delete_producto,
    ajustar_stock_variante, get_stock_bajo,
    get_variantes_by_producto, save_compra,
    registrar_movimiento_stock, get_movimientos_stock,
    get_movimientos_by_producto, get_curvas_by_producto,
)
from services.autocomplete_service import search_proveedores


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





from views.flow_guide import HelpButton




def StockView(page: ft.Page, on_nueva_compra=None):
    t = get_theme(page)
    MOV_MAX = 100
    _show_all: dict[str, bool] = {"value": False}
    search_filter: dict[str, str] = {"value": ""}
    form_mode: dict[str, str | None] = {"value": None}

    def _close_dlg(dlg):
        page.close(dlg)

    def _show_message(text: str, color=t["accent"]):
        sb = ft.SnackBar(
            ft.Text(text, color=ft.Colors.WHITE),
            bgcolor=color,
            duration=3200,
        )
        page.open(sb)

    def _tf(hint, width=None, keyboard_type=None):
        return ft.TextField(
            hint_text=hint,
            border_radius=7,
            height=42,
            text_size=14,
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

    # ── Column widths (shared between header and rows) ──
    COL_W = type("ColWidths", (), {
        "chevron": 22, "stock": 70, "precio": 85,
        "fab_comp": 80, "costo_total": 90, "acciones": 58,
    })()

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
                                        ft.Text("  |  ".join(subtitle_parts), size=14,
                                                color=t["accent"] if stock_bajo_count else t["text_secondary"]),
                                    ],
                                    spacing=2, expand=True,
                                ),
                                help_btn,
                                ft.ElevatedButton(
                                    "Nuevo producto", icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=_open_form,
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

    def _open_ajuste_simple(producto: dict):
        variantes = get_variantes_by_producto(producto["id"])
        if not variantes:
            _show_message("Este producto no tiene variantes.", t["accent"])
            return

        def _make_toggle():
            state = {"add": True}
            btn = ft.IconButton(
                icon=ft.Icons.ADD, icon_size=18,
                icon_color=ft.Colors.GREEN_700,
                tooltip="Agregar stock",
                style=ft.ButtonStyle(padding=ft.padding.all(2)),
            )
            def _toggle(e):
                state["add"] = not state["add"]
                if state["add"]:
                    btn.icon = ft.Icons.ADD
                    btn.icon_color = ft.Colors.GREEN_700
                    btn.tooltip = "Agregar stock"
                else:
                    btn.icon = ft.Icons.REMOVE
                    btn.icon_color = ft.Colors.RED_700
                    btn.tooltip = "Reducir stock"
                if btn.page:
                    try: btn.update()
                    except Exception: pass
            btn.on_click = _toggle
            return btn, state

        variant_rows = []
        for v in variantes:
            vname = f"{v.get('color') or 'Sin color'} — Talle {v.get('talla') or '-'}"
            stock_actual = float(v.get("stock_actual", 0) or 0)
            tf_cant = ft.TextField(
                hint_text="0", width=70, height=34, text_size=13,
                content_padding=ft.padding.symmetric(6, 6),
                border_radius=6,
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.CENTER,
                border_color=t["border"], focused_border_color=t["accent"],
                bgcolor=t["bg_input"], color=t["text_primary"],
            )
            toggle_btn, toggle_state = _make_toggle()
            row = ft.Row([
                ft.Text(vname, size=13, expand=True, color=t["text_primary"]),
                ft.Text(_fmt_stock(stock_actual), size=13, width=50,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.ERROR if stock_actual <= 0 else t["text_primary"]),
                toggle_btn,
                tf_cant,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            row._v = v
            row._tf = tf_cant
            row._toggle = toggle_state
            variant_rows.append(row)

        def _do_ajuste(ev, d):
            from services.auth_service import AuthService
            applied = 0
            for row in variant_rows:
                raw = (row._tf.value or "").strip()
                if not raw:
                    continue
                try:
                    cantidad = _parse_input_number(raw)
                except ValueError:
                    continue
                if cantidad == 0:
                    continue
                delta = cantidad if row._toggle["add"] else -cantidad
                ajustar_stock_variante(row._v["id"], delta)
                registrar_movimiento_stock(
                    row._v["id"], "ajuste_manual", None, delta, None,
                )
                applied += 1
            if applied == 0:
                _show_message("No se ingresó ninguna cantidad.", t["accent"])
                return
            AuthService().track("ajuste_stock", producto["detalle"], f"Ajuste de stock en '{producto['detalle']}' — {applied} variante(s)")
            _show_message(
                f"Stock de '{producto['detalle']}' ajustado en {applied} variante(s).",
                ft.Colors.GREEN_700,
            )
            page.close(d)
            _refresh_table()

        header = ft.Row([
            ft.Text("Variante", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], expand=True),
            ft.Text("Stock", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], width=50,
                    text_align=ft.TextAlign.CENTER),
            ft.Text("±", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], width=30,
                    text_align=ft.TextAlign.CENTER),
            ft.Text("Cantidad", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], width=70,
                    text_align=ft.TextAlign.CENTER),
        ], spacing=6)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text(f"Ajuste de stock — {producto.get('detalle', '')}",
                          size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column(
                    [header, ft.Divider(height=1, color=t["border_light"])] + variant_rows,
                    spacing=6, tight=True,
                ),
                width=480,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: _close_dlg(dlg)),
                ft.ElevatedButton(
                    "Aplicar", bgcolor=t["accent"], color=t["accent_text"],
                    on_click=lambda ev: _do_ajuste(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _open_add_stock(producto: dict):
        variantes = get_variantes_by_producto(producto["id"])
        if not variantes:
            _show_message("Este producto no tiene variantes.", t["accent"])
            return

        proveedor_state = {"id": None, "nombre": ""}

        tf_proveedor = ft.TextField(
            hint_text="Nombre del proveedor...",
            border_radius=7, height=42, text_size=14, expand=True,
            content_padding=ft.padding.symmetric(8, 10),
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            on_change=lambda e: _search_proveedor(e.control.value or ""),
        )

        proveedor_results = ft.Column(spacing=0, visible=False)

        def _search_proveedor(query):
            proveedor_results.controls.clear()
            if len(query.strip()) < 2:
                proveedor_results.visible = False
                if proveedor_results.page:
                    try: proveedor_results.update()
                    except Exception: pass
                return
            results = search_proveedores(query, limit=5)
            for p in results:
                item = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.BUSINESS_CENTER, size=14, color=t["text_secondary"]),
                        ft.Column([
                            ft.Text(p.get("nombre", ""), size=13, color=t["text_primary"]),
                            ft.Text(p.get("telefono", ""), size=10, color=t["text_hint"]) if p.get("telefono") else ft.Text(""),
                        ], spacing=0, expand=True),
                    ], spacing=8),
                    padding=ft.padding.symmetric(8, 6),
                    border_radius=4,
                    on_click=lambda e, pv=p, q=query: _select_proveedor(pv),
                    on_hover=lambda e: setattr(e.control, "bgcolor", t["bg_input"] if e.data == "true" else ft.Colors.TRANSPARENT),
                )
                proveedor_results.controls.append(item)
            if not results:
                proveedor_results.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.ADD, size=14, color=t["accent"]),
                            ft.Text(f'Crear "{query}" como nuevo proveedor', size=13, color=t["accent"]),
                        ], spacing=6),
                        padding=ft.padding.symmetric(8, 6),
                        border_radius=4,
                        on_click=lambda e, q=query: _select_proveedor({"nombre": q}),
                    )
                )
            proveedor_results.visible = True
            if proveedor_results.page:
                try: proveedor_results.update()
                except Exception: pass

        def _select_proveedor(pv):
            nombre = pv.get("nombre", "")
            proveedor_state["id"] = pv.get("id")
            proveedor_state["nombre"] = nombre
            tf_proveedor.value = nombre
            proveedor_results.visible = False
            if tf_proveedor.page:
                try: tf_proveedor.update()
                except Exception: pass
            if proveedor_results.page:
                try: proveedor_results.update()
                except Exception: pass

        tf_precio = ft.TextField(
            hint_text="Precio compra unitario...",
            width=180, height=42, text_size=14,
            content_padding=ft.padding.symmetric(8, 10),
            border_radius=7,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
        )

        variant_rows = []
        for v in variantes:
            vname = f"{v.get('color') or 'Sin color'} — Talle {v.get('talla') or '-'}"
            stock_actual = float(v.get("stock_actual", 0) or 0)
            tf_cant = ft.TextField(
                hint_text="0", width=70, height=34, text_size=13,
                content_padding=ft.padding.symmetric(6, 6),
                border_radius=6,
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.CENTER,
                border_color=t["border"], focused_border_color=t["accent"],
                bgcolor=t["bg_input"], color=t["text_primary"],
            )
            row = ft.Row([
                ft.Text(vname, size=13, expand=True, color=t["text_primary"]),
                ft.Text(_fmt_stock(stock_actual), size=13, width=50,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.ERROR if stock_actual <= 0 else t["text_primary"]),
                tf_cant,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            row._v = v
            row._tf = tf_cant
            variant_rows.append(row)

        def _do_add(ev, d):
            proveedor = (tf_proveedor.value or "").strip()
            if not proveedor:
                _show_message("Ingresá un proveedor.", ft.Colors.ERROR)
                return
            raw_precio = (tf_precio.value or "").strip()
            if not raw_precio:
                _show_message("Ingresá el precio de compra.", ft.Colors.ERROR)
                return
            try:
                precio = _parse_input_number(raw_precio)
            except ValueError:
                _show_message("Precio inválido.", ft.Colors.ERROR)
                return
            if precio <= 0:
                _show_message("El precio debe ser mayor a 0.", ft.Colors.ERROR)
                return
            items = []
            for row in variant_rows:
                raw = (row._tf.value or "").strip()
                if not raw:
                    continue
                try:
                    cant = _parse_input_number(raw)
                except ValueError:
                    continue
                if cant <= 0:
                    continue
                v = row._v
                items.append({
                    "detalle": f"{producto.get('detalle', '')} {v.get('color', '')} {v.get('talla', '')}".strip(),
                    "cantidad": cant,
                    "precio_unitario": precio,
                    "total": cant * precio,
                    "variante_id": v["id"],
                })
            if not items:
                _show_message("Ingresá cantidad en al menos una variante.", ft.Colors.ERROR)
                return
            total = sum(it["total"] for it in items)
            data = {
                "fecha": datetime.now().strftime("%d/%m/%Y"),
                "proveedor_nombre": proveedor,
                "total": total,
                "notas": "Aumento rápido desde stock",
            }
            try:
                numero = save_compra(data, items)
                _show_message(f"Stock aumentado — {numero} ({len(items)} variante(s))", ft.Colors.GREEN_700)
                page.close(d)
                _refresh_table()
            except Exception as ex:
                log.error(f"Error guardando compra rápida: {ex}", exc_info=True)
                _show_message(f"Error: {ex}", ft.Colors.ERROR)

        header = ft.Row([
            ft.Text("Variante", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], expand=True),
            ft.Text("Stock", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], width=50,
                    text_align=ft.TextAlign.CENTER),
            ft.Text("Cantidad", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], width=70,
                    text_align=ft.TextAlign.CENTER),
        ], spacing=6)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text(f"Aumentar stock — {producto.get('detalle', '')}",
                          size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.BUSINESS_CENTER, size=18, color=t["text_secondary"]),
                        tf_proveedor,
                    ], spacing=6),
                    proveedor_results,
                    ft.Row([
                        ft.Text("$", size=14, color=t["text_secondary"]),
                        tf_precio,
                    ], spacing=6),
                    ft.Divider(height=1, color=t["border_light"]),
                    header,
                    ft.Divider(height=1, color=t["border_light"]),
                    *variant_rows,
                ], spacing=6, tight=True, scroll=ft.ScrollMode.AUTO),
                width=520,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: _close_dlg(dlg)),
                ft.ElevatedButton(
                    "Guardar y aumentar stock",
                    bgcolor=t["accent"], color=t["accent_text"],
                    on_click=lambda ev: _do_add(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _confirm_delete(producto):
        detalle = producto.get("detalle", "")
        prod_id = producto["id"]

        movs = get_movimientos_by_producto(prod_id)
        curvas = get_curvas_by_producto(prod_id)
        razones = []
        if movs:
            razones.append(f"Tiene {len(movs)} movimiento(s) de stock registrado(s).")
        if curvas:
            razones.append(f"Tiene {len(curvas)} curva(s) pendiente(s).")

        if razones:
            razones.append("")
            razones.append("Eliminá los movimientos y curvas asociadas antes de eliminar este producto.")
            dlg = ft.AlertDialog(
                modal=True,
                bgcolor=t["bg_card"],
                title=ft.Text("No se puede eliminar", color=ft.Colors.ERROR, size=16, weight=ft.FontWeight.W_600),
                content=ft.Column([
                    ft.Text(f"No se puede eliminar '{detalle}'.", size=14),
                    ft.Container(height=8),
                    *[ft.Text(r, size=12, color=t["text_secondary"]) for r in razones],
                ], spacing=4, tight=True),
                actions=[
                    ft.TextButton("Cerrar", on_click=lambda ev: page.close(dlg)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)
            return

        def _do_delete(ev, d):
            try:
                delete_producto(prod_id)
                _show_message(f"Producto '{detalle}' eliminado.", ft.Colors.RED_700)
                page.close(d)
                _refresh_table()
            except Exception as ex:
                _show_message(f"Error al eliminar: {ex}", ft.Colors.ERROR)
                page.close(d)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text("Eliminar producto"),
            content=ft.Text(f"¿Seguro que querés eliminar '{detalle}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                ft.ElevatedButton(
                    "Eliminar",
                    bgcolor=ft.Colors.ERROR,
                    color=t["accent_text"],
                    on_click=lambda ev: _do_delete(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _open_reduce_stock(producto: dict):
        variantes = get_variantes_by_producto(producto["id"])
        if not variantes:
            _show_message("Este producto no tiene variantes.", t["accent"])
            return

        tf_motivo = ft.TextField(
            hint_text="Motivo de la reducción...",
            expand=True, height=36, text_size=12,
            border_radius=6,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
        )

        warning = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=16, color=ft.Colors.AMBER_400),
                ft.Text(
                    "Reducir stock sin una compra asociada puede desbalancear "
                    "la deuda con el proveedor. Si este stock se compró, "
                    "considerá registrar una devolución en Compras.",
                    size=11, color=ft.Colors.AMBER_400, wrap=True, expand=True,
                ),
            ], spacing=6),
            padding=ft.padding.symmetric(8, 8),
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.AMBER_400),
        )

        variant_rows = []
        for v in variantes:
            vname = f"{v.get('color') or 'Sin color'} — Talle {v.get('talla') or '-'}"
            stock_actual = float(v.get("stock_actual", 0) or 0)
            tf_cant = ft.TextField(
                hint_text="0", width=70, height=34, text_size=13,
                content_padding=ft.padding.symmetric(6, 6),
                border_radius=6,
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.CENTER,
                border_color=t["border"], focused_border_color=t["accent"],
                bgcolor=t["bg_input"], color=t["text_primary"],
            )
            row = ft.Row([
                ft.Text(vname, size=13, expand=True, color=t["text_primary"]),
                ft.Text(_fmt_stock(stock_actual), size=13, width=50,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.ERROR if stock_actual <= 0 else t["text_primary"]),
                tf_cant,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            row._v = v
            row._tf = tf_cant
            variant_rows.append(row)

        def _do_reduce(ev, d):
            from services.auth_service import AuthService
            motivo = (tf_motivo.value or "").strip()
            applied = 0
            for row in variant_rows:
                raw = (row._tf.value or "").strip()
                if not raw:
                    continue
                try:
                    cant = _parse_input_number(raw)
                except ValueError:
                    continue
                if cant <= 0:
                    continue
                v = row._v
                actual = float(v.get("stock_actual", 0) or 0)
                if cant > actual:
                    _show_message(
                        f"Stock insuficiente en {v.get('color','')} {v.get('talla','')}: "
                        f"tenés {int(actual)}, querés reducir {int(cant)}.",
                        ft.Colors.ERROR,
                    )
                    return
                ajustar_stock_variante(v["id"], -cant)
                registrar_movimiento_stock(v["id"], "reduccion_manual", None, -cant, motivo or None)
                applied += 1
            if applied == 0:
                _show_message("No se ingresó ninguna cantidad.", t["accent"])
                return
            AuthService().track("reduccion_stock", producto["detalle"], f"Reducción de stock en '{producto['detalle']}' — {applied} variante(s) — {motivo or 'sin motivo'}")
            _show_message(
                f"Stock reducido en {applied} variante(s).",
                ft.Colors.GREEN_700,
            )
            page.close(d)
            _refresh_table()

        header = ft.Row([
            ft.Text("Variante", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], expand=True),
            ft.Text("Stock", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], width=50,
                    text_align=ft.TextAlign.CENTER),
            ft.Text("Reducir", size=12, weight=ft.FontWeight.W_500,
                    color=t["text_secondary"], width=70,
                    text_align=ft.TextAlign.CENTER),
        ], spacing=6)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text(f"Reducir stock — {producto.get('detalle', '')}",
                          size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column([
                    warning,
                    ft.Row([
                        ft.Text("Motivo:", size=12, color=t["text_secondary"]),
                        tf_motivo,
                    ], spacing=6),
                    ft.Divider(height=1, color=t["border_light"]),
                    header,
                    ft.Divider(height=1, color=t["border_light"]),
                    *variant_rows,
                ], spacing=6, tight=True, scroll=ft.ScrollMode.AUTO),
                width=520,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: _close_dlg(dlg)),
                ft.ElevatedButton(
                    "Reducir stock",
                    bgcolor=ft.Colors.ERROR, color=ft.Colors.WHITE,
                    on_click=lambda ev: _do_reduce(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _open_historial(producto: dict):
        movimientos = get_movimientos_stock(producto_id=producto["id"])
        if not movimientos:
            _show_message("No hay movimientos registrados para este producto.", t["text_secondary"])
            return

        tipo_labels = {
            "compra": ("Compra", ft.Colors.GREEN_700),
            "facturacion": ("Facturación", ft.Colors.RED_700),
            "reduccion_manual": ("Reducción", ft.Colors.AMBER_400),
        }

        rows = []
        for m in movimientos:
            tipo_text, tipo_color = tipo_labels.get(m.get("tipo", ""), (m.get("tipo", ""), t["text_secondary"]))
            cant = float(m.get("cantidad", 0) or 0)
            signo = "+" if cant > 0 else ""
            stock_res = m.get("stock_resultante")
            stock_text = _fmt_stock(stock_res) if stock_res is not None else "-"
            motivo = m.get("motivo") or ""
            rows.append(ft.Row([
                ft.Text(m.get("created_at", "")[:16], size=11, color=t["text_hint"], width=110),
                ft.Text(tipo_text, size=11, color=tipo_color, width=85),
                ft.Text(m.get("referencia", "-"), size=11, color=t["text_secondary"], width=75),
                ft.Text(f"{signo}{int(cant)}", size=12, weight=ft.FontWeight.W_500,
                        color=ft.Colors.GREEN_700 if cant > 0 else ft.Colors.RED_700, width=50,
                        text_align=ft.TextAlign.RIGHT),
                ft.Text(stock_text, size=12, width=50, text_align=ft.TextAlign.CENTER, color=t["text_primary"]),
                ft.Text(motivo[:30] if motivo else "", size=10, color=t["text_hint"], expand=True),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text(f" Historial — {producto.get('detalle', '')}",
                          size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Fecha", size=11, weight=ft.FontWeight.W_500, color=t["text_hint"], width=110),
                        ft.Text("Tipo", size=11, weight=ft.FontWeight.W_500, color=t["text_hint"], width=85),
                        ft.Text("Ref", size=11, weight=ft.FontWeight.W_500, color=t["text_hint"], width=75),
                        ft.Text("Cant", size=11, weight=ft.FontWeight.W_500, color=t["text_hint"],
                                width=50, text_align=ft.TextAlign.RIGHT),
                        ft.Text("Stock", size=11, weight=ft.FontWeight.W_500, color=t["text_hint"],
                                width=50, text_align=ft.TextAlign.CENTER),
                        ft.Text("Motivo", size=11, weight=ft.FontWeight.W_500, color=t["text_hint"], expand=True),
                    ], spacing=4),
                    ft.Divider(height=1, color=t["border_light"]),
                    *rows[:30],
                    ft.Text(f"{len(movimientos)} movimientos totales", size=10,
                            color=t["text_hint"], visible=len(movimientos) > 30),
                ], spacing=4, scroll=ft.ScrollMode.AUTO),
                width=560,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda ev: _close_dlg(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _build_row(producto: dict, zebra: bool):
        variantes = get_variantes_by_producto(producto["id"])
        total_stock = sum(float(v.get("stock_actual", 0) or 0) for v in variantes)
        var_count = len(variantes)
        var_label = f" ({var_count} var)" if var_count > 1 else ""

        tipo_origen = producto.get("tipo_origen", "proveedor")
        cost_key = "precio_fabricacion" if tipo_origen == "propio" else "precio_compra"
        costo_total = sum(float(v.get(cost_key, 0) or 0) * float(v.get("stock_actual", 0) or 0) for v in variantes)

        if var_count > 1:
            precios_venta = [float(v.get("precio_unitario", 0) or 0) for v in variantes if float(v.get("precio_unitario", 0) or 0) > 0]
            precio_venta_unit = sum(precios_venta) / len(precios_venta) if precios_venta else 0
            costos = [float(v.get(cost_key, 0) or 0) for v in variantes if float(v.get(cost_key, 0) or 0) > 0]
            costo_unit = sum(costos) / len(costos) if costos else 0
        elif var_count == 1:
            v = variantes[0]
            precio_venta_unit = float(v.get("precio_unitario", 0) or 0)
            costo_unit = float(v.get(cost_key, 0) or 0)
        else:
            precio_venta_unit = 0
            costo_unit = 0

        origen_badge = ft.Container(
            ft.Text("Propio" if tipo_origen == "propio" else "Proveedor", size=11,
                    weight=ft.FontWeight.W_600, color=t["text_secondary"]),
            bgcolor=t["border_light"],
            border_radius=8, padding=ft.padding.symmetric(1, 6),
        )

        # ── Expand/collapse state ──
        expanded = {"value": False}
        variant_details = ft.Column(spacing=0, visible=False)

        has_variants = len(variantes) > 1

        if var_count == 1:
            v = variantes[0]
            color_part = v.get("color") or ""
            talle_part = f"Talle {v.get('talla')}" if v.get("talla") else ""
            parts = [producto["detalle"], color_part, talle_part]
            display_name = " ".join(p for p in parts if p)
        else:
            display_name = f"{producto['detalle']}{var_label}"

        def _toggle_product(e):
            expanded["value"] = not expanded["value"]
            variant_details.visible = expanded["value"]
            chevron_btn.icon = ft.Icons.KEYBOARD_ARROW_DOWN if expanded["value"] else ft.Icons.KEYBOARD_ARROW_RIGHT
            if variant_details.page:
                variant_details.update()

        chevron_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_ARROW_RIGHT, icon_size=18,
            on_click=_toggle_product,
            style=ft.ButtonStyle(padding=ft.padding.all(2)),
        )

        if has_variants:
            expand_control = ft.Container(
                chevron_btn,
                width=22, height=22,
                padding=ft.padding.all(2),
                alignment=ft.alignment.center,
            )
        else:
            expand_control = ft.Container(
                ft.Icon(ft.Icons.CIRCLE, size=6, color=t["accent"]),
                width=22, height=22,
                padding=ft.padding.all(2),
                alignment=ft.alignment.center,
            )

        # ── Group variants by color ──
        by_color: dict[str, list] = {}
        for v in variantes:
            by_color.setdefault(v.get("color") or "Sin color", []).append(v)

        variant_sections: list[ft.Control] = []
        for cname in sorted(by_color.keys()):
            cvars = by_color[cname]
            col_exp = {"value": False}
            col_chevron = ft.Icon(ft.Icons.KEYBOARD_ARROW_RIGHT, size=14, color=t["text_hint"])

            talla_rows = []
            for v in cvars:
                tname = v.get("talla") or "-"
                cost_val = v.get(cost_key, 0) or 0
                st = float(v.get("stock_actual", 0) or 0)
                talla_rows.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(width=28),
                            ft.Text(f"Talle {tname}", size=14, expand=True, color=t["text_primary"]),
                            ft.Text(_fmt_stock(st), size=14,
                                    width=COL_W.stock,
                                    text_align=ft.TextAlign.CENTER,
                                    color=ft.Colors.ERROR if st <= 0 else t["text_primary"]),
                            ft.Text(_fmt(v["precio_unitario"]), size=14,
                                    width=COL_W.precio,
                                    text_align=ft.TextAlign.RIGHT, color=t["text_primary"]),
                            ft.Text(_fmt(cost_val), size=14,
                                    width=COL_W.fab_comp,
                                    text_align=ft.TextAlign.RIGHT, color=t["text_secondary"]),
                            ft.Container(width=COL_W.costo_total),
                            ft.Container(width=COL_W.acciones),
                        ], spacing=6),
                        padding=ft.padding.symmetric(5, 28),
                    )
                )

            talla_container = ft.Column(talla_rows, spacing=1, visible=False)

            def _toggle_col(e, tc=talla_container, ce=col_exp, ch=col_chevron):
                ce["value"] = not ce["value"]
                tc.visible = ce["value"]
                ch.name = ft.Icons.KEYBOARD_ARROW_DOWN if ce["value"] else ft.Icons.KEYBOARD_ARROW_RIGHT
                if tc.page:
                    tc.update()

            variant_sections.append(
                ft.Column([
                    ft.Container(
                        content=ft.Row([
                            col_chevron,
                            ft.Container(width=14),
                            ft.Text(f"{cname} ({len(cvars)})", size=14, weight=ft.FontWeight.W_600,
                                    color=t["text_primary"], expand=True),
                            ft.Container(width=COL_W.stock),
                            ft.Container(width=COL_W.precio),
                            ft.Container(width=COL_W.fab_comp),
                            ft.Container(width=COL_W.costo_total),
                            ft.Container(width=COL_W.acciones),
                        ], spacing=6),
                        on_click=_toggle_col,
                        padding=ft.padding.symmetric(8, 14),
                        bgcolor=t["bg_header"],
                        border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
                    ),
                    talla_container,
                ], spacing=0)
            )

        variant_details.controls = variant_sections

        # ── Acciones ──
        is_propio = tipo_origen == "propio"
        btn_ajuste = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            icon_size=18,
            icon_color=t["accent"],
            tooltip="Ajustar stock" if is_propio else "Aumentar stock",
            on_click=lambda e, p=producto: _open_ajuste_simple(p) if is_propio else _open_add_stock(p),
            style=ft.ButtonStyle(padding=ft.padding.all(2)),
        )

        popup_items = [
            ft.PopupMenuItem(
                icon=ft.Icons.EDIT_OUTLINED,
                text="Editar producto",
                on_click=lambda e, p=producto: _open_form(producto=p),
            ),
        ]
        if not is_propio:
            popup_items.append(ft.PopupMenuItem(
                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                text="Reducir stock",
                on_click=lambda e, p=producto: _open_reduce_stock(p),
            ))
        popup_items.append(ft.PopupMenuItem(
            icon=ft.Icons.HISTORY,
            text="Historial de movimientos",
            on_click=lambda e, p=producto: _open_historial(p),
        ))
        popup_items.append(ft.PopupMenuItem())
        popup_items.append(ft.PopupMenuItem(
            icon=ft.Icons.DELETE_OUTLINE,
            text="Eliminar",
            on_click=lambda e, p=producto: _confirm_delete(p),
        ))

        popup = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_size=18,
            icon_color=t["text_secondary"],
            items=popup_items,
            style=ft.ButtonStyle(padding=ft.padding.all(2)),
        )

        header = ft.Container(
            content=ft.Row(
                [
                    expand_control,
                    ft.Column([
                        ft.Text(display_name, size=15,
                                weight=ft.FontWeight.W_500,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        origen_badge,
                    ], spacing=2, expand=True),
                    ft.Text(_fmt_stock(total_stock), size=15,
                            text_align=ft.TextAlign.CENTER,
                            color=ft.Colors.ERROR if total_stock <= 0 else t["text_primary"],
                            weight=ft.FontWeight.W_500,
                            width=COL_W.stock),
                    ft.Text(_fmt(precio_venta_unit), size=14,
                            text_align=ft.TextAlign.RIGHT, color=t["text_primary"],
                            width=COL_W.precio),
                    ft.Text(_fmt(costo_unit), size=14,
                            text_align=ft.TextAlign.RIGHT, color=t["text_secondary"],
                            width=COL_W.fab_comp),
                    ft.Text(_fmt(costo_total), size=14,
                            text_align=ft.TextAlign.RIGHT, color=t["text_secondary"],
                            width=COL_W.costo_total),
                    ft.Container(content=btn_ajuste, width=26),
                    ft.Container(content=popup, width=26),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(12, 14),
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
                        ft.Row([ft.Container(width=COL_W.chevron), ft.Text("Artículo", size=13, weight=ft.FontWeight.W_500, color=t["text_secondary"])], spacing=4),
                        ft.Container(expand=True),
                        ft.Text("Stock", size=13, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=COL_W.stock, text_align=ft.TextAlign.CENTER),
                        ft.Text("Precio venta", size=13, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=COL_W.precio, text_align=ft.TextAlign.RIGHT),
                        ft.Text("Fab/Comp", size=13, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=COL_W.fab_comp, text_align=ft.TextAlign.RIGHT),
                        ft.Text("Costo total", size=13, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=COL_W.costo_total, text_align=ft.TextAlign.RIGHT),
                        ft.Container(width=COL_W.acciones),
                    ],
                    spacing=6,
                ),
                padding=ft.padding.symmetric(12, 14),
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
                            ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=42, color=t["text_hint"]),
                            ft.Text("No hay productos registrados.", size=15, weight=ft.FontWeight.W_500),
                        ],
                        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0), padding=ft.padding.all(40), expand=True,
                )
            )
        else:
            visible_products = productos if _show_all["value"] else productos[:MOV_MAX]
            for i, p in enumerate(visible_products):
                table_col.controls.append(_build_row(p, i % 2 == 0))
            remaining = len(productos) - MOV_MAX
            if remaining > 0 and not _show_all["value"]:
                def _load_more_prods(e):
                    _show_all["value"] = True
                    _refresh_table()
                table_col.controls.append(
                    ft.Container(
                        content=ft.ElevatedButton(
                            f"Cargar más ({remaining} restantes)",
                            on_click=_load_more_prods,
                            style=ft.ButtonStyle(
                                bgcolor=t.get("bg_header", t["bg_card"]),
                                color=t["accent"],
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                        ),
                        alignment=ft.alignment.center,
                        padding=ft.padding.all(14),
                    )
                )

        if table_col.parent:
            table_col.update()

    def _on_search_stock(e):
        _show_all["value"] = False
        search_filter["value"] = (e.control.value or "").strip()
        _refresh_table()
    tf_search.on_change = _on_search_stock
    _refresh_table()

    main_container = ft.Container(expand=True)
    _render()

    main_container.refresh_data = _refresh_table
    main_container.open_new_form = lambda: _open_form()
    return main_container
