import logging
log = logging.getLogger("mvp10")

import flet as ft

from db.database import (
    get_clientes,
    save_cliente,
    update_cliente,
    delete_cliente,
    get_resumen_cuentas,
    get_movimientos_cliente,
    registrar_movimiento,
)


def _fmt_saldo(val: float) -> str:
    try:
        v = float(val)
        signo = "-" if v < 0 else ""
        return f"{signo}${abs(int(v)):,}".replace(",", ".")
    except Exception:
        return "$0"


from views.flow_guide import HelpButton

def ClientesView(page: ft.Page, t: dict, on_switch_tab=None):
    search_filter: dict[str, str] = {"value": ""}
    selected_id: dict[str, int | None] = {"value": None}

    def _show_message(text: str, color=t["accent"]):
        page.open(ft.SnackBar(ft.Text(text, color=ft.colors.WHITE), bgcolor=color, duration=3200))

    def _tf(hint, width=None):
        return ft.TextField(
            hint_text=hint,
            border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            width=width,
            border_color=t["border"],
            focused_border_color=t["accent"],
            bgcolor=t["bg_input"],
            color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
        )

    # ── Panel derecho ─────────────────────────────────────────────────────────
    right_panel = ft.Container(expand=True)

    def _render_empty_panel():
        right_panel.content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.PEOPLE_OUTLINE, size=48, color=t["text_hint"]),
                    ft.Text("Seleccioná un cliente", size=15, color=t["text_hint"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
        if right_panel.page:
            right_panel.update()

    def _render_panel(cliente: dict):
        selected_id["value"] = cliente["id"]
        movimientos = get_movimientos_cliente(cliente["id"])
        saldo = sum(m.get("debe", 0) - m.get("haber", 0) for m in movimientos)
        saldo_color = ft.colors.RED_700 if saldo > 0 else (
            ft.colors.GREEN_700 if saldo < 0 else t["text_secondary"]
        )

        # ── Campos edición ──
        tf_nombre    = _tf("Nombre")
        tf_domicilio = _tf("Domicilio")
        tf_telefono  = _tf("Teléfono")
        
        tf_nombre.value    = cliente.get("nombre", "")
        tf_domicilio.value = cliente.get("domicilio", "")
        tf_telefono.value  = cliente.get("telefono", "")

        editando = {"value": False}
        form_col = ft.Column(
            [
                ft.Text("Nombre *", size=12, color=t["text_secondary"]), tf_nombre,
                ft.Text("Teléfono", size=12, color=t["text_secondary"]), tf_telefono,
                ft.Text("Domicilio", size=12, color=t["text_secondary"]), tf_domicilio,
            ],
            spacing=6, tight=True, visible=False,
        )

        btn_editar_label = ft.Text("Editar datos", size=13)
        btn_editar = ft.TextButton(
            content=ft.Row([ft.Icon(ft.icons.EDIT_OUTLINED, size=15), btn_editar_label], spacing=4),
        )

        def _toggle_edit(ev):
            editando["value"] = not editando["value"]
            form_col.visible = editando["value"]
            btn_editar_label.value = "Cancelar" if editando["value"] else "Editar datos"
            if form_col.page: form_col.update()
            if btn_editar_label.page: btn_editar_label.update()

        btn_editar.on_click = _toggle_edit

        def _guardar_edicion(ev):
            nombre = (tf_nombre.value or "").strip()
            if not nombre:
                _show_message("El nombre es obligatorio.", t["accent"])
                return
            update_cliente(cliente["id"], {
                "nombre": nombre,
                "domicilio": (tf_domicilio.value or "").strip(),
                "telefono": (tf_telefono.value or "").strip(),
            })
            _show_message(f"Cliente '{nombre}' actualizado.", ft.colors.GREEN_700)
            _refresh_all(keep_selected=cliente["id"])

        # ── Registrar pago ──
        tf_pago_monto = ft.TextField(
            hint_text="Monto", border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            keyboard_type=ft.KeyboardType.NUMBER, width=140,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
        )
        tf_pago_desc = ft.TextField(
            hint_text="Descripción (opcional)", border_radius=7, height=38,
            text_size=13, content_padding=ft.padding.symmetric(8, 10), expand=True,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
        )

        def _guardar_pago(ev):
            raw = (tf_pago_monto.value or "").strip().replace(".", "").replace(",", ".")
            try:
                monto = float(raw)
            except ValueError:
                _show_message("Ingresá un monto válido.", ft.colors.ORANGE_700)
                return
            if monto <= 0:
                _show_message("El monto debe ser mayor a cero.", ft.colors.ORANGE_700)
                return
            registrar_movimiento(
                cliente_id=cliente["id"],
                tipo="Pago",
                monto=monto,
                referencia="",
                descripcion=(tf_pago_desc.value or "").strip() or "Pago manual",
                es_pago=True,
            )
            _show_message(f"Pago registrado.", ft.colors.GREEN_700)
            _refresh_all(keep_selected=cliente["id"])

        # ── Historial ──
        def _build_mov_row(m: dict, zebra: bool):
            es_debe = m.get("debe", 0) > 0
            return ft.Container(
                content=ft.Row([
                    ft.Text(m.get("fecha", ""), size=11, color=t["text_secondary"], width=120),
                    ft.Text(m.get("tipo", ""), size=11, color=t["text_secondary"], width=80),
                    ft.Text(m.get("descripcion", ""), size=12, color=t["text_primary"], expand=True),
                    ft.Text(
                        f"+${int(m.get('debe', 0)):,}".replace(",", ".") if es_debe
                        else f"-${int(m.get('haber', 0)):,}".replace(",", "."),
                        size=12, weight=ft.FontWeight.W_600,
                        color=ft.colors.RED_700 if es_debe else ft.colors.GREEN_700,
                        width=90, text_align=ft.TextAlign.RIGHT,
                    ),
                ], spacing=8),
                padding=ft.padding.symmetric(8, 12),
                bgcolor=t["bg_card"] if zebra else t["bg_row_odd"],
                border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
            )

        movs_controls = (
            [_build_mov_row(m, i % 2 == 0) for i, m in enumerate(movimientos)]
            if movimientos else [
                ft.Container(
                    ft.Text("Sin movimientos registrados.", size=13, color=t["text_hint"]),
                    padding=ft.padding.all(16),
                )
            ]
        )

        def _confirm_delete(ev):
            nombre = cliente.get("nombre", "")
            def _do_delete(ev2, d):
                delete_cliente(cliente["id"])
                _show_message(f"'{nombre}' eliminado.", ft.colors.RED_700)
                page.close(d)
                selected_id["value"] = None
                _refresh_all()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar cliente"),
                content=ft.Text(f"¿Seguro que querés eliminar a '{nombre}'?"),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                    ft.ElevatedButton("Eliminar", bgcolor=ft.colors.RED_700, color=t["accent_text"],
                                      on_click=lambda ev: _do_delete(ev, dlg)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)

        right_panel.content = ft.Container(
            content=ft.Column(
                [
                    # ── Cabecera ──
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(cliente.get("nombre", ""), size=18, weight=ft.FontWeight.W_700,
                                            color=t["text_primary"]),
                                    ft.Text(cliente.get("telefono", "") or "Sin teléfono", size=12, color=t["text_secondary"]),
                                    ft.Text(cliente.get("domicilio", "") or "Sin domicilio", size=12, color=t["text_secondary"]),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.Column(
                                [
                                    ft.Text("Saldo", size=11, color=t["text_secondary"]),
                                    ft.Text(_fmt_saldo(saldo), size=26, weight=ft.FontWeight.W_800, color=saldo_color),
                                ],
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(height=1, color=t["border_light"]),

                    # ── Acciones ──
                    ft.Row([btn_editar,
                            ft.TextButton(
                                content=ft.Row([ft.Icon(ft.icons.DELETE_OUTLINE, size=15, color=ft.colors.RED_400),
                                                ft.Text("Eliminar", size=13, color=ft.colors.RED_400)], spacing=4),
                                on_click=_confirm_delete,
                            )], spacing=0),
                    form_col,

                    # ── Registrar pago ──
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Registrar pago", size=13, weight=ft.FontWeight.W_500,
                                        color=t["text_primary"]),
                                ft.Row([tf_pago_monto, tf_pago_desc,
                                        ft.ElevatedButton(
                                            "Registrar",
                                            bgcolor=ft.colors.GREEN_700,
                                            color=t["accent_text"],
                                            on_click=_guardar_pago,
                                            style=ft.ButtonStyle(padding=ft.padding.symmetric(8, 16)),
                                        )], spacing=8),
                            ],
                            spacing=8, tight=True,
                        ),
                        bgcolor=t["bg_card"],
                        border=ft.border.all(0.5, t["border_light"]),
                        border_radius=10,
                        padding=14,
                    ),

                    ft.ElevatedButton(
                        "Guardar cambios",
                        bgcolor=t["accent"], color=t["accent_text"],
                        on_click=_guardar_edicion,
                        visible=False,
                        style=ft.ButtonStyle(padding=ft.padding.symmetric(8, 16)),
                    ) if False else ft.Container(),

                    # ── Historial ──
                    ft.Text("Movimientos", size=13, weight=ft.FontWeight.W_500, color=t["text_primary"]),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Container(
                                    ft.Row([
                                        ft.Text("Fecha", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=120),
                                        ft.Text("Tipo", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=80),
                                        ft.Text("Descripción", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], expand=True),
                                        ft.Text("Monto", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=90, text_align=ft.TextAlign.RIGHT),
                                    ], spacing=8),
                                    padding=ft.padding.symmetric(8, 12),
                                    bgcolor=t["bg_header"],
                                ),
                                ft.Column(controls=movs_controls, spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
                            ],
                            spacing=0, expand=True,
                        ),
                        border=ft.border.all(0.5, t["border"]),
                        border_radius=8,
                        expand=True,
                    ),
                ],
                spacing=12, expand=True,
            ),
            padding=ft.padding.only(left=20, right=4, top=4, bottom=4),
            expand=True,
        )

        # Conectar botón guardar edición al form visible
        # Reemplazar el placeholder por botón real integrado al form_col
        save_btn = ft.ElevatedButton(
            "Guardar cambios",
            bgcolor=t["accent"], color=t["accent_text"],
            on_click=_guardar_edicion,
            style=ft.ButtonStyle(padding=ft.padding.symmetric(8, 16)),
        )
        form_col.controls.append(save_btn)

        if right_panel.page:
            right_panel.update()

    # ── Lista izquierda ───────────────────────────────────────────────────────
    list_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    tf_search = ft.TextField(
        hint_text="Buscar...",
        border_radius=7, height=34, text_size=12,
        content_padding=ft.padding.symmetric(6, 10),
        border_color=t["border"],
        focused_border_color=t["accent"],
        prefix_icon=ft.icons.SEARCH,
        bgcolor=t["bg_input"], color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )

    def _build_list_row(cliente: dict, saldo: float):
        is_selected = selected_id["value"] == cliente["id"]
        saldo_color = ft.colors.RED_700 if saldo > 0 else (
            ft.colors.GREEN_700 if saldo < 0 else t["text_hint"]
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(cliente["nombre"], size=13, weight=ft.FontWeight.W_600, expand=True,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, color=t["text_primary"]),
                            ft.Text(_fmt_saldo(saldo), size=12, weight=ft.FontWeight.W_600, color=saldo_color),
                        ],
                        spacing=4,
                    ),
                    ft.Text(cliente.get("telefono", "") or "—", size=11, color=t["text_secondary"]),
                ],
                spacing=2, tight=True,
            ),
            padding=ft.padding.symmetric(10, 14),
            bgcolor=t["bg_selected"] if is_selected else t["bg_card"],
            border=ft.border.only(
                left=ft.border.BorderSide(3, t["accent"]) if is_selected else ft.border.BorderSide(3, ft.colors.TRANSPARENT),
                bottom=ft.border.BorderSide(0.5, t["border_light"]),
            ),
            ink=True,
            on_click=lambda e, c=cliente: _select_cliente(c),
        )

    def _select_cliente(cliente: dict):
        selected_id["value"] = cliente["id"]
        _refresh_list()
        _render_panel(cliente)

    def _refresh_list():
        saldos_map = {r["id"]: r["saldo"] for r in get_resumen_cuentas()}
        clientes = get_clientes()
        query = search_filter["value"].lower()
        if query:
            clientes = [
                c for c in clientes
                if query in (c.get("nombre", "") + " " + c.get("telefono", "")).lower()
            ]

        # Deudores primero, luego alfabético
        clientes.sort(key=lambda c: (-(saldos_map.get(c["id"], 0) > 0), c["nombre"].lower()))

        list_col.controls.clear()
        if not clientes:
            list_col.controls.append(
                ft.Container(
                    ft.Text("Sin resultados.", size=12, color=t["text_hint"]),
                    padding=ft.padding.all(16),
                )
            )
        else:
            for c in clientes:
                list_col.controls.append(_build_list_row(c, saldos_map.get(c["id"], 0)))

        if list_col.page:
            list_col.update()

    def _refresh_all(keep_selected: int | None = None):
        _refresh_list()
        if keep_selected is not None:
            # Recargar panel del cliente que estaba seleccionado
            from db.database import get_clientes
            todos = get_clientes()
            match = next((c for c in todos if c["id"] == keep_selected), None)
            if match:
                _render_panel(match)
        elif selected_id["value"] is None:
            _render_empty_panel()

    def _on_search(e):
        search_filter["value"] = (e.control.value or "").strip()
        _refresh_list()

    tf_search.on_change = _on_search

    def _open_nuevo_cliente(e=None):
        tf_n = _tf("Nombre del cliente")
        tf_d = _tf("Domicilio")
        tf_t = _tf("Teléfono / WhatsApp")

        def _guardar(ev, dlg):
            nombre = (tf_n.value or "").strip()
            if not nombre:
                _show_message("El nombre es obligatorio.", t["accent"])
                return
            new_id = save_cliente({
                "nombre": nombre,
                "domicilio": (tf_d.value or "").strip(),
                "telefono": (tf_t.value or "").strip(),
            })
            _show_message(f"Cliente '{nombre}' creado.", ft.colors.GREEN_700)
            page.close(dlg)
            _refresh_all(keep_selected=new_id)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo cliente", size=16, weight=ft.FontWeight.W_500, color=t["text_primary"]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Nombre *", size=12, color=t["text_secondary"]), tf_n,
                    ft.Text("Teléfono", size=12, color=t["text_secondary"]), tf_t,
                    ft.Text("Domicilio", size=12, color=t["text_secondary"]), tf_d,
                ], spacing=8, tight=True),
                width=420,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                ft.ElevatedButton("Guardar", bgcolor=t["accent"], color=t["accent_text"],
                                  on_click=lambda ev: _guardar(ev, dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── Inicializar ───────────────────────────────────────────────────────────
    _refresh_list()

    # Abrir automáticamente el primero de la lista
    saldos_map = {r["id"]: r["saldo"] for r in get_resumen_cuentas()}
    todos = get_clientes()
    todos.sort(key=lambda c: (-(saldos_map.get(c["id"], 0) > 0), c["nombre"].lower()))
    if todos:
        selected_id["value"] = todos[0]["id"]
        _render_panel(todos[0])
    else:
        _render_empty_panel()

    # ── Layout principal ──────────────────────────────────────────────────────
    help_btn = HelpButton([
        {"text": "Creá un cliente nuevo con el botón superior"},
        {"text": "Andá a Facturación para facturarle", "action": ("Ir a Facturación", 1)},
        {"text": "Registrale un pago desde el panel derecho"},
    ], page, on_switch_tab)

    view = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Clientes", size=22, weight=ft.FontWeight.W_500, color=t["text_primary"], expand=True),
                        help_btn,
                        ft.ElevatedButton(
                            "Nuevo cliente", icon=ft.icons.PERSON_ADD_OUTLINED,
                            on_click=_open_nuevo_cliente,
                            style=ft.ButtonStyle(
                                bgcolor=t["accent"], color=t["accent_text"],
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(10, 18),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                # Cuerpo dividido
                ft.Container(
                    content=ft.Row(
                        [
                            # Panel izquierdo
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Container(content=tf_search, padding=ft.padding.all(8)),
                                        ft.Divider(height=1, color=t["border_light"]),
                                        list_col,
                                    ],
                                    spacing=0, expand=True,
                                ),
                                width=260,
                                border=ft.border.only(right=ft.border.BorderSide(0.5, t["border"])),
                                bgcolor=t["bg_card"],
                            ),
                            # Panel derecho
                            right_panel,
                        ],
                        spacing=0, expand=True,
                    ),
                    expand=True,
                    border=ft.border.all(0.5, t["border"]),
                    border_radius=12,
                    bgcolor=t["bg_card"],
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
            ],
            spacing=12, expand=True,
        ),
        padding=28, expand=True,
        bgcolor=t["bg_page"],
    )

    view.refresh_data = lambda: _refresh_all(keep_selected=selected_id["value"])
    return view