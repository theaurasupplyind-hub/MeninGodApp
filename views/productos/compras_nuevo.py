"""
compras_nuevo.py — NUEVO flujo de compra con cascada Producto → Color → Talle.
Comparar con compras.py (original) para evaluar velocidad y simplicidad.
"""

import logging


from datetime import datetime

import flet as ft
from theme import get_theme
from services.autocomplete_service import search_productos_proveedor, search_proveedores
from db.database import (
    get_colores_by_producto, get_talles_by_producto_color,
    get_variante_by_producto_color_talla, get_variante_by_id,
    get_variantes_by_producto,
    save_compra, update_compra, delete_compra,
    get_compras, get_compra_by_numero,
    get_producto_by_id,
)
from views.productos.nuevo_producto_compra import NuevoProductoCompraDialog
from views.facturacion.components.autocomplete import AutocompleteField

log = logging.getLogger("mvp10")


def ComprasViewNuevo(page: ft.Page, on_switch_tab=None):
    t = get_theme(page)
    proveedor_id = {"value": None}
    editando = {"value": False, "numero": None}
    items = []
    items_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

    def _build_add_btn():
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=18, color=t["text_secondary"]),
                ft.Text("Agregar fila", size=13, color=t["text_secondary"]),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(12, 0),
            border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
            ink=True,
            on_click=lambda e: _agregar_fila(),
        )

    items_col.controls.append(_build_add_btn())

    # ── Encabezado ──────────────────────────────────────────────────────────
    ac_proveedor = AutocompleteField(
        page,
        search_fn=search_proveedores,
        label_fn=lambda p: p["nombre"],
        on_select=lambda p: proveedor_id.update({"value": p["id"]}) or None,
        t=t,
        allow_free_text=True,
        search_label="proveedor",
        icon=ft.Icons.STORE_OUTLINED,
        hint_text="Proveedor *",
        expand=True,
    )
    ac_proveedor.field.expand = True

    tf_fecha = ft.TextField(
        value=datetime.now().strftime("%d/%m/%Y"),
        hint_text="Fecha",
        border_radius=7, height=38, text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        bgcolor=t["bg_input"], border_color=t["border"],
        focused_border_color=t["accent"], color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
        width=140,
    )
    tf_notas = ft.TextField(
        hint_text="Observaciones",
        border_radius=7, height=38, text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        bgcolor=t["bg_input"], border_color=t["border"],
        focused_border_color=t["accent"], color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
        expand=True,
    )

    # ── Toolbar ─────────────────────────────────────────────────────────────
    def _agregar_fila(e=None):
        item = _build_row()
        items.append(item)
        btn_idx = len(items_col.controls) - 1
        items_col.controls.insert(btn_idx, item["container"])
        if items_col.page:
            items_col.update()
        item["ac_field"].focus()

    def _abrir_nuevo_producto(e):
        def _on_created(prod):
            _agregar_fila()
            item = items[-1]
            _on_producto_seleccionado(prod, item)
        dlg = NuevoProductoCompraDialog(page, t, on_created=_on_created)
        page.open(dlg)

    def _agregar_todas_variantes(e):
        tf_search = ft.TextField(
            hint_text="Buscar producto...",
            border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            bgcolor=t["bg_input"], border_color=t["border"],
            focused_border_color=t["accent"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
            autofocus=True,
        )
        results_col = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, height=250, tight=True)

        def _buscar(q):
            results_col.controls.clear()
            if not q.strip():
                if results_col.page:
                    results_col.update()
                return
            prods = search_productos_proveedor(q, limit=8)
            if not prods:
                results_col.controls.append(
                    ft.Container(
                        ft.Text("Sin resultados", size=13, color=t["text_secondary"]),
                        padding=ft.padding.all(20), alignment=ft.alignment.center,
                    )
                )
            else:
                for p in prods:
                    row = ft.Container(
                        content=ft.Text(p["detalle"], size=13, color=t["text_primary"]),
                        padding=ft.padding.symmetric(8, 10),
                        bgcolor=t["bg_row_even"],
                        border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
                        ink=True,
                        on_click=lambda e, prod=p: _seleccionar(prod),
                    )
                    results_col.controls.append(row)
            if results_col.page:
                results_col.update()

        def _seleccionar(prod):
            page.close(dlg_search)
            variantes = get_variantes_by_producto(prod["id"])
            if not variantes:
                _show_msg("El producto no tiene variantes.", t["accent"])
                return
            colores_map = {c["id"]: c for c in get_colores_by_producto(prod["id"])}
            for v in variantes:
                item = _build_row()
                item["ac_field"].value = prod["detalle"]
                item["producto_id"] = prod["id"]
                item["color_id"] = v["color_id"]
                item["talle_id"] = v["talla_id"]
                item["variante_id"] = v["id"]
                item["dd_color"].disabled = False
                item["dd_color"].options = [
                    ft.dropdown.Option(key=str(c["id"]), text=c["nombre"])
                    for c in colores_map.values()
                ]
                item["dd_color"].value = str(v["color_id"])
                talles = get_talles_by_producto_color(prod["id"], v["color_id"])
                item["dd_talle"].disabled = False
                item["dd_talle"].options = [
                    ft.dropdown.Option(key=str(t["id"]), text=t["nombre"])
                    for t in talles
                ]
                item["dd_talle"].value = str(v["talla_id"])
                pc = float(v.get("precio_compra", 0) or 0)
                if pc > 0:
                    item["tf_precio"].value = str(pc)
                items.append(item)
                btn_idx = len(items_col.controls) - 1
                items_col.controls.insert(btn_idx, item["container"])
            if items_col.page:
                items_col.update()

        tf_search.on_change = lambda e: _buscar(e.control.value or "")
        dlg_search = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text("Seleccionar producto", size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column([tf_search, results_col], spacing=8, tight=True),
                width=400,
            ),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg_search))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg_search)

    def _show_validation_modal(errors: list):
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text("Completá los datos", size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Corregí estos errores antes de guardar:", size=12, color=t["text_secondary"]),
                    ft.Column([
                        ft.Text(f"• {e}", size=12, color=ft.Colors.RED_400)
                        for e in errors
                    ], spacing=4, scroll=ft.ScrollMode.AUTO, height=200),
                ], spacing=8, tight=True),
                width=380,
            ),
            actions=[
                ft.TextButton("Entendido", on_click=lambda e: page.close(dlg)),
            ],
        )
        page.open(dlg)

    toolbar = ft.Row([
        ft.OutlinedButton(
            "+ Nuevo producto", icon=ft.Icons.NEW_RELEASES_OUTLINED,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8),
                                 color=t["text_secondary"]),
            on_click=_abrir_nuevo_producto,
        ),
        ft.OutlinedButton(
            "Todas las variantes", icon=ft.Icons.DASHBOARD_CUSTOMIZE_OUTLINED,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8),
                                 color=t["text_secondary"]),
            on_click=_agregar_todas_variantes,
        ),
    ], spacing=8)

    # ── Row builder ─────────────────────────────────────────────────────────
    def _build_row():
        ac_producto = AutocompleteField(
            page,
            search_fn=search_productos_proveedor,
            label_fn=lambda p: p["detalle"],
            on_select=lambda prod: _on_producto_seleccionado(prod, item),
            t=t,
            allow_free_text=False,
            search_label="producto",
            icon=ft.Icons.INVENTORY_2_OUTLINED,
            hint_text="Buscar producto...",
            width=180,
        )
        ac_producto.field.height = None
        ac_producto.field.content_padding = ft.padding.symmetric(6, 4)
        dd_color = ft.Dropdown(
            hint_text="Color",
            options=[],
            disabled=True,
            width=120,
            text_size=12,
            bgcolor=t["bg_input"],
            border_color=t["border"],
            focused_border_color=t["accent"],
            color=t["text_primary"],
            content_padding=ft.padding.symmetric(6, 4),
            on_change=lambda e: _on_color_change(e, item),
        )
        dd_talle = ft.Dropdown(
            hint_text="Talle",
            options=[],
            disabled=True,
            width=100,
            text_size=12,
            bgcolor=t["bg_input"],
            border_color=t["border"],
            focused_border_color=t["accent"],
            color=t["text_primary"],
            content_padding=ft.padding.symmetric(6, 4),
            on_change=lambda e: _on_talle_change(e, item),
        )
        tf_cant = ft.TextField(
            value="1",
            width=60, text_size=13,
            content_padding=ft.padding.symmetric(6, 4),
            bgcolor=t["bg_input"], border_color=t["border"],
            focused_border_color=t["accent"], color=t["text_primary"],
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: _calc_total(item),
        )
        tf_precio = ft.TextField(
            hint_text="P. compra",
            width=100, text_size=13,
            content_padding=ft.padding.symmetric(6, 4),
            bgcolor=t["bg_input"], border_color=t["border"],
            focused_border_color=t["accent"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: _calc_total(item),
        )
        tf_total = ft.TextField(
            value="0",
            width=90, text_size=13, read_only=True,
            content_padding=ft.padding.symmetric(6, 4),
            bgcolor=t["bg_input"], border_color=t["border"],
            color=t["accent"],
        )
        remove_btn = ft.IconButton(
            ft.Icons.CLOSE, icon_size=16, icon_color=t["text_secondary"],
            on_click=lambda e: _remove_row(item),
        )

        row_container = ft.Container(
            content=ft.Row([
                ac_producto.field,
                dd_color,
                dd_talle,
                tf_cant,
                tf_precio,
                tf_total,
                remove_btn,
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(4, 0),
        )

        item = {
            "ac_field": ac_producto.field,
            "dd_color": dd_color,
            "dd_talle": dd_talle,
            "tf_cant": tf_cant,
            "tf_precio": tf_precio,
            "tf_total": tf_total,
            "remove_btn": remove_btn,
            "container": row_container,
            "producto_id": None,
            "color_id": None,
            "talle_id": None,
            "variante_id": None,
        }
        return item

    def _on_producto_seleccionado(prod, item):
        item["ac_field"].value = prod["detalle"]
        item["producto_id"] = prod["id"]
        item["color_id"] = None
        item["talle_id"] = None
        item["variante_id"] = None
        # Reset color/talle
        item["dd_color"].options = []
        item["dd_color"].value = None
        item["dd_color"].disabled = False
        item["dd_talle"].options = []
        item["dd_talle"].value = None
        item["dd_talle"].disabled = True
        # Set precio venta as hint for precio compra
        pv = prod.get("precio_unitario", 0)
        item["tf_precio"].hint_text = f"P. compra (venta: ${int(pv):,})".replace(",", ".")
        # Load colors
        colores = get_colores_by_producto(prod["id"])
        if colores:
            item["dd_color"].options = [
                ft.dropdown.Option(key=str(c["id"]), text=c["nombre"])
                for c in colores
            ]
        else:
            # Producto sin variantes (genérico) — usar variante única
            variantes = get_variantes_by_producto(prod["id"])
            gen = [v for v in variantes if not v.get("color_id")]
            if gen:
                item["variante_id"] = gen[0]["id"]
                item["dd_color"].disabled = True
                item["dd_talle"].disabled = True
        if item["ac_field"].page:
            item["ac_field"].update()
            item["dd_color"].update()
            item["dd_talle"].update()
            item["tf_precio"].update()

    def _on_color_change(e, item):
        color_id = int(e.control.value) if e.control.value else None
        item["color_id"] = color_id
        item["talle_id"] = None
        item["variante_id"] = None
        item["dd_talle"].value = None
        if color_id and item["producto_id"]:
            talles = get_talles_by_producto_color(item["producto_id"], color_id)
            item["dd_talle"].options = [
                ft.dropdown.Option(key=str(talle["id"]), text=talle["nombre"])
                for talle in talles
            ]
            item["dd_talle"].disabled = False
        else:
            item["dd_talle"].options = []
            item["dd_talle"].disabled = True
        if item["dd_talle"].page:
            item["dd_talle"].update()

    def _on_talle_change(e, item):
        talla_id = int(e.control.value) if e.control.value else None
        item["talle_id"] = talla_id
        if item["producto_id"] and item["color_id"] and talla_id:
            var = get_variante_by_producto_color_talla(
                item["producto_id"], item["color_id"], talla_id
            )
            if var:
                item["variante_id"] = var["id"]
                pc = float(var.get("precio_compra", 0) or 0)
                if pc > 0:
                    item["tf_precio"].hint_text = f"Últ. compra: ${int(pc):,}".replace(",", ".")
                    if not item["tf_precio"].value:
                        item["tf_precio"].value = str(pc)
            else:
                item["variante_id"] = None
                item["tf_precio"].hint_text = "P. compra (nueva variante)"
        if item["tf_precio"].page:
            item["tf_precio"].update()

    def _calc_total(item):
        try:
            cant = float(item["tf_cant"].value or "0")
            precio = float(item["tf_precio"].value or "0")
            total = cant * precio
            item["tf_total"].value = f"${int(total):,}".replace(",", ".")
        except (ValueError, AttributeError):
            item["tf_total"].value = "$0"
        if item["tf_total"].page:
            item["tf_total"].update()

    def _remove_row(item):
        if item in items:
            items.remove(item)
            items_col.controls.remove(item["container"])
            if items_col.page:
                items_col.update()

    # ── Guardar ──────────────────────────────────────────────────────────────
    def _guardar(e):
        try:
            if not ac_proveedor.value:
                _show_msg("Ingresá un proveedor.", t["accent"])
                return
            if not items:
                _show_msg("Agregá al menos un producto.", t["accent"])
                return

            # Filtrar filas vacías (sin producto seleccionado ni texto)
            items_filtrados = [it for it in items
                               if it.get("producto_id")
                               or (it["ac_field"].value or "").strip()]
            if not items_filtrados:
                _show_msg("Agregá al menos un producto.", t["accent"])
                return

            errors = []
            for i, item in enumerate(items_filtrados, 1):
                det = item["ac_field"].value or f"Fila {i}"
                if not item["producto_id"]:
                    errors.append(f"{det}: seleccioná un producto de la lista.")
                    continue
                if not item["variante_id"]:
                    if not item["color_id"]:
                        errors.append(f"{det}: seleccioná un color.")
                    if not item["talle_id"]:
                        errors.append(f"{det}: seleccioná un talle.")
                try:
                    cant = float(item["tf_cant"].value or "0")
                    if cant <= 0:
                        errors.append(f"{det}: la cantidad debe ser mayor a 0.")
                except ValueError:
                    errors.append(f"{det}: cantidad inválida.")

            if errors:
                _show_validation_modal(errors)
                return

            data_items = []
            for item in items_filtrados:
                detalle = (item["ac_field"].value or "").strip()
                cant = float(item["tf_cant"].value or "0")
                precio = float(item["tf_precio"].value or "0")
                data_items.append({
                    "detalle": detalle,
                    "cantidad": cant,
                    "precio_unitario": precio,
                    "total": cant * precio,
                    "variante_id": item["variante_id"],
                    "_producto_id": item["producto_id"],
                    "_color_id": item["color_id"],
                    "_talla_id": item["talle_id"],
                })

            total_compra = sum(it["total"] for it in data_items)
            compra_data = {
                "proveedor_nombre": ac_proveedor.value.strip(),
                "fecha": tf_fecha.value or datetime.now().strftime("%d/%m/%Y"),
                "notas": tf_notas.value or "",
                "total": total_compra,
            }
            if editando["value"]:
                update_compra(editando["numero"], compra_data, data_items)
                numero = editando["numero"]
            else:
                numero = save_compra(compra_data, data_items)
        except Exception as ex:
            log.error(f"Error al guardar compra: {ex}", exc_info=True)
            _show_msg(f"Error: {ex}", ft.Colors.RED_600)
            return

        _show_msg(f"Compra {numero} guardada ✅", ft.Colors.GREEN_600)
        _limpiar()
        _cargar_historial()
        page.update()

    def _show_msg(text, color):
        sb = ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color, duration=3200)
        page.open(sb)

    def _limpiar():
        editando["value"] = False
        editando["numero"] = None
        ac_proveedor.value = ""
        proveedor_id["value"] = None
        tf_fecha.value = datetime.now().strftime("%d/%m/%Y")
        tf_notas.value = ""
        items.clear()
        items_col.controls.clear()
        items_col.controls.append(_build_add_btn())
        if items_col.page:
            items_col.update()
        if ac_proveedor.field.page:
            ac_proveedor.field.update()
            tf_fecha.update()
            tf_notas.update()

    # ── Layout ──────────────────────────────────────────────────────────────
    form_col = ft.Column([
        ft.Text("Nueva Compra", size=18, weight=ft.FontWeight.W_600, color=t["text_primary"]),
        ft.Container(height=8),
        ft.Column([
            ft.Row([
                ac_proveedor.control,
                tf_fecha,
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                tf_notas,
                toolbar,
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=6, tight=True),
        ft.Container(height=4),
        ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Text("Producto", size=11, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=180),
                    ft.Text("Color", size=11, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=120),
                    ft.Text("Talle", size=11, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=100),
                    ft.Text("Cant", size=11, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=60),
                    ft.Text("Precio", size=11, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=100),
                    ft.Text("Total", size=11, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=90),
                ], spacing=4),
                padding=ft.padding.symmetric(4, 0),
            ),
            items_col,
        ], scroll=ft.ScrollMode.AUTO, expand=True),
        ft.Divider(height=1, color=t["border"]),
        ft.Row([
            ft.OutlinedButton(
                "Nueva compra",
                icon=ft.Icons.ADD,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                    color=t["text_secondary"],
                ),
                on_click=lambda e: _limpiar(),
            ),
            ft.ElevatedButton(
                "Guardar compra",
                icon=ft.Icons.SAVE,
                bgcolor=t["accent"], color=t["accent_text"],
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=_guardar,
            ),
        ], alignment=ft.MainAxisAlignment.END, spacing=8),
    ], spacing=0, expand=True)

    # ── Historial ───────────────────────────────────────────────────────────
    history_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
    history_header = ft.Container(
        content=ft.Row([
            ft.Text("N°", size=10, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=65),
            ft.Text("Proveedor", size=10, weight=ft.FontWeight.W_600, color=t["text_secondary"], expand=True),
            ft.Text("Fecha", size=10, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=75),
            ft.Text("Total", size=10, weight=ft.FontWeight.W_600, color=t["text_secondary"], width=75),
        ], spacing=4),
        padding=ft.padding.only(bottom=4),
    )

    def _cargar_historial():
        history_list.controls.clear()
        compras = get_compras(limit=50)
        for c in compras:
            row = ft.Container(
                content=ft.Row([
                    ft.Text(c["numero"], size=11, weight=ft.FontWeight.W_600, color=t["accent"], width=65),
                    ft.Text(c.get("proveedor_nombre", ""), size=11, color=t["text_secondary"], expand=True),
                    ft.Text(c.get("fecha", ""), size=11, color=t["text_secondary"], width=75),
                    ft.Text(f"${int(c.get('total', 0)):,}".replace(",", "."), size=11, color=t["text_primary"], width=75),
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(6, 8),
                bgcolor=t["bg_row_even"],
                border_radius=6,
                ink=True,
                on_click=lambda e, num=c["numero"]: _editar_compra(num),
            )
            history_list.controls.append(row)
        if history_list.page:
            history_list.update()

    def _editar_compra(numero):
        compra = get_compra_by_numero(numero)
        if not compra:
            return
        editando["value"] = True
        editando["numero"] = numero
        ac_proveedor.value = compra.get("proveedor_nombre", "")
        proveedor_id["value"] = compra.get("proveedor_id")
        tf_fecha.value = compra.get("fecha", "")
        tf_notas.value = compra.get("notas", "")
        items.clear()
        items_col.controls.clear()
        for ci in compra.get("items", []):
            item = _build_row()
            item["tf_cant"].value = str(ci.get("cantidad", 1))
            item["tf_precio"].value = str(ci.get("precio_unitario", 0))
            item["variante_id"] = ci.get("variante_id")
            item["producto_id"] = ci.get("producto_id")
            item["color_id"] = ci.get("color_id")
            item["talle_id"] = ci.get("talla_id")
            pid = item["producto_id"]
            ci_color_id = ci.get("color_id")
            ci_talle_id = ci.get("talla_id")
            vr = get_variante_by_id(ci["variante_id"]) if ci.get("variante_id") else None
            if vr:
                pid = vr["producto_id"]
                item["producto_id"] = pid
                if vr.get("color_id"):
                    ci_color_id = vr["color_id"]
                if vr.get("talla_id"):
                    ci_talle_id = vr["talla_id"]
            if pid:
                prod = get_producto_by_id(pid)
                prod_detalle = prod["detalle"] if prod else (ci.get("detalle", ""))
                print(f"[DEBUG _editar_compra] producto encontrado: detalle={prod_detalle}")
                _on_producto_seleccionado(
                    {"id": pid, "detalle": prod_detalle, "precio_unitario": 0},
                    item,
                )
                # _on_producto_seleccionado resetea color_id/talle_id a None, restaurar
                item["color_id"] = ci_color_id
                item["talle_id"] = ci_talle_id
                if item["color_id"]:
                    item["dd_color"].value = str(item["color_id"])
                    talles = get_talles_by_producto_color(pid, item["color_id"])
                    item["dd_talle"].options = [
                        ft.dropdown.Option(key=str(t["id"]), text=t["nombre"])
                        for t in talles
                    ]
                    item["dd_talle"].disabled = False
                    if item["talle_id"]:
                        item["dd_talle"].value = str(item["talle_id"])
                    if item["dd_color"].page:
                        item["dd_color"].update()
                        item["dd_talle"].update()
            _calc_total(item)
            items.append(item)
            items_col.controls.append(item["container"])
        items_col.controls.append(_build_add_btn())
        if items_col.page:
            items_col.update()
        if ac_proveedor.field.page:
            ac_proveedor.field.update()
            tf_fecha.update()
            tf_notas.update()

    view = ft.Row([
        ft.Container(
            content=form_col,
            padding=ft.padding.symmetric(vertical=12, horizontal=16),
            expand=True,
        ),
        ft.VerticalDivider(width=1, color=t["border_light"]),
        ft.Container(
            content=ft.Column([
                ft.Text("Historial", size=14, weight=ft.FontWeight.W_600, color=t["text_primary"]),
                ft.Container(height=4),
                history_header,
                history_list,
            ], expand=True),
            width=380,
            padding=ft.padding.symmetric(vertical=12, horizontal=12),
        ),
    ], expand=True, spacing=0)

    view.refresh_data = _cargar_historial
    _cargar_historial()
    return view
