"""
view.py
Capa de presentacion de la vista de facturacion.

Responsabilidades:
  - Construir todos los controles de Flet
  - Instanciar FacturacionState, FacturacionUI y FacturacionController
  - Enlazar callbacks de UI -> controller
  - Registrar y limpiar el keyboard handler (dispose)

NO contiene logica de negocio ni accesos a la DB.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable

import flet as ft

from services.autocomplete_service import search_clientes
from views.facturacion.components.autocomplete import AutocompleteField
from views.facturacion.controller import FacturacionController, FacturacionUI
from views.facturacion.state import FacturacionState
from theme import get_theme, page_title, section_label


from views.flow_guide import HelpButton

from db.database import get_curvas_pendientes, resolver_curva, get_variantes_con_producto

def FacturacionView(
    page: ft.Page,
    on_factura_guardada: Callable | None = None,
    on_switch_tab: Callable | None = None,
) -> ft.Container:
    """
    Construye y devuelve el widget raíz de la vista de facturación.

    El widget expone dos atributos adicionales:
        .refresh_data  → llama a controller.refresh_history()
        .dispose       → restaura el keyboard handler previo (llamar al desmontar)
    """

    # ── Estado ─────────────────────────────────────────────────────────────────
    state = FacturacionState()

    t = get_theme(page)

    # ── Controles fijos (necesarios antes de crear UI y Controller) ────────────
    numero_text = ft.Text(
        "", size=17, weight=ft.FontWeight.W_500, color=t["accent"]
    )
    fecha_text = ft.Text(
        datetime.now().strftime("%d/%m/%Y"),
        size=13,
        color=t["text_secondary"],
    )
    status_chip = ft.Text(
        "Sin guardar",
        size=12,
        weight=ft.FontWeight.W_500,
        color=t["accent"],
    )
    total_text = ft.Text(
        "$ 0", size=32, weight=ft.FontWeight.W_700, color=t["accent"]
    )
    items_col = ft.ListView(spacing=0, expand=True, auto_scroll=False)
    history_col = ft.ListView(spacing=0, expand=True, auto_scroll=False)

    # ── Campos de cliente ──────────────────────────────────────────────────────
    tf_provincia = ft.TextField(
        hint_text="Provincia",
        border_radius=7,
        height=38,
        text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        expand=True,
        border_color=t["border"],
        focused_border_color=t["accent"],
        bgcolor=t["bg_input"],
        color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )
    tf_transporte = ft.TextField(
        hint_text="Transporte",
        border_radius=7,
        height=38,
        text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        width=140,
        border_color=t["border"],
        focused_border_color=t["accent"],
        bgcolor=t["bg_input"],
        color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )
    tf_tel = ft.TextField(
        hint_text="Telefono / WhatsApp",
        border_radius=7,
        height=38,
        text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        width=190,
        border_color=t["border"],
        focused_border_color=t["accent"],
        bgcolor=t["bg_input"],
        color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )

    # on_change se enlaza después de crear el controller
    ac_cliente = AutocompleteField(
        page=page,
        search_fn=search_clientes,
        label_fn=lambda c: c.get("nombre", ""),
        sublabel_fn=lambda c: c.get("telefono", "") or "",
        hint_text="Nombre del cliente",
        expand=True,
        t=t,
        on_submit_next=lambda: tf_tel.focus(),
    )

    tf_history_search = ft.TextField(
        hint_text="Buscar por numero, fecha o cliente",
        border_radius=7,
        height=38,
        text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        expand=True,
        border_color=t["border"],
        focused_border_color=t["accent"],
        prefix_icon=ft.Icons.SEARCH,
        bgcolor=t["bg_input"],
        color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )

    # ── Seña y subtotal de referencia ───────────────────────────────────────────
    tf_seña = ft.TextField(
        hint_text="$ 0",
        border_radius=7,
        height=36,
        text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        width=210,
        border_color=t["border"],
        focused_border_color=t["accent"],
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=t["bg_input"],
        color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )
    sub_reference_text = ft.Text(
        "", size=10, color=t["text_secondary"],
    )

    # ── UI bundle ──────────────────────────────────────────────────────────────
    ui = FacturacionUI(
        page=page,
        numero_text=numero_text,
        fecha_text=fecha_text,
        status_chip=status_chip,
        total_text=total_text,
        items_col=items_col,
        history_col=history_col,
        ac_cliente=ac_cliente,
        tf_provincia=tf_provincia,
        tf_transporte=tf_transporte,
        tf_tel=tf_tel,
        tf_seña=tf_seña,
        sub_reference_text=sub_reference_text,
        t=t,
    )

    # ── Controller ─────────────────────────────────────────────────────────────
    ctrl = FacturacionController(
        state=state,
        ui=ui,
        on_factura_guardada=on_factura_guardada,
    )

    # ── Enlazar callbacks que dependen del controller ──────────────────────────
    tf_provincia.on_change = lambda e: ctrl.mark_dirty()
    tf_provincia.on_submit = lambda e: tf_transporte.focus()
    tf_transporte.on_change = lambda e: ctrl.mark_dirty()
    tf_transporte.on_submit = lambda e: _focus_first_item_cant()
    tf_seña.on_change = lambda e: (ctrl.recalculate(mark_dirty=True), None)[1]
    tf_tel.on_change = lambda e: ctrl.mark_dirty()
    tf_tel.on_submit = lambda e: tf_provincia.focus()
    tf_history_search.on_change = lambda e: ctrl.set_history_filter(e.control.value)
    ac_cliente._user_on_change = lambda e: ctrl.mark_dirty()
    ac_cliente._on_select = lambda c: (
        tf_provincia.__setattr__("value", c.get("domicilio", ""))
        or tf_tel.__setattr__("value", c.get("telefono", ""))
        or tf_transporte.__setattr__("value", c.get("empresa_envio", ""))
        or _safe_update(tf_provincia)
        or _safe_update(tf_tel)
        or _safe_update(tf_transporte)
        or ctrl.mark_dirty()
    )

    def _safe_update(control: ft.Control) -> None:
        if getattr(control, "page", None):
            try:
                control.update()
            except Exception:
                pass

    # Cliente seleccionado: necesita actualizar domicilio y tel en la UI
    def _on_cliente_selected(cliente: dict) -> None:
        tf_provincia.value = cliente.get("domicilio", "")
        tf_tel.value = cliente.get("telefono", "")
        tf_transporte.value = cliente.get("empresa_envio", "")
        _safe_update(tf_provincia)
        _safe_update(tf_tel)
        _safe_update(tf_transporte)
        ctrl.mark_dirty()

    ac_cliente._on_select = _on_cliente_selected

    def _focus_first_item_cant() -> None:
        if state.items_controls:
            try:
                state.items_controls[0]["cant"].focus()
            except Exception:
                pass

    # ── Hotkeys ────────────────────────────────────────────────────────────────
    _previous_keyboard_handler = page.on_keyboard_event

    def _on_keyboard(e: ft.KeyboardEvent) -> None:
        if not getattr(items_col, "page", None):
            if _previous_keyboard_handler:
                try:
                    _previous_keyboard_handler(e)
                except Exception:
                    pass
            return
        if e.key == "F1":
            ctrl.save()
        elif e.key == "F2":
            ctrl.nueva()
        elif _previous_keyboard_handler:
            try:
                _previous_keyboard_handler(e)
            except Exception:
                pass

    page.on_keyboard_event = _on_keyboard

    # ── Botones de acción ──────────────────────────────────────────────────────
    btn_guardar = ft.ElevatedButton(
        "Guardar  [F1]",
        icon=ft.Icons.SAVE_OUTLINED,
        on_click=ctrl.save,
        bgcolor=t["accent"],
        color=t["accent_text"],
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(10, 14),
        ),
        width=210,
    )

    btn_nueva = ft.ElevatedButton(
        "Nueva  [F2]",
        icon=ft.Icons.ADD,
        on_click=ctrl.nueva,
        bgcolor=t["bg_card"],
        color=t["accent"],
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(10, 14),
            side=ft.BorderSide(1, t["accent_light"]),
        ),
        width=210,
    )

    btn_whatsapp = ft.OutlinedButton(
        "Compartir WhatsApp",
        icon=ft.Icons.SHARE_OUTLINED,
        width=210,
        on_click=ctrl.share_whatsapp,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(10, 14),
            color=ft.Colors.GREEN_700,
            side=ft.BorderSide(1, ft.Colors.GREEN_200),
        ),
    )

    btn_eliminar = ft.OutlinedButton(
        "Eliminar factura",
        icon=ft.Icons.DELETE_OUTLINE,
        width=210,
        on_click=ctrl.delete,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(10, 14),
            color=ft.Colors.RED_700,
            side=ft.BorderSide(1, ft.Colors.RED_300),
        ),
    )

    # ── Panel izquierdo (acciones) ─────────────────────────────────────────────
    left_panel = ft.Container(
        content=ft.Column(
            [
                section_label("Acciones", t),
                ft.Divider(height=1, color=t["border_light"]),

                # Tarjeta de total
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Seña",
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=t["text_secondary"],
                            ),
                            tf_seña,
                            ft.Divider(height=1, color=t["border_light"]),
                            ft.Text(
                                "TOTAL",
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=t["text_secondary"],
                            ),
                            total_text,
                            sub_reference_text,
                            status_chip,
                        ],
                        spacing=4,
                    ),
                    padding=ft.padding.all(16),
                    bgcolor=t["bg_card"],
                    border=ft.border.all(1, t["border_light"]),
                    border_radius=10,
                    width=210,
                ),

                ft.Container(height=4),
                btn_guardar,
                btn_nueva,

                ft.Divider(height=1, color=t["border_light"]),
                btn_whatsapp,

                ft.Divider(height=1, color=t["border_light"]),
                btn_eliminar,
            ],
            spacing=10,
        ),
        width=240,
        padding=ft.padding.all(20),
        bgcolor=t["bg_card"],
        border=ft.border.only(
            right=ft.border.BorderSide(0.5, t["border_light"])
        ),
    )

    # ── Cabecera de columnas de ítems ──────────────────────────────────────────
    items_header = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    ft.Text("CANT.", size=10, color=t["text_secondary"], weight=ft.FontWeight.W_600),
                    width=52,
                ),
                ft.Container(
                    ft.Text("DETALLE", size=10, color=t["text_secondary"], weight=ft.FontWeight.W_600),
                    expand=True,
                ),
                ft.Container(
                    ft.Text("P. UNIT.", size=10, color=t["text_secondary"], weight=ft.FontWeight.W_600),
                    width=105,
                ),
                ft.Container(
                    ft.Text("TOTAL", size=10, color=t["text_secondary"], weight=ft.FontWeight.W_600),
                    width=95,
                ),
                ft.Container(width=32),
            ],
            spacing=0,
        ),
        padding=ft.padding.symmetric(6, 4),
        bgcolor=t["bg_header"],
    )

    # ── Panel central ──────────────────────────────────────────────────────────
    help_fact = HelpButton([
        {"text": "Elegí o creá un cliente", "action": ("Ir a Clientes", 2)},
        {"text": "Agregá productos (cantidad + precio)"},
        {"text": "Guardá la factura"},
        {"text": "Volvé al Dashboard para cobrar", "action": ("Ir a Dashboard", 0)},
    ], page, on_switch_tab)

    center = ft.Container(
        content=ft.Column(
            [
                # Header de la factura
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    page_title("PRESUPUESTO", t),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            help_fact,
                            ft.Column(
                                [
                                    ft.Text(
                                        "PRESUPUESTO",
                                        size=12,
                                        weight=ft.FontWeight.W_600,
                                        color=t["text_secondary"],
                                    ),
                                    ft.Row(
                                        [
                                            ft.Text("N°", size=12, color=t["text_secondary"]),
                                            numero_text,
                                            ft.Text("·", size=12, color=t["border"]),
                                            fecha_text,
                                        ],
            spacing=0,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                spacing=4,
                            ),
                        ]
                    ),
                    padding=ft.padding.only(bottom=12),
                ),

                ft.Divider(height=1, color=t["border_light"]),

                # Datos del cliente
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "Cliente:",
                                        size=12,
                                        color=t["text_secondary"],
                                        width=72,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    ft.Container(content=ac_cliente.control, expand=True),
                                    ft.Container(
                                        ft.Text("Tel:", size=12, color=t["text_secondary"], weight=ft.FontWeight.W_500),
                                        width=32,
                                        alignment=ft.alignment.center_right,
                                    ),
                                    tf_tel,
                                ]
                            ),
                            ft.Row(
                                [
                                    ft.Text(
                                        "Provincia:",
                                        size=12,
                                        color=t["text_secondary"],
                                        width=72,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    tf_provincia,
                                    ft.Container(
                                        ft.Text("Transp:", size=12, color=t["text_secondary"], weight=ft.FontWeight.W_500),
                                        width=56,
                                        alignment=ft.alignment.center_right,
                                    ),
                                    tf_transporte,
                                ]
                            ),
                        ],
                        spacing=8,
                    ),
                    bgcolor=t["bg_card"],
                    border=ft.border.all(0.5, t["border_light"]),
                    border_radius=8,
                    padding=ft.padding.all(12),
                ),

                # Tabla de ítems
                ft.Container(
                    content=ft.Column(
                        [
                            items_header,
                            ft.Container(content=items_col, expand=True),
                            ft.Container(
                                content=ft.TextButton(
                                    "+ Agregar ítem",
                                    style=ft.ButtonStyle(color=t["accent"]),
                                    on_click=lambda e: (ctrl.add_item(), ctrl.mark_dirty()),
                                ),
                                alignment=ft.alignment.center_left,
                                padding=ft.padding.only(top=4, left=4),
                            ),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    expand=True,
                    bgcolor=t["bg_card"],
                    border_radius=8,
                    border=ft.border.all(0.5, t["border"]),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),

                # Navegación entre facturas
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Anterior factura",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: ctrl.load_relative_factura(1),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=7),
                                color=t["text_secondary"],
                                side=ft.BorderSide(1, t["border"]),
                            ),
                        ),
                        ft.OutlinedButton(
                            "Siguiente factura",
                            icon=ft.Icons.ARROW_FORWARD,
                            on_click=lambda e: ctrl.load_relative_factura(-1),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=7),
                                color=t["text_secondary"],
                                side=ft.BorderSide(1, t["border"]),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=12,
            expand=True,
        ),
        expand=True,
        padding=ft.padding.symmetric(vertical=22, horizontal=24),
        bgcolor=t["bg_page"],
    )

    # ── Panel derecho (historial + pendientes) ─────────────────────────────
    pendientes_expanded = {"value": False}
    pendientes_container = ft.Container(visible=False, padding=ft.padding.only(top=4))

    def _toggle_pendientes(e):
        pendientes_expanded["value"] = not pendientes_expanded["value"]
        if pendientes_expanded["value"]:
            _render_pendientes()
        pendientes_container.visible = pendientes_expanded["value"]
        if pendientes_container.page:
            pendientes_container.update()

    def _render_pendientes():
        curvas = get_curvas_pendientes()
        items = []
        if not curvas:
            items.append(
                ft.Container(
                    ft.Text("Sin pendientes", size=11, color=t["text_hint"]),
                    padding=ft.padding.symmetric(4, 0),
                )
            )
        else:
            for cv in curvas:
                detalle = cv.get("detalle_curva", "")
                numero = cv.get("factura_numero", "")
                cliente = cv.get("cliente_nombre", "")
                items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(detalle, size=11, weight=ft.FontWeight.W_500,
                                        color=t["text_primary"]),
                                ft.Text(f"{numero} - {cliente}", size=10,
                                        color=t["text_secondary"]),
                            ], spacing=1, expand=True),
                            ft.TextButton("Resolver", style=ft.ButtonStyle(
                                color=t["accent"], padding=ft.padding.symmetric(2, 6)),
                                on_click=lambda e, c=cv: _abrir_resolver(c)),
                        ], spacing=4),
                        padding=ft.padding.symmetric(4, 0),
                        border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
                    )
                )
        container = ft.Column(items, spacing=2, scroll=ft.ScrollMode.AUTO, height=200)
        pendientes_container.content = container

    def _abrir_resolver(curva: dict):
        es_surtida = curva.get("es_surtida", 0)
        variante_ids = [int(x) for x in curva["variante_ids"].split(",") if x.strip()]
        all_vars = get_variantes_con_producto()
        vars_map = {v["variante_id"]: v for v in all_vars}

        distribucion: list[dict] = []
        fields: list[ft.Control] = []

        if es_surtida:
            # Group by color
            from collections import defaultdict
            by_color: dict[str, list] = defaultdict(list)
            for vid in variante_ids:
                v = vars_map.get(vid)
                if v:
                    by_color[v.get("color") or "Sin color"].append(v)

            for cname, cvars in by_color.items():
                fields.append(ft.Text(f"● {cname}", size=12, weight=ft.FontWeight.W_600,
                                      color=t["text_primary"]))
                for v in cvars:
                    tf = ft.TextField(
                        value="0", hint_text=v.get("talla") or "-",
                        width=70, height=34, text_size=12,
                        keyboard_type=ft.KeyboardType.NUMBER,
                        border_radius=6,
                        border_color=t["border"], focused_border_color=t["accent"],
                        color=t["text_primary"], bgcolor=t["bg_input"],
                    )
                    distribucion.append({"variante_id": v["variante_id"], "tf": tf})
                    fields.append(
                        ft.Row([
                            ft.Text(v.get("talla") or "-", size=12, width=40, color=t["text_secondary"]),
                            tf,
                        ], spacing=6)
                    )
        else:
            for vid in variante_ids:
                v = vars_map.get(vid)
                tf = ft.TextField(
                    value="0", hint_text=v.get("talla") or "-",
                    width=70, height=34, text_size=12,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    border_radius=6,
                    border_color=t["border"], focused_border_color=t["accent"],
                    color=t["text_primary"], bgcolor=t["bg_input"],
                )
                distribucion.append({"variante_id": vid, "tf": tf})
                fields.append(
                    ft.Row([
                        ft.Text(f"{v.get('color', '')} {v.get('talla', '')}".strip(),
                                size=12, width=100, color=t["text_secondary"]),
                        tf,
                    ], spacing=6)
                )

        def _do_resolver(ev):
            dist = [{"variante_id": d["variante_id"], "cantidad": float(d["tf"].value or "0")}
                    for d in distribucion]
            if sum(d["cantidad"] for d in dist) <= 0:
                return
            resolver_curva(curva["id"], dist)
            page.close(dlg)
            _render_pendientes()
            if pendientes_container.page:
                pendientes_container.update()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text(f"Resolver: {curva.get('detalle_curva', '')}",
                          size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Factura {curva.get('factura_numero', '')}",
                            size=12, color=t["text_secondary"]),
                    ft.Divider(height=6, color=t["border_light"]),
                    *fields,
                ], spacing=4, scroll=ft.ScrollMode.AUTO),
                width=360,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                ft.ElevatedButton("Aplicar", bgcolor=t["accent"], color=t["accent_text"],
                                  on_click=_do_resolver),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    pendientes_btn = ft.TextButton(
        "📦 Pendientes",
        style=ft.ButtonStyle(color=t["accent"]),
        on_click=_toggle_pendientes,
    )

    right_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Historial",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=t["text_secondary"],
                            expand=True,
                        ),
                        ft.IconButton(
                            ft.Icons.REFRESH,
                            icon_size=16,
                            icon_color=t["text_secondary"],
                            tooltip="Actualizar",
                            on_click=lambda e: ctrl.refresh_history(),
                            style=ft.ButtonStyle(padding=ft.padding.all(4)),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(
                    content=tf_history_search,
                    margin=ft.margin.only(bottom=6),
                ),
                ft.Divider(height=0.5, thickness=0.5, color=t["border_light"]),
                ft.Container(
                    content=history_col,
                    expand=True,
                    padding=0,
                    margin=0,
                ),
                ft.Divider(height=0.5, thickness=0.5, color=t["border_light"]),
                pendientes_btn,
                pendientes_container,
            ],
            spacing=8,
            expand=True,
        ),
        width=310,
        bgcolor=t["bg_card"],
        border=ft.border.only(
            left=ft.border.BorderSide(0.5, t["border_light"])
        ),
        padding=ft.padding.only(top=18, left=14, right=14, bottom=14),
    )

    # ── Inicialización ─────────────────────────────────────────────────────────
    ctrl.nueva()

    # ── Widget raíz ────────────────────────────────────────────────────────────
    view = ft.Container(
        content=ft.Row([left_panel, center, right_panel], spacing=0, expand=True),
        expand=True,
        bgcolor=t["bg_page"],
    )

    # API pública del widget
    view.refresh_data = ctrl.refresh_history
    view.dispose = lambda: setattr(page, "on_keyboard_event", _previous_keyboard_handler)

    return view
