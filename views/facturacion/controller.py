"""
controller.py
Logica de negocio de la vista de facturacion.

La clase FacturacionController recibe en su constructor:
  - page    : ft.Page
  - state   : FacturacionState
  - ui      : FacturacionUI  (dataclass con referencias a los controles)

De esta forma la vista (view.py) construye la UI, crea el controller
pasandole esas referencias, y el controller nunca importa nada de la capa
de presentacion directamente — solo opera sobre los controles que recibe.
"""
from __future__ import annotations

import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

import flet as ft

from db.database import (
    get_factura_by_numero,
    get_facturas,
    save_factura,
    save_from_factura,
    update_factura,
    procesar_stock_factura,
    revertir_stock_factura,
    save_curva_pendiente,
)

from services.autocomplete_service import search_clientes
from services.invoice_share import render_invoice_image
from services.whatsapp_service import (
    copy_image_to_clipboard,
    paste_clipboard_image,
    share_invoice,
)
from views.facturacion.components.autocomplete import AutocompleteField
from views.facturacion.components.item_row import build_item_row
from views.facturacion.state import FacturacionState

log = logging.getLogger("mvp10")


# ── Helpers de formato (modulo-nivel, reutilizables) ──────────────────────────

def fmt(val) -> str:
    """Formatea un numero como $1.234.567 (separador de miles con punto)."""
    try:
        cleaned = str(val).replace(".", "").replace(",", ".") or "0"
        return ("$" + f"{int(float(cleaned)):,}").replace(",", ".")
    except Exception:
        return "$0"


def parse_num(raw: str) -> float:
    """Parsea strings como '1.234' o '1,234.56' a float."""
    try:
        return float(str(raw).replace(".", "").replace(",", ".").strip() or 0)
    except Exception:
        return 0.0


# ── Dataclass liviano de referencias UI ───────────────────────────────────────

class FacturacionUI:
    """
    Agrupa las referencias a los controles de UI que el controller necesita
    mutar. Se construye en view.py y se pasa al controller.

    No es un ft.Control — es un simple objeto contenedor.
    """

    __slots__ = (
        "page",
        "numero_text",
        "fecha_text",
        "status_chip",
        "total_text",
        "items_col",
        "history_col",
        "ac_cliente",
        "tf_provincia",
        "tf_transporte",
        "tf_tel",
        "tf_seña",
        "sub_reference_text",
        "t",
    )

    def __init__(
        self,
        page: ft.Page,
        numero_text: ft.Text,
        fecha_text: ft.Text,
        status_chip: ft.Text,
        total_text: ft.Text,
        items_col: ft.ListView,
        history_col: ft.ListView,
        ac_cliente: AutocompleteField,
        tf_provincia: ft.TextField,
        tf_transporte: ft.TextField,
        tf_tel: ft.TextField,
        tf_seña: ft.TextField,
        sub_reference_text: ft.Text,
        t: dict,
    ) -> None:
        self.page = page
        self.numero_text = numero_text
        self.fecha_text = fecha_text
        self.status_chip = status_chip
        self.total_text = total_text
        self.items_col = items_col
        self.history_col = history_col
        self.ac_cliente = ac_cliente
        self.tf_provincia = tf_provincia
        self.tf_transporte = tf_transporte
        self.tf_tel = tf_tel
        self.tf_seña = tf_seña
        self.sub_reference_text = sub_reference_text
        self.t = t


# ── Controller ─────────────────────────────────────────────────────────────────

class FacturacionController:
    """
    Contiene toda la logica de negocio de la vista de facturacion.
    Los metodos publicos son los que se enlazan a los callbacks de la UI.
    """

    def __init__(
        self,
        state: FacturacionState,
        ui: FacturacionUI,
        on_factura_guardada: Callable | None = None,
    ) -> None:
        self._s = state
        self._ui = ui
        self._on_factura_guardada = on_factura_guardada

    # ── Helpers internos ───────────────────────────────────────────────────────

    def _is_mounted(self, control: ft.Control) -> bool:
        return getattr(control, "page", None) is not None

    def _safe_update(self, control: ft.Control) -> None:
        if self._is_mounted(control):
            try:
                control.update()
            except Exception as exc:
                log.debug(f"safe_update ignored: {exc}")

    def _show_message(self, text: str, color=ft.colors.PRIMARY) -> None:
        page = self._ui.page
        if page is None:
            return
        sb = ft.SnackBar(
            ft.Text(text, color=ft.colors.ON_PRIMARY),
            bgcolor=color,
            duration=3200,
        )
        page.open(sb)

    # ── Estado de guardado ─────────────────────────────────────────────────────

    def mark_dirty(self) -> None:
        if self._s.suppress_dirty:
            return
        self._s.is_saved = False
        self._ui.status_chip.value = "Sin guardar"
        self._ui.status_chip.color = ft.colors.TERTIARY
        self._safe_update(self._ui.status_chip)

    def _set_saved_state(self, numero: str) -> None:
        self._s.current_numero = numero
        self._s.is_saved = True
        self._ui.numero_text.value = numero
        self._ui.status_chip.value = "Guardada"
        self._ui.status_chip.color = ft.colors.PRIMARY
        self._safe_update(self._ui.numero_text)
        self._safe_update(self._ui.status_chip)

    def _set_new_state(self) -> None:
        self._s.is_saved = False
        self._s.current_numero = None
        self._ui.status_chip.value = "Sin guardar"
        self._ui.status_chip.color = ft.colors.TERTIARY
        self._safe_update(self._ui.status_chip)

    def _set_next_numero(self) -> None:
        existing = get_facturas(1)
        if existing:
            raw = str(existing[0].get("numero") or "")
            m = re.search(r"(\d+)$", raw)
            last_num = int(m.group(1)) if m else 10249
            self._ui.numero_text.value = f"F-{last_num + 1}"
        else:
            self._ui.numero_text.value = "F-10250"
        self._safe_update(self._ui.numero_text)

    # ── Coleccion de datos ─────────────────────────────────────────────────────

    def collect_items(self) -> list[dict]:
        return [
            {
                "cantidad": parse_num(item["cant"].value or "1"),
                "detalle": item["detalle_ac"].value or "",
                "precio_unitario": parse_num(item["precio"].value),
                "total": parse_num(
                    item["total_tf"].value.replace("$", "").replace(".", "")
                ),
            }
            for item in self._s.items_controls
            if (item["detalle_ac"].value or "").strip()
        ]

    def collect_factura_data(self) -> dict:
        return {
            "fecha": self._ui.fecha_text.value or datetime.now().strftime("%d/%m/%Y"),
            "cliente": self._ui.ac_cliente.value or "",
            "domicilio": self._ui.tf_provincia.value or "",
            "telefono": self._ui.tf_tel.value or "",
            "envio": 0,
            "total": self._s.original_total,
            "seña": parse_num(self._ui.tf_seña.value or "0"),
            "tipo_entrega": "",
            "fecha_estimada": "",
            "empresa_envio": self._ui.tf_transporte.value or "",
        }

    # ── Items ──────────────────────────────────────────────────────────────────

    def recalculate(self, mark_dirty: bool = False) -> None:
        subtotal = 0.0
        for item in self._s.items_controls:
            cant = parse_num(item["cant"].value or "1")
            precio = parse_num(item["precio"].value or "0")
            line_total = cant * precio
            item["total_tf"].value = fmt(line_total)
            self._safe_update(item["total_tf"])
            subtotal += line_total
        self._s.original_total = subtotal
        seña = parse_num(self._ui.tf_seña.value or "0")
        displayed = max(0, subtotal - seña)
        self._ui.total_text.value = f"$ {int(displayed):,}".replace(",", ".")
        if seña > 0:
            self._ui.sub_reference_text.value = f"subtotal $ {int(subtotal):,}".replace(",", ".")
        else:
            self._ui.sub_reference_text.value = ""
        self._safe_update(self._ui.total_text)
        self._safe_update(self._ui.sub_reference_text)
        if mark_dirty:
            self.mark_dirty()

    def _renumber_rows(self) -> None:
        for idx, item in enumerate(self._s.items_controls, start=1):
            item["index_text"].value = str(idx)
            self._safe_update(item["index_text"])

    def remove_item(self, item_data: dict) -> None:
        if item_data in self._s.items_controls:
            self._s.items_controls.remove(item_data)
        if item_data["row"] in self._ui.items_col.controls:
            self._ui.items_col.controls.remove(item_data["row"])
        self._renumber_rows()
        self.recalculate(mark_dirty=True)
        self._safe_update(self._ui.items_col)

    def add_item(self, initial: dict | None = None, auto_focus: bool = False) -> None:
        index = len(self._s.items_controls) + 1
        
        # Callback para cuando el usuario presiona Enter en el precio de esta fila
        def _on_row_complete():
            current_index = next(
                (i for i, it in enumerate(self._s.items_controls) if it is item_data), None
            )
            if current_index is not None:
                next_index = current_index + 1
                if next_index < len(self._s.items_controls):
                    try:
                        self._s.items_controls[next_index]["cant"].focus()
                    except Exception:
                        pass
                    return
            # No hay fila siguiente — crear una nueva
            if self._ui.page:
                self._ui.page.update()
            new_item = self.add_item()
            if new_item and self._ui.page:
                self._ui.page.update()
                try:
                    new_item["cant"].focus()
                except Exception:
                    pass

        item_data = build_item_row(
            page=self._ui.page,
            index=index,
            initial=initial,
            on_remove=self.remove_item,
            on_change=lambda: self.recalculate(mark_dirty=True),
            on_row_complete=_on_row_complete,
            t=self._ui.t,
        )
        self._s.items_controls.append(item_data)
        self._ui.items_col.controls.append(item_data["row"])
        self._safe_update(self._ui.items_col)
        
        # Si se pidio auto_focus (por ej, al darle enter a la fila anterior)
        # Si se pidio auto_focus (por ej, al darle enter a la fila anterior)
        if auto_focus and self._ui.page:
            self._ui.page.update()
            try:
                item_data["cant"].focus()
            except Exception:
                pass
        return item_data
    def _add_row_and_focus(self) -> None:
        """Crea una nueva fila y mueve el foco a su campo cantidad."""
        new_item = self.add_item()
        if new_item:
            try:
                new_item["cant"].focus()
            except Exception:
                pass
    def clear_items(self) -> None:
        self._s.items_controls.clear()
        self._ui.items_col.controls.clear()

    # ── Historial ──────────────────────────────────────────────────────────────

    def set_history_filter(self, value: str) -> None:
        self._s.history_filter = (value or "").strip().lower()
        self.refresh_history()

    def _get_history_rows(self) -> list[dict]:
        rows = get_facturas(200)
        query = self._s.history_filter
        if not query:
            return rows
        filtered = []
        for row in rows:
            haystack = " ".join([
                str(row.get("numero", "")),
                str(row.get("fecha", "")),
                str(row.get("cliente_nombre", "")),
            ]).lower()
            if query in haystack:
                filtered.append(row)
        return filtered

    def load_relative_factura(self, step: int) -> None:
        """
        step=+1 → factura mas vieja (Anterior)
        step=-1 → factura mas nueva (Siguiente)
        """
        rows = self._get_history_rows()
        if not rows:
            self._show_message("No hay facturas en el historial.", ft.colors.TERTIARY)
            return
        if not self._s.current_numero:
            self.load_factura(rows[0]["numero"])
            return
        current_index = next(
            (i for i, r in enumerate(rows) if r["numero"] == self._s.current_numero),
            None,
        )
        if current_index is None:
            self.load_factura(rows[0]["numero"])
            return
        next_index = current_index + step
        if 0 <= next_index < len(rows):
            self.load_factura(rows[next_index]["numero"])
        else:
            self._show_message("No hay mas facturas en esa direccion.", ft.colors.TERTIARY)

    def load_factura(self, numero: str) -> None:
        factura = get_factura_by_numero(numero)
        if not factura:
            self._show_message("No se pudo cargar la factura.", ft.colors.ERROR)
            return

        self._s.suppress_dirty = True
        try:
            ui = self._ui
            ui.ac_cliente.value = factura.get("cliente_nombre", "")
            self._safe_update(ui.ac_cliente.field)
            ui.tf_provincia.value = factura.get("domicilio", "")
            ui.tf_tel.value = factura.get("telefono", "")
            ui.tf_transporte.value = factura.get("empresa_envio", "")
            ui.fecha_text.value = factura.get("fecha", datetime.now().strftime("%d/%m/%Y"))
            ui.numero_text.value = factura.get("numero", "")

            seña_val = factura.get("seña", 0) or 0
            ui.tf_seña.value = f"{int(seña_val):,}".replace(",", ".") if seña_val else ""

            self.clear_items()
            items = factura.get("items", [])
            if items:
                for item in items:
                    self.add_item(item)
            else:
                for _ in range(6):
                    self.add_item()

            self.recalculate()
            self._set_saved_state(factura["numero"])
            self._s.last_generated_image = None
            self.refresh_history()

            if ui.page:
                try:
                    ui.page.update()
                except Exception:
                    pass
        finally:
            self._s.suppress_dirty = False

    def _build_history_row_widget(self, row: dict, zebra: bool) -> ft.Container:
        is_active = self._s.current_numero == row["numero"]
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(row["numero"], size=12, color=ft.colors.PRIMARY, width=62),
                    ft.Text(row["fecha"], size=11, color=ft.colors.SECONDARY, width=72),
                    ft.Text(
                        row["cliente_nombre"] or "",
                        size=12,
                        expand=True,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        fmt(row["total"] or 0),
                        size=12,
                        weight=ft.FontWeight.W_500,
                        width=70,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ],
                spacing=4,
            ),
            padding=ft.padding.symmetric(7, 12),
            bgcolor=(
                ft.colors.PRIMARY_CONTAINER
                if is_active
                else (ft.colors.SURFACE if zebra else ft.colors.SURFACE_VARIANT)
            ),
            border=ft.border.only(
                bottom=ft.border.BorderSide(0.5, ft.colors.OUTLINE_VARIANT)
            ),
            ink=True,
            on_click=lambda e, num=row["numero"]: self.load_factura(num),
            tooltip=f"Abrir factura {row['numero']}",
        )

    def refresh_history(self) -> None:
        hc = self._ui.history_col
        hc.controls.clear()

        # Cabecera
        hc.controls.append(
            ft.Container(
                ft.Row(
                    [
                        ft.Text("N°", size=11, weight=ft.FontWeight.W_500,
                                color=ft.colors.SECONDARY, width=62),
                        ft.Text("Fecha", size=11, weight=ft.FontWeight.W_500,
                                color=ft.colors.SECONDARY, width=72),
                        ft.Text("Cliente", size=11, weight=ft.FontWeight.W_500,
                                color=ft.colors.SECONDARY, expand=True),
                        ft.Text("$", size=11, weight=ft.FontWeight.W_500,
                                color=ft.colors.SECONDARY, width=70,
                                text_align=ft.TextAlign.RIGHT),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(8, 12),
                bgcolor=ft.colors.SURFACE_VARIANT,
                border=ft.border.only(
                    bottom=ft.border.BorderSide(0.5, ft.colors.OUTLINE_VARIANT)
                ),
            )
        )

        rows = self._get_history_rows()
        if not rows:
            hc.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.HISTORY, size=36, color=ft.colors.SECONDARY),
                            ft.Text("Sin resultados.", size=14, weight=ft.FontWeight.W_500),
                            ft.Text(
                                "No encontramos facturas con ese filtro.",
                                size=12,
                                color=ft.colors.SECONDARY,
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(24),
                    expand=True,
                )
            )
        else:
            for i, row in enumerate(rows):
                hc.controls.append(self._build_history_row_widget(row, i % 2 == 0))

        self._safe_update(hc)

    # ── Guardar ────────────────────────────────────────────────────────────────

    def save(self, e=None) -> None:
        items_data = self.collect_items()
        if not items_data:
            self._show_message(
                "Agrega al menos un item antes de guardar.", ft.colors.TERTIARY
            )
            return
        data = self.collect_factura_data()
        try:
            if self._s.current_numero:
                revertir_stock_factura(self._s.current_numero)
                numero = update_factura(self._s.current_numero, data, items_data)
                ordenes = procesar_stock_factura(numero, data.get("cliente", ""), items_data)
                msg = f"Factura {numero} actualizada correctamente"
            else:
                numero = save_factura(data, items_data)
                ordenes = procesar_stock_factura(numero, data.get("cliente", ""), items_data)
                msg = f"Factura {numero} guardada correctamente"

            self._show_message(msg)

            # ── Curvas pendientes ──────────────────────────────────────────
            factura = get_factura_by_numero(numero)
            if factura:
                for item in self._s.items_controls:
                    cm = item.get("curva_metadata", {}).get("value")
                    if cm:
                        save_curva_pendiente({
                            "factura_id": factura["id"],
                            "factura_numero": numero,
                            "producto_id": cm["producto_id"],
                            "detalle_curva": cm["detalle_curva"],
                            "es_surtida": cm["es_surtida"],
                            "color_id": cm.get("color_id"),
                            "variante_ids": ",".join(str(vid) for vid in cm["variante_ids"]),
                            "cantidad": parse_num(item["cant"].value or "1"),
                            "precio_total": cm["precio_total"],
                        })

            save_from_factura(
                {
                    "nombre": data.get("cliente", ""),
                    "domicilio": data.get("domicilio", ""),
                    "telefono": data.get("telefono", ""),
                },
                items_data,
                numero_factura=numero,
                total=data.get("total", 0),
                seña=data.get("seña", 0),
            )
            self._set_saved_state(numero)
            self.refresh_history()
            self._s.last_generated_image = None

            if self._on_factura_guardada:
                self._on_factura_guardada()
            if self._ui.page:
                try:
                    self._ui.page.update()
                except Exception:
                    pass
        except Exception as error:
            log.error(f"Error en save: {error}", exc_info=True)
            self._show_message(f"Error al guardar: {error}", ft.colors.ERROR)

    # ── Nueva ──────────────────────────────────────────────────────────────────

    def nueva(self, e=None) -> None:
        self._s.suppress_dirty = True
        try:
            ui = self._ui
            ui.ac_cliente.value = ""
            self._safe_update(ui.ac_cliente.field)
            ui.tf_provincia.value = ""
            ui.tf_transporte.value = ""
            ui.tf_tel.value = ""
            ui.tf_seña.value = ""
            ui.fecha_text.value = datetime.now().strftime("%d/%m/%Y")

            self.clear_items()
            for _ in range(8):
                self.add_item()

            self._set_next_numero()
            self._set_new_state()
            self._s.last_generated_image = None
            self.recalculate()
            self.refresh_history()

            if ui.page:
                try:
                    ui.page.update()
                except Exception:
                    pass
        finally:
            self._s.suppress_dirty = False

    # ── WhatsApp ───────────────────────────────────────────────────────────────

    def _prepare_whatsapp_share(self) -> Path | None:
        if not self._s.current_numero or not self._s.is_saved:
            self._show_message(
                "Primero debes guardar la factura antes de compartir.",
                ft.colors.TERTIARY,
            )
            return None
        items_data = self.collect_items()
        if not items_data:
            self._show_message(
                "La factura no tiene items para compartir.", ft.colors.TERTIARY
            )
            return None
        data = self.collect_factura_data()
        data["numero"] = self._s.current_numero
        try:
            image_path = render_invoice_image(
                data,
                items_data,
                f"presupuesto_{self._s.current_numero.lower()}",
            )
            self._s.last_generated_image = str(image_path)
            return image_path
        except Exception as error:
            self._show_message(f"No se pudo generar la imagen: {error}", ft.colors.ERROR)
            return None

    def share_whatsapp(self, e=None) -> None:
        # 1. Generar la imagen del comprobante
        image_path = self._prepare_whatsapp_share()
        if not image_path:
            return

        try:
            # 2. Copiar la imagen al portapapeles y abrir WhatsApp (Web o App)
            result = share_invoice(image_path)
            if result.get("error"):
                self._show_message(f"Error al abrir WhatsApp: {result['error']}", ft.colors.ERROR)
                return

            # 3. Mostrar un aviso cortito en la app para confirmar
            self._show_message("Abriendo WhatsApp... Buscá el recuadro verde en la esquina.", ft.colors.PRIMARY)

            # 4. Lanzar nuestra nueva herramienta flotante (encima del sistema operativo)
            from services.whatsapp_service import show_floating_paste_button
            show_floating_paste_button()

        except Exception as ex:
            self._show_message(f"Error al procesar: {ex}", ft.colors.ERROR)
            return
