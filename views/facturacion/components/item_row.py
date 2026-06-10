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
    initial: dict | None = None,
    on_remove: Callable[[dict], None] | None = None,
    on_change: Callable[[], None] | None = None,
    on_row_complete: Callable[[], None] | None = None,
    on_select: Callable[[dict], None] | None = None,
    t: dict | None = None,
    row_index: int = 0,
) -> dict:
    initial = initial or {}
    curva_metadata: dict = {"value": None}

    raw_cant = initial.get("cantidad", 1)
    cant_value = str(raw_cant).rstrip("0").rstrip(".") if isinstance(raw_cant, float) else str(raw_cant)
    tf_cant = ft.TextField(
        value=cant_value, width=52, height=34, text_size=13,
        hint_text="Stock",
        content_padding=ft.padding.symmetric(6, 6),
        border_radius=ft.border_radius.only(top_left=6, bottom_left=6),
        keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.CENTER,
        border_color=t["border_light"] if t else ft.Colors.OUTLINE_VARIANT,
        focused_border_color=t["accent"] if t else ft.Colors.PRIMARY,
        bgcolor=t["bg_input"] if t else None,
        color=t["text_primary"] if t else None,
        on_change=lambda e: on_change and on_change(),
    )

    tf_precio = ft.TextField(
        value="" if not initial.get("precio_unitario") else str(int(initial.get("precio_unitario"))),
        hint_text="0", width=105, height=34, text_size=13,
        content_padding=ft.padding.symmetric(8, 6), border_radius=0,
        keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT,
        border_color=ft.Colors.TRANSPARENT, focused_border_color=ft.Colors.TRANSPARENT,
        bgcolor=t["bg_input"] if t else None,
        color=t["text_primary"] if t else None,
        on_change=lambda e: on_change and on_change(),
        on_submit=lambda e: on_row_complete and on_row_complete(),
        read_only=False,
    )

    tf_total = ft.TextField(
        value=_fmt(initial.get("total", 0)), width=95, height=34, text_size=13,
        content_padding=ft.padding.symmetric(8, 6),
        border_radius=ft.border_radius.only(top_right=6, bottom_right=6),
        read_only=True, text_align=ft.TextAlign.RIGHT,
        border_color=t["border_light"] if t else ft.Colors.OUTLINE_VARIANT,
        focused_border_color=t["accent"] if t else ft.Colors.PRIMARY,
        bgcolor=t["bg_input"] if t else ft.Colors.SURFACE_CONTAINER_HIGHEST,
        color=t["text_primary"] if t else None,
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
            item_data["producto_id"] = prod.get("id")
            item_data["variante_id"] = prod.get("variante_id")
        else:
            item_data["producto_id"] = prod.get("id")
            item_data["variante_id"] = None

        if ac_detalle.field.page:
            try: ac_detalle.field.update()
            except Exception: pass
        if tf_precio.page:
            try: tf_precio.update()
            except Exception: pass
        if on_change: on_change()
        if on_select: on_select(prod)

    def _on_detail_change(e=None):
        if on_change:
            on_change()

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
        on_change=_on_detail_change,
        on_submit_next=lambda: tf_precio.focus(),
        allow_free_text=False,
    )
    ac_detalle.field.border_radius = 0
    ac_detalle.field.border_color = ft.Colors.TRANSPARENT
    ac_detalle.field.focused_border_color = ft.Colors.TRANSPARENT
    ac_detalle.field.height = 34
    ac_detalle.field.expand = True
    if initial.get("detalle"):
        ac_detalle.value = initial["detalle"]

    tf_cant.on_submit = lambda e: ac_detalle.focus()

    row_bg = t["bg_card"] if row_index % 2 == 0 else t.get("bg_row_odd", t["bg_card"]) if t else None
    row = ft.Container(
        content=ft.Row(
            [
                tf_cant,
                ac_detalle.control,
                tf_precio, tf_total,
                ft.IconButton(
                    ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=ft.Colors.ERROR,
                    icon_size=16, tooltip="Quitar fila",
                    on_click=lambda e: on_remove and on_remove(item_data),
                    style=ft.ButtonStyle(padding=ft.padding.all(4)),
                ),
            ],
            spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(0, 4),
        bgcolor=row_bg,
        border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"] if t else ft.Colors.OUTLINE_VARIANT)),
    )

    item_data: dict = {
        "cant": tf_cant, "detalle_ac": ac_detalle, "precio": tf_precio,
        "total_tf": tf_total, "row": row,
        "curva_metadata": curva_metadata,
        "producto_id": None, "variante_id": None,
        "row_index": row_index,
    }

    if initial.get("producto_id"):
        item_data["producto_id"] = initial["producto_id"]
    if initial.get("variante_id"):
        item_data["variante_id"] = initial["variante_id"]

    return item_data


def update_row_zebra(item_data: dict, row_index: int, t: dict) -> None:
    item_data["row_index"] = row_index
    row_bg = t["bg_card"] if row_index % 2 == 0 else t.get("bg_row_odd", t["bg_card"])
    item_data["row"].bgcolor = row_bg


def _fmt(val) -> str:
    try:
        return ("$" + f"{int(float(val)):,}").replace(",", ".")
    except Exception: return "$0"