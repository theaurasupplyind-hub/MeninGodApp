"""
productos/compras.py
Registro de compras (entrada de mercadería).
Dos columnas: formulario a la izquierda, historial a la derecha.
"""
import logging
from datetime import datetime
log = logging.getLogger("mvp10")

import flet as ft
from theme import get_theme

from db.database import (
    get_compras, get_compra_by_numero, save_compra, update_compra, delete_compra,
    get_stats_compras, get_productos, get_producto_by_detalle, get_producto_by_id,
    get_variantes_activas, get_variante_by_id,
    get_variante_by_producto_color_talla,
    get_colores, get_tallas,
    get_color_by_nombre, get_talla_by_nombre,
    save_color, save_talla, save_variante, save_producto,
    get_colores_by_producto, get_talles_by_producto_color,
)
from services.autocomplete_service import search_proveedores, search_productos_proveedor, search_colores, search_talles
from views.facturacion.components.autocomplete import AutocompleteField


def _fmt(val: float) -> str:
    try:
        return f"${int(float(val)):,}".replace(",", ".")
    except Exception:
        return "$0"


def _parse_num(raw: str) -> float:
    val = (raw or "0").strip().replace("$", "").replace(".", "")
    if "," in val:
        val = val.replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return 0.0


from views.flow_guide import HelpButton

def ComprasView(page: ft.Page, on_switch_tab=None):
    t = get_theme(page)
    state = {
        "editando": False,
        "numero_actual": None,
    }

    # ── Controles ────────────────────────────────────────────────────────────
    numero_text = ft.Text("", size=13, color=t["accent"], weight=ft.FontWeight.W_500)
    fecha_text = ft.Text(datetime.now().strftime("%d/%m/%Y"), size=13, color=t["text_secondary"])
    total_text = ft.Text("$ 0", size=24, weight=ft.FontWeight.W_700, color=t["accent"])
    items_col = ft.ListView(spacing=4, expand=True, auto_scroll=False)
    history_col = ft.ListView(spacing=0, expand=True, auto_scroll=False)

    # ── Autocomplete proveedor ───────────────────────────────────────────────
    ac_proveedor = AutocompleteField(
        page=page,
        search_fn=search_proveedores,
        label_fn=lambda p: p.get("nombre", ""),
        sublabel_fn=lambda p: p.get("telefono", "") or "",
        hint_text="Nombre del proveedor", t=t,
        on_submit_next=lambda: (items_controls[0]["ac_producto"].focus() if items_controls else None),
    )

    tf_notas = ft.TextField(
        hint_text="Notas opcionales",
        border_radius=7, height=38, text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
    )

    items_controls: list[dict] = []

    def _show_message(text: str, color=t["accent"]):
        page.open(ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color, duration=3200))

    def _recalcular():
        total = 0.0
        for item in items_controls:
            cant = _parse_num(item["stock"].value or "1")
            precio = _parse_num(item["precio"].value or "0")
            subtotal = cant * precio
            item["total_tf"].value = _fmt(subtotal)
            total += subtotal
        total_text.value = _fmt(total)
        page.update()

    # ── Custom row builder for Compras ──────────────────────────────────────

    def _resolve_variant(item_data: dict, tf_precio, ultimo_precio_text, stock_badge):
        pid = item_data.get("_producto_id")
        cid = item_data.get("_color_id")
        tid = item_data.get("_talla_id")
        if pid and cid and tid:
            v = get_variante_by_producto_color_talla(pid, cid, tid)
            if v:
                item_data["_variante_id"] = v["id"]
                tf_precio.value = str(int(v.get("precio_compra", 0) or 0))
                stock_badge.content.value = f"Stock: {int(v.get('stock_actual', 0) or 0)}"
                stock_badge.visible = True
                ult_compra = v.get("precio_compra", 0) or 0
                if ult_compra > 0:
                    ultimo_precio_text.value = f"Últ: {_fmt(ult_compra)}"
                    ultimo_precio_text.visible = True
                else:
                    ultimo_precio_text.visible = False
                if stock_badge.page:
                    try: stock_badge.update()
                    except Exception: pass
                return
        item_data["_variante_id"] = None
        stock_badge.visible = False
        if stock_badge.page:
            try: stock_badge.update()
            except Exception: pass

    def _build_compra_row(initial=None, on_change=None, on_remove=None, on_row_complete=None, on_select=None):
        init = initial or {}

        # Stock badge (below producto)
        stock_badge = ft.Container(
            content=ft.Text("", size=9, color=t["text_secondary"]),
            padding=ft.padding.only(left=4, top=0),
            visible=False,
        )

        # ── Producto Autocomplete ──
        def _on_producto_selected(prod: dict) -> None:
            tf_precio_nuevo.value = str(int(prod.get("precio_compra", 0) or 0))
            if prod.get("is_variant"):
                ac_producto.value = prod.get("detalle", "")
                item_data["_producto_id"] = prod.get("id")
                item_data["_color_id"] = prod.get("color_id")
                item_data["_talla_id"] = prod.get("talla_id")
                item_data["_color_nombre"] = prod.get("color", "")
                item_data["_talle_nombre"] = prod.get("talla", "")
                _resolve_variant(item_data, tf_precio_nuevo, ultimo_precio_text, stock_badge)
                all_colores = get_colores()
                dd_color.options = [ft.dropdown.Option(key=str(c["id"]), text=c["nombre"]) for c in all_colores]
                dd_color.disabled = False
                dd_color.value = str(prod.get("color_id", "")) if prod.get("color_id") else None
                all_tallas = get_tallas()
                dd_talle.options = [ft.dropdown.Option(key=str(ta["id"]), text=ta["nombre"]) for ta in all_tallas]
                dd_talle.disabled = False
                dd_talle.value = str(prod.get("talla_id", "")) if prod.get("talla_id") else None
                if dd_color.page:
                    try: dd_color.update()
                    except Exception: pass
                if dd_talle.page:
                    try: dd_talle.update()
                    except Exception: pass
            elif prod.get("is_curva"):
                item_data["_producto_id"] = prod.get("id")
                item_data["_color_id"] = None
                item_data["_talla_id"] = None
                item_data["_variante_id"] = None
                stock_badge.visible = False
            else:
                item_data["_producto_id"] = prod.get("id")
                item_data["_color_id"] = None
                item_data["_talla_id"] = None
                item_data["_color_nombre"] = None
                item_data["_talle_nombre"] = None
                item_data["_variante_id"] = None
                _populate_color_dropdown(prod.get("id"))
                stock_badge.visible = False
                if dd_color.page:
                    try: dd_color.update()
                    except Exception: pass
                if dd_talle.page:
                    try: dd_talle.update()
                    except Exception: pass
                if on_select:
                    on_select(prod, item_data)
            if ac_producto.field.page:
                try: ac_producto.field.update()
                except Exception: pass
            if tf_precio_nuevo.page:
                try: tf_precio_nuevo.update()
                except Exception: pass
            if ultimo_precio_text.page:
                try: ultimo_precio_text.update()
                except Exception: pass
            if on_change:
                on_change()

        ac_producto = AutocompleteField(
            page=page,
            search_fn=search_productos_proveedor,
            label_fn=lambda p: (
                f"🔄 {p.get('detalle', '')} - {p.get('producto_detalle', '')}" if p.get("is_curva")
                else f"{p.get('detalle', '')} - {p.get('color', '')} {p.get('talla', '')}".strip(" -") if p.get("is_variant")
                else p.get("detalle", "")
            ),
            sublabel_fn=lambda p: f"Stock: {int(p.get('stock_actual', 0) or 0)}  ${int(p.get('precio_compra', 0) or 0):,}".replace(",", "."),
            hint_text="Producto...",
            expand=True, t=t,
            on_select=_on_producto_selected,
            on_submit_next=lambda: dd_color.focus(),
            allow_free_text=False,
        )
        if init.get("detalle"):
            ac_producto.value = init["detalle"]

        # ── Color Dropdown ──
        dd_color = ft.Dropdown(
            options=[], width=100, text_size=13,
            hint_text="Color", disabled=True,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
            content_padding=ft.padding.symmetric(6, 4),
            on_change=lambda e: _on_color_change(e.control.value),
        )

        def _on_color_change(color_id_str):
            if not color_id_str:
                item_data["_color_id"] = None
                item_data["_color_nombre"] = None
                dd_talle.options = []
                dd_talle.value = None
                dd_talle.disabled = True
                if dd_talle.page:
                    try: dd_talle.update()
                    except Exception: pass
                return
            cid = int(color_id_str)
            prod_id = item_data.get("_producto_id")
            item_data["_color_id"] = cid
            option = next((c for c in dd_color.options if c.key == color_id_str), None)
            item_data["_color_nombre"] = option.text if option else ""
            talles = get_talles_by_producto_color(prod_id, cid) if prod_id else []
            dd_talle.options = [ft.dropdown.Option(key=str(t["id"]), text=t["nombre"]) for t in talles]
            dd_talle.disabled = False
            dd_talle.value = None
            item_data["_talla_id"] = None
            item_data["_talle_nombre"] = None
            if dd_talle.page:
                try: dd_talle.update()
                except Exception: pass
            _resolve_variant(item_data, tf_precio_nuevo, ultimo_precio_text, stock_badge)
            if on_change:
                on_change()

        def _populate_color_dropdown(producto_id):
            colores = get_colores_by_producto(producto_id) if producto_id else []
            dd_color.options = [ft.dropdown.Option(key=str(c["id"]), text=c["nombre"]) for c in colores]
            dd_color.disabled = False
            dd_color.value = None
            dd_talle.options = []
            dd_talle.disabled = True
            dd_talle.value = None

        # ── Talle Dropdown ──
        dd_talle = ft.Dropdown(
            options=[], width=85, text_size=13,
            hint_text="Talle", disabled=True,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
            content_padding=ft.padding.symmetric(6, 4),
            on_change=lambda e: _on_talle_change(e.control.value),
        )

        def _on_talle_change(talle_id_str):
            if not talle_id_str:
                item_data["_talla_id"] = None
                item_data["_talle_nombre"] = None
                return
            tid = int(talle_id_str)
            item_data["_talla_id"] = tid
            option = next((td for td in dd_talle.options if td.key == talle_id_str), None)
            item_data["_talle_nombre"] = option.text if option else ""
            _resolve_variant(item_data, tf_precio_nuevo, ultimo_precio_text, stock_badge)
            if on_change:
                on_change()

        if init.get("color_id"):
            all_colores = get_colores()
            dd_color.options = [ft.dropdown.Option(key=str(c["id"]), text=c["nombre"]) for c in all_colores]
            dd_color.disabled = False
            dd_color.value = str(init["color_id"])
        if init.get("talla_id"):
            all_tallas = get_tallas()
            dd_talle.options = [ft.dropdown.Option(key=str(ta["id"]), text=ta["nombre"]) for ta in all_tallas]
            dd_talle.disabled = False
            dd_talle.value = str(init["talla_id"])

        # ── Stock a Comprar ──
        raw_cant = init.get("cantidad", 1)
        stock_val = str(raw_cant).rstrip("0").rstrip(".") if isinstance(raw_cant, float) else str(raw_cant)
        tf_stock = ft.TextField(
            value=stock_val, width=50, height=34, text_size=13,
            hint_text="Stock",
            content_padding=ft.padding.symmetric(6, 6), border_radius=6,
            keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.CENTER,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
            on_change=lambda e: on_change and on_change(),
            on_submit=lambda e: tf_precio_nuevo.focus(),
        )

        # ── Precio Nuevo + Último precio ──
        ultimo_precio_text = ft.Text("", size=8, color=t["text_hint"], visible=False)
        raw_precio = init.get("precio_unitario", 0)
        precio_val = "" if not raw_precio else str(int(raw_precio))
        if raw_precio and float(raw_precio) > 0:
            ultimo_precio_text.value = f"Últ: {_fmt(float(raw_precio))}"
            ultimo_precio_text.visible = True
        tf_precio_nuevo = ft.TextField(
            value=precio_val, width=95, height=34, text_size=13,
            hint_text="Precio",
            content_padding=ft.padding.symmetric(8, 6), border_radius=6,
            keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
            read_only=False,
            on_change=lambda e: on_change and on_change(),
            on_submit=lambda e: on_row_complete and on_row_complete(item_data),
        )
        precio_col = ft.Column([tf_precio_nuevo, ultimo_precio_text],
                               spacing=0, tight=True)

        # ── Total ──
        tf_total = ft.TextField(
            value=_fmt(init.get("total", 0)), width=70, height=34, text_size=13,
            content_padding=ft.padding.symmetric(8, 6), border_radius=6,
            read_only=True, text_align=ft.TextAlign.RIGHT, border_color=ft.Colors.TRANSPARENT,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

        item_data: dict = {
            "ac_producto": ac_producto,
            "ac_color": dd_color,
            "ac_talle": dd_talle,
            "stock": tf_stock,
            "precio": tf_precio_nuevo,
            "total_tf": tf_total,
            "row": None,
            "_variante_id": init.get("variante_id"),
            "_producto_id": init.get("_producto_id"),
            "_color_id": init.get("color_id"),
            "_talla_id": init.get("talla_id"),
            "_color_nombre": init.get("color"),
            "_talle_nombre": init.get("talla"),
        }

        remove_btn = ft.IconButton(
            ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=ft.Colors.ERROR,
            icon_size=16, tooltip="Quitar fila",
            on_click=lambda e: on_remove and on_remove(item_data),
            style=ft.ButtonStyle(padding=ft.padding.all(4)),
        )

        row = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(content=ac_producto.control, width=220),
                    dd_color,
                    dd_talle,
                    tf_stock,
                    precio_col,
                    tf_total,
                    remove_btn,
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                stock_badge,
            ], spacing=0, tight=True),
            padding=ft.padding.symmetric(3, 0),
        )
        item_data["row"] = row

        # If initial data had a variant, resolve it
        if item_data.get("_producto_id") and item_data.get("_color_id") and item_data.get("_talla_id"):
            _resolve_variant(item_data, tf_precio_nuevo, ultimo_precio_text, stock_badge)
        elif init.get("stock_actual") and not init.get("_producto_id"):
            stock_badge.content.value = f"Stock: {int(init['stock_actual'])}"
            stock_badge.visible = True

        return item_data

    # ── Inline row helpers ──────────────────────────────────────────────────

    def _on_item_removed(item_data: dict) -> None:
        if item_data in items_controls:
            items_controls.remove(item_data)
            items_col.controls.remove(item_data["row"])
        _recalcular()

    def _on_row_producto_selected(prod: dict, current_item: dict = None):
        if not prod.get("is_variant") and not prod.get("is_curva"):
            _add_variant_rows(prod, current_item)

    def _add_variant_rows(prod: dict, current_item: dict = None):
        variantes = get_variantes_activas(prod["id"])

        # Collect empty rows (excluding the current one)
        empty_slots = []
        for item in items_controls:
            if item is current_item:
                continue
            if not (item["ac_producto"].value or "").strip():
                empty_slots.append(item)

        # Priority: current_item first, then empty slots, then new rows
        slots = []
        if current_item:
            slots.append(current_item)
        slots.extend(empty_slots)

        for i, v in enumerate(variantes):
            if i < len(slots):
                slot = slots[i]
                slot["ac_producto"].value = prod.get("detalle", "")
                slot["_variante_id"] = v["id"]
                slot["_producto_id"] = prod.get("id")
                slot["_color_id"] = v.get("color_id")
                slot["_talla_id"] = v.get("talla_id")
                slot["_color_nombre"] = v.get("color", "")
                slot["_talle_nombre"] = v.get("talla", "")
                slot["precio"].value = str(int(v.get("precio_compra", 0) or 0))
                slot["stock"].value = "1"
                colores = get_colores_by_producto(prod["id"]) if prod.get("id") else []
                slot["ac_color"].options = [ft.dropdown.Option(key=str(c["id"]), text=c["nombre"]) for c in colores]
                slot["ac_color"].disabled = False
                slot["ac_color"].value = str(v.get("color_id", "")) if v.get("color_id") else None
                talles = get_talles_by_producto_color(prod["id"], v.get("color_id")) if prod.get("id") and v.get("color_id") else []
                slot["ac_talle"].options = [ft.dropdown.Option(key=str(ta["id"]), text=ta["nombre"]) for ta in talles]
                slot["ac_talle"].disabled = False
                slot["ac_talle"].value = str(v.get("talla_id", "")) if v.get("talla_id") else None
                if slot["ac_producto"].field.page:
                    try: slot["ac_producto"].field.update()
                    except Exception: pass
                if slot["ac_color"].page:
                    try: slot["ac_color"].update()
                    except Exception: pass
                if slot["ac_talle"].page:
                    try: slot["ac_talle"].update()
                    except Exception: pass
                if slot["precio"].page:
                    try: slot["precio"].update()
                    except Exception: pass
                if slot["stock"].page:
                    try: slot["stock"].update()
                    except Exception: pass
            else:
                try:
                    row = _build_compra_row(
                        initial={
                            "detalle": prod.get("detalle", ""),
                            "color": v.get("color", ""),
                            "talla": v.get("talla", ""),
                            "color_id": v.get("color_id"),
                            "talla_id": v.get("talla_id"),
                            "cantidad": 1,
                            "precio_unitario": v.get("precio_compra", 0) or 0,
                            "variante_id": v["id"],
                            "_producto_id": prod.get("id"),
                            "stock_actual": v.get("stock_actual", 0),
                        },
                        on_change=lambda: _recalcular(),
                        on_remove=_on_item_removed,
                        on_row_complete=lambda item: _on_row_complete(item),
                        on_select=_on_row_producto_selected,
                    )
                    items_controls.append(row)
                    items_col.controls.append(row["row"])
                except Exception as ex:
                    _show_message(f"Error al crear fila: {ex}", ft.Colors.ERROR)
                    log.error(f"Error _build_compra_row: {ex}", exc_info=True)
        page.update()
        _recalcular()

    def _build_new_row(initial=None):
        row = _build_compra_row(
            initial=initial,
            on_change=lambda: _recalcular(),
            on_remove=_on_item_removed,
            on_row_complete=lambda item: _on_row_complete(item),
            on_select=_on_row_producto_selected,
        )
        return row

    def _add_empty_row():
        row = _build_new_row()
        items_controls.append(row)
        items_col.controls.append(row["row"])
        if items_col.page:
            items_col.update()

    def _on_row_complete(current_item=None):
        if current_item:
            for i, item in enumerate(items_controls):
                if item is current_item and i + 1 < len(items_controls):
                    items_controls[i + 1]["ac_producto"].focus()
                    return
        _add_empty_row()
        if items_controls:
            items_controls[-1]["ac_producto"].focus()
        if items_col.page:
            items_col.update()

    def _limpiar_form():
        state["editando"] = False
        state["numero_actual"] = None
        numero_text.value = ""
        fecha_text.value = datetime.now().strftime("%d/%m/%Y")
        total_text.value = "$ 0"
        ac_proveedor.value = ""
        tf_notas.value = ""
        items_controls.clear()
        items_col.controls.clear()
        for _ in range(3):
            _add_empty_row()
        if items_col.page:
            items_col.update()
        if ac_proveedor.field.page:
            ac_proveedor.focus()

    def _cargar_compra(compra: dict):
        _limpiar_form()
        state["editando"] = True
        state["numero_actual"] = compra["numero"]
        numero_text.value = compra["numero"]
        fecha_text.value = compra.get("fecha", "")
        ac_proveedor.value = compra.get("proveedor_nombre", "")
        ac_proveedor.field.update()
        tf_notas.value = compra.get("notas", "")
        tf_notas.update()
        items_controls.clear()
        items_col.controls.clear()
        for i, it in enumerate(compra.get("items", [])):
            v_id = it.get("variante_id")
            stock_act = 0
            v_data = None
            if v_id:
                v_data = get_variante_by_id(v_id)
                if v_data:
                    stock_act = v_data.get("stock_actual", 0) or 0

            # Resolver producto_id, color_id, talla_id desde v_data o desde DB
            pid = v_data.get("producto_id") if v_data else it.get("producto_id")
            cid = v_data.get("color_id") if v_data else it.get("color_id")
            tid = v_data.get("talla_id") if v_data else it.get("talla_id")
            color_nombre = v_data.get("color", "") if v_data else ""
            talle_nombre = v_data.get("talla", "") if v_data else ""

            # Usar nombre del producto en vez del detalle completo para evitar duplicación
            detalle_autocomplete = it.get("detalle", "")
            if pid:
                prod = get_producto_by_id(pid)
                if prod:
                    detalle_autocomplete = prod.get("detalle", "") or detalle_autocomplete

            row = _build_new_row(initial={
                "detalle": detalle_autocomplete,
                "color": color_nombre,
                "talla": talle_nombre,
                "color_id": cid,
                "talla_id": tid,
                "cantidad": float(it.get("cantidad", 1)),
                "precio_unitario": float(it.get("precio_unitario", 0)),
                "total": it.get("total", 0),
                "variante_id": v_id,
                "_producto_id": pid,
                "stock_actual": stock_act,
            })
            items_controls.append(row)
            items_col.controls.append(row["row"])
        _recalcular()
        items_col.update()

    # ── Guardar ──────────────────────────────────────────────────────────────

    def collect_items() -> list:
        result = []
        for item in items_controls:
            prod = (item["ac_producto"].value or "").strip()
            if not prod:
                continue
            result.append({
                "detalle": f"{prod} {item.get('_color_nombre') or ''} {item.get('_talle_nombre') or ''}".strip(),
                "producto": prod,
                "color": item.get("_color_nombre") or "",
                "talla": item.get("_talle_nombre") or "",
                "cantidad": _parse_num(item["stock"].value),
                "precio_unitario": _parse_num(item["precio"].value),
                "total": _parse_num(item["total_tf"].value.replace("$", "").replace(".", "")),
                "variante_id": item.get("_variante_id"),
                "_producto_id": item.get("_producto_id"),
                "_color_id": item.get("_color_id"),
                "_talla_id": item.get("_talla_id"),
            })
        return result

    def collect_data() -> dict:
        return {
            "fecha": fecha_text.value or datetime.now().strftime("%d/%m/%Y"),
            "proveedor_id": None,
            "proveedor_nombre": ac_proveedor.value or "",
            "total": _parse_num(total_text.value.replace("$", "").replace(".", "").replace(" ", "")),
            "notas": tf_notas.value or "",
        }

    def _guardar(e=None):
        items_data = collect_items()
        if not items_data:
            _show_message("Agregá al menos un item.", t["accent"])
            return
        data = collect_data()
        if not data["proveedor_nombre"]:
            _show_message("Ingresá el nombre del proveedor.", t["accent"])
            return

        # Validate items without variante_id — try to auto-resolve or prompt
        unresolved = []
        for it in items_data:
            if it.get("variante_id"):
                continue
            prod = get_producto_by_detalle(it.get("producto", ""))
            if prod:
                color = get_color_by_nombre(it.get("color", ""))
                talla = get_talla_by_nombre(it.get("talla", ""))
                if color and talla:
                    v = get_variante_by_producto_color_talla(prod["id"], color["id"], talla["id"])
                    if v:
                        it["variante_id"] = v["id"]
                        continue
                unresolved.append(it)
            else:
                unresolved.append(it)

        def _do_save(items_override=None):
            final_items = items_override or items_data
            try:
                from services.auth_service import AuthService
                if state["numero_actual"]:
                    numero = update_compra(state["numero_actual"], data, final_items)
                    msg = f"Compra {numero} actualizada correctamente"
                else:
                    numero = save_compra(data, final_items)
                    msg = f"Compra {numero} guardada correctamente"
                _show_message(msg, ft.Colors.GREEN_700)
                AuthService().track("compra", numero, f"Compra {numero} —Proveedor: {data.get('proveedor_nombre', '')}")
                _limpiar_form()
                _refresh_history()
            except Exception as ex:
                log.error(f"Error guardando compra: {ex}", exc_info=True)
                _show_message(f"Error: {ex}", ft.Colors.ERROR)

        if unresolved:
            rows = []
            for it in unresolved:
                prod_name = it.get("producto", "")
                color_name = it.get("color", "")
                talla_name = it.get("talla", "")
                prod = get_producto_by_detalle(prod_name)
                color = get_color_by_nombre(color_name) if color_name else None
                talla = get_talla_by_nombre(talla_name) if talla_name else None
                issues = []
                if not prod:
                    issues.append("crear desde Productos")
                elif not color:
                    issues.append("nuevo color")
                elif not talla:
                    issues.append("nuevo talle")
                else:
                    issues.append("nueva variante")
                label = f"{prod_name} {color_name} {talla_name}".strip()
                rows.append(
                    ft.Container(
                        ft.Row([
                            ft.Text(f"• {label}", size=12, expand=True, weight=ft.FontWeight.W_500),
                            ft.Text(f"[{', '.join(issues)}]", size=11, color=t["text_hint"]),
                        ]),
                        padding=ft.padding.symmetric(4, 0),
                    )
                )

            def _resolve_and_save(ev, dlg):
                page.close(dlg)
                errores = []
                for it in unresolved:
                    prod_name = it.get("producto", "")
                    color_name = it.get("color", "")
                    talla_name = it.get("talla", "")
                    prod = get_producto_by_detalle(prod_name)
                    if not prod:
                        errores.append(f"'{prod_name}' no existe. Créalo desde Productos > Nuevo producto")
                        continue
                    prod_id = prod["id"]
                    color = get_color_by_nombre(color_name) if color_name else None
                    if not color and color_name:
                        color_id = save_color(color_name)
                    else:
                        color_id = color["id"] if color else None
                    talla = get_talla_by_nombre(talla_name) if talla_name else None
                    if not talla and talla_name:
                        talla_id = save_talla(talla_name)
                    else:
                        talla_id = talla["id"] if talla else None
                    if prod_id and color_id and talla_id:
                        v_id = save_variante(prod_id, {
                            "color_id": color_id,
                            "talla_id": talla_id,
                            "precio_compra": it.get("precio_unitario", 0),
                        })
                        it["variante_id"] = v_id
                if errores:
                    _show_message(" | ".join(errores), ft.Colors.ERROR)
                    return
                _do_save()

            dlg = ft.AlertDialog(
                modal=True,
                bgcolor=t["bg_card"],
                title=ft.Text("Filas sin variante", size=15, weight=ft.FontWeight.W_500),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Estos items no coinciden con ninguna variante existente:", size=12),
                        ft.Column(rows, spacing=2, scroll=ft.ScrollMode.AUTO, height=160),
                        ft.Text("Se crearán automáticamente al guardar.", size=11, color=t["text_hint"]),
                    ], spacing=8),
                    width=400,
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                    ft.ElevatedButton("Crear todo y guardar",
                                      bgcolor=t["accent"], color=t["accent_text"],
                                      on_click=lambda ev: _resolve_and_save(ev, dlg)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)
        else:
            _do_save()

    # ── Historial ───────────────────────────────────────────────────────────

    def _build_history_row(compra: dict, zebra: bool):
        resumen = compra.get("resumen", "") or ""
        if len(resumen) > 60:
            resumen = resumen[:60] + "..."
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(compra.get("fecha", ""), size=11, color=t["text_secondary"], width=70),
                    ft.Text(compra.get("proveedor_nombre", ""), size=12, width=90,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(resumen, size=11, color=t["text_primary"], expand=True,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(_fmt(compra.get("total", 0)), size=12, weight=ft.FontWeight.W_600, width=70, text_align=ft.TextAlign.RIGHT),
                    ft.IconButton(ft.Icons.DELETE_OUTLINED, icon_size=14, tooltip="Eliminar",
                                  icon_color=ft.Colors.ERROR,
                                  on_click=lambda e, c=compra: _confirmar_eliminar(c)),
                ],
                spacing=4,
            ),
            padding=ft.padding.symmetric(6, 10),
            bgcolor=t["bg_row_even"] if zebra else t["bg_row_odd"],
            border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
            ink=True,
            on_click=lambda e, c=compra: _editar_compra(c),
        )

    def _refresh_history():
        history_col.controls.clear()
        compras = get_compras(50)
        if not compras:
            history_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, size=36, color=t["text_hint"]),
                            ft.Text("No hay compras registradas.", size=14, weight=ft.FontWeight.W_500),
                        ],
                        spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0), padding=ft.padding.all(30), expand=True,
                )
            )
        else:
            history_col.controls.append(
                ft.Container(
                    ft.Row(
                        [
                            ft.Text("Fecha", size=10, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=70),
                            ft.Text("Proveedor", size=10, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=90),
                            ft.Text("Resumen", size=10, weight=ft.FontWeight.W_500, color=t["text_secondary"], expand=True),
                            ft.Text("Total", size=10, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=70, text_align=ft.TextAlign.RIGHT),
                            ft.Container(width=50),
                        ],
                        spacing=4,
                    ),
                    padding=ft.padding.symmetric(6, 10),
                    bgcolor=t["bg_header"],
                    border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border"])),
                )
            )
            for i, c in enumerate(compras):
                history_col.controls.append(_build_history_row(c, i % 2 == 0))
        if history_col.parent:
            history_col.update()

    def _editar_compra(compra: dict):
        compra_full = get_compra_by_numero(compra["numero"])
        if compra_full:
            _cargar_compra(compra_full)

    def _confirmar_eliminar(compra: dict):
        def _do_delete(ev, d):
            try:
                delete_compra(compra["numero"])
                if state["numero_actual"] == compra["numero"]:
                    _limpiar_form()
                _show_message(f"Compra {compra['numero']} eliminada.", ft.Colors.ERROR)
                page.close(d)
                _refresh_history()
            except Exception as ex:
                _show_message(f"Error: {ex}", ft.Colors.ERROR)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text("Eliminar compra"),
            content=ft.Text(f"¿Seguro que querés eliminar la compra {compra['numero']}?\nSe revertirá el stock."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                ft.ElevatedButton("Eliminar", bgcolor=ft.Colors.ERROR, color=t["accent_text"],
                                  on_click=lambda ev: _do_delete(ev, dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── Layout (2 columnas) ─────────────────────────────────────────────────

    help_comp = HelpButton([
        {"text": "Escribí el nombre del proveedor (se crea solo si no existe)"},
        {"text": "Buscá el fardo/producto o escribí uno nuevo"},
        {"text": "Guardá — el stock aumenta automáticamente"},
        {"text": "Revisá la deuda", "action": ("Ir a Proveedores", 0)},
    ], page, on_switch_tab)

    # Left column: form
    form_col = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Registrar compra", size=16, weight=ft.FontWeight.W_500, expand=True),
                        help_comp,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                numero_text,
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Proveedor", size=11, color=t["text_secondary"]),
                                ac_proveedor.control,
                            ],
                            spacing=2, expand=True,
                        ),
                        ft.Column(
                            [
                                ft.Text("Fecha", size=11, color=t["text_secondary"]),
                                fecha_text,
                            ],
                            spacing=2,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Container(
                    content=ft.Column([
                        items_col,
                        ft.Container(
                            content=ft.IconButton(
                                icon=ft.Icons.ADD,
                                icon_size=14,
                                icon_color=t["text_hint"],
                                tooltip="Agregar fila",
                                on_click=lambda e: _add_empty_row(),
                                style=ft.ButtonStyle(padding=ft.padding.all(4)),
                            ),
                            alignment=ft.alignment.center,
                            padding=ft.padding.symmetric(0, 4),
                        ),
                    ], spacing=0, tight=True),
                    expand=True,
                    border=ft.border.all(0.5, t["border_light"]),
                    border_radius=8,
                ),
                ft.Text("Notas", size=11, color=t["text_secondary"]),
                tf_notas,
                ft.Row(
                    [
                        total_text,
                        ft.Row(
                            [
                                ft.OutlinedButton("Limpiar", on_click=lambda e: _limpiar_form()),
                                ft.ElevatedButton("Guardar compra", icon=ft.Icons.SAVE,
                                                  bgcolor=t["accent"], color=t["accent_text"],
                                                  on_click=_guardar),
                            ],
                            spacing=6,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=6, expand=True,
        ),
        padding=ft.padding.only(right=12),
        expand=True,
    )

    # Right column: history
    history_col_wrapper = ft.Container(
        content=ft.Column(
            [
                ft.Text("Historial", size=16, weight=ft.FontWeight.W_500),
                ft.Container(
                    content=history_col,
                    border=ft.border.all(0.5, t["border"]),
                    border_radius=8,
                    expand=True,
                ),
            ],
            spacing=6, expand=True,
        ),
        padding=ft.padding.only(left=12),
        width=400,
    )

    _refresh_history()
    _limpiar_form()

    view = ft.Container(
        content=ft.Row(
            [
                form_col,
                ft.VerticalDivider(width=1, color=t["border_light"]),
                history_col_wrapper,
            ],
            spacing=0,
            expand=True,
        ),
        padding=ft.padding.only(top=8),
        expand=True,
    )

    view.refresh_data = _refresh_history
    return view
