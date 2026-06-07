"""
components/item_row.py
"""
from __future__ import annotations
from typing import Callable
import flet as ft
from services.autocomplete_service import search_productos
from views.facturacion.components.autocomplete import AutocompleteField

def build_item_row(
    page: ft.Page,
    index: int,
    initial: dict | None = None,
    on_remove: Callable[[dict], None] | None = None,
    on_change: Callable[[], None] | None = None,
    on_row_complete: Callable[[], None] | None = None,
    on_select: Callable[[dict], None] | None = None,
    t: dict | None = None,
) -> dict:
    initial = initial or {}
    index_text = ft.Text(str(index), size=11, color=ft.colors.SECONDARY)
    curva_metadata: dict = {"value": None}

    raw_cant = initial.get("cantidad", 1)
    cant_value = str(raw_cant).rstrip("0").rstrip(".") if isinstance(raw_cant, float) else str(raw_cant)
    border_color = t["border"] if t else ft.colors.OUTLINE
    focused_color = t["accent"] if t else ft.colors.PRIMARY

    tf_cant = ft.TextField(
        value=cant_value, width=52, height=34, text_size=13,
        hint_text="Stock",
        content_padding=ft.padding.symmetric(6, 6), border_radius=6,
        keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.CENTER,
        border_color=border_color, focused_border_color=focused_color,
        bgcolor=t["bg_input"] if t else None,
        color=t["text_primary"] if t else None,
        on_change=lambda e: on_change and on_change(),
    )

    tf_precio = ft.TextField(
        value="" if not initial.get("precio_unitario") else str(int(initial.get("precio_unitario"))),
        hint_text="0", width=105, height=34, text_size=13,
        content_padding=ft.padding.symmetric(8, 6), border_radius=6,
        keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT,
        border_color=border_color, focused_border_color=focused_color,
        bgcolor=t["bg_input"] if t else None,
        color=t["text_primary"] if t else None,
        on_change=lambda e: on_change and on_change(),
        on_submit=lambda e: on_row_complete and on_row_complete(),
        read_only=False,
    )

    tf_total = ft.TextField(
        value=_fmt(initial.get("total", 0)), width=95, height=34, text_size=13,
        content_padding=ft.padding.symmetric(8, 6), border_radius=6,
        read_only=True, text_align=ft.TextAlign.RIGHT, border_color=ft.colors.TRANSPARENT,
        bgcolor=ft.colors.SURFACE_VARIANT,
    )

    current_stock_tag = ft.Container(
        ft.Text("", size=9, weight=ft.FontWeight.W_600, color=t["text_secondary"]),
        bgcolor=t["bg_header"], border_radius=4,
        padding=ft.padding.symmetric(2, 5), visible=False,
    )

    def _on_producto_selected(prod: dict) -> None:
        tf_precio.value = str(int(prod.get("precio_unitario", 0)))
        if prod.get("is_curva"):
            ac_detalle.value = f"{prod.get('detalle', '')} - {prod.get('producto_detalle', '')}"
            curva_metadata["value"] = {
                "producto_id": prod["id"],
                "detalle_curva": ac_detalle.value,
                "es_surtida": prod.get("es_surtida", False),
                "color_id": prod.get("color_id"),
                "variante_ids": prod.get("variante_ids", []),
                "precio_total": prod.get("precio_unitario", 0),
            }
        else:
            curva_metadata["value"] = None

        if prod.get("is_variant"):
            ac_detalle.value = f"{prod.get('detalle', '')} - {prod.get('color', '')} {prod.get('talla', '')}".strip(" -")
            stock = prod.get("stock_actual", 0) or 0
            current_stock_tag.content.value = str(int(stock))
            current_stock_tag.visible = True
        else:
            current_stock_tag.visible = False
        if ac_detalle.field.page:
            try: ac_detalle.field.update()
            except Exception: pass
        if tf_precio.page:
            try: tf_precio.update()
            except Exception: pass
        if on_change: on_change()
        if on_select: on_select(prod)

    # 2. Detalle -> Pasa foco a Precio
    ac_detalle = AutocompleteField(
        page=page,
        search_fn=search_productos,
        label_fn=lambda p: (
            f"🔄 {p.get('detalle', '')} - {p.get('producto_detalle', '')}" if p.get("is_curva")
            else f"{p.get('detalle', '')} - {p.get('color', '')} {p.get('talla', '')}".strip(" -") if p.get("is_variant")
            else p.get("detalle", "")
        ),
        sublabel_fn=lambda p: f"${int(p.get('precio_unitario', 0)):,}".replace(",", "."),
        on_select=_on_producto_selected,
        hint_text="Descripcion del producto...",
        expand=True,
        t=t,
        on_change=lambda e: on_change and on_change(),
        on_submit_next=lambda: tf_precio.focus()
    )
    if initial.get("detalle"):
        ac_detalle.value = initial["detalle"]

    # Conectar el salto de Cantidad a Detalle
    tf_cant.on_submit = lambda e: ac_detalle.focus()

    item_data: dict = {
        "cant": tf_cant, "detalle_ac": ac_detalle, "precio": tf_precio,
        "total_tf": tf_total, "row": None, "index_text": index_text,
        "curva_metadata": curva_metadata,
    }

    row = ft.Container(
        content=ft.Row(
            [
                ft.Container(index_text, width=20, alignment=ft.alignment.center),
                tf_cant, current_stock_tag,
                ft.Container(content=ac_detalle.control, expand=True),
                tf_precio, tf_total,
                ft.IconButton(
                    ft.icons.REMOVE_CIRCLE_OUTLINE, icon_color=ft.colors.ERROR,
                    icon_size=16, tooltip="Quitar fila",
                    on_click=lambda e: on_remove and on_remove(item_data),
                    style=ft.ButtonStyle(padding=ft.padding.all(4)),
                ),
            ],
            spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(0, 0),
    )
    item_data["row"] = row

    return item_data

def _fmt(val) -> str:
    try:
        cleaned = str(val).replace(".", "").replace(",", ".") or "0"
        return ("$" + f"{int(float(cleaned)):,}").replace(",", ".")
    except Exception: return "$0"