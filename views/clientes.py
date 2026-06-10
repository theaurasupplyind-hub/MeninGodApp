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
    get_facturas_pendientes_cliente,
    registrar_cobro_factura,
    update_movimiento_cc,
    delete_movimiento_cc,
    anular_cobro,
    get_facturas,
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
    MOV_MAX = 100
    _show_all_movs: dict[str, bool] = {"value": False}
    search_filter: dict[str, str] = {"value": ""}
    selected_id: dict[str, int | None] = {"value": None}
    _auto_edit: dict[str, bool] = {"value": False}
    _form_open: dict[str, bool] = {"value": False}

    def _show_message(text: str, color=t["accent"]):
        page.open(ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color, duration=3200))

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

    def _do_confirm_delete(cliente: dict):
        nombre = cliente.get("nombre", "")
        razones = []

        facturas = get_facturas(200)
        facturas_cliente = [f for f in facturas if (f.get("cliente_nombre") or "") == nombre]
        if facturas_cliente:
            razones.append(f"Tiene {len(facturas_cliente)} factura(s) asociada(s).")

        saldo = cliente.get("saldo", 0) or 0
        if saldo and float(saldo) != 0:
            razones.append(f"Saldo pendiente: {_fmt_saldo(saldo)}.")

        if razones:
            razones.append("")
            razones.append("Desvinculá las facturas y saldá la cuenta antes de eliminar.")
            dlg = ft.AlertDialog(
                modal=True,
                bgcolor=t["bg_card"],
                title=ft.Text("No se puede eliminar", color=ft.Colors.ERROR, size=16, weight=ft.FontWeight.W_600),
                content=ft.Column([
                    ft.Text(f"No se puede eliminar a '{nombre}'.", size=14),
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

        def _do_delete(ev2, d):
            try:
                delete_cliente(cliente["id"])
                _show_message(f"'{nombre}' eliminado.", ft.Colors.RED_700)
                page.close(d)
                selected_id["value"] = None
                _refresh_all()
            except Exception as ex:
                _show_message(f"Error al eliminar: {ex}", ft.Colors.ERROR)
                page.close(d)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text("Eliminar cliente"),
            content=ft.Text(f"¿Seguro que querés eliminar a '{nombre}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                ft.ElevatedButton("Eliminar", bgcolor=ft.Colors.RED_700, color=t["accent_text"],
                                  on_click=lambda ev: _do_delete(ev, dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── Panel derecho ─────────────────────────────────────────────────────────
    right_panel = ft.Container(expand=True)

    def _render_empty_panel():
        right_panel.content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=48, color=t["text_hint"]),
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
        all_movimientos = get_movimientos_cliente(cliente["id"], limit=100000)
        movimientos = all_movimientos
        saldo = sum(m.get("debe", 0) - m.get("haber", 0) for m in movimientos)
        saldo_color = ft.Colors.RED_700 if saldo > 0 else (
            ft.Colors.GREEN_700 if saldo < 0 else t["text_secondary"]
        )

        # ── Campos edición ──
        tf_nombre    = _tf("Nombre")
        tf_domicilio = _tf("Domicilio")
        tf_telefono  = _tf("Teléfono")
        
        tf_nombre.value    = cliente.get("nombre", "")
        tf_domicilio.value = cliente.get("domicilio", "")
        tf_telefono.value  = cliente.get("telefono", "")

        editando = {"value": _auto_edit["value"]}
        _auto_edit["value"] = False
        _form_open["value"] = editando["value"]
        form_col = ft.Column(
            [
                ft.Text("Nombre *", size=12, color=t["text_secondary"]), tf_nombre,
                ft.Text("Teléfono", size=12, color=t["text_secondary"]), tf_telefono,
                ft.Text("Domicilio", size=12, color=t["text_secondary"]), tf_domicilio,
            ],
            spacing=6, tight=True, visible=editando["value"],
        )

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
            _show_message(f"Cliente '{nombre}' actualizado.", ft.Colors.GREEN_700)
            _refresh_all(keep_selected=cliente["id"])

        # ── Registrar pago (linkeado a factura) ──
        pendientes = get_facturas_pendientes_cliente(cliente.get("nombre", ""))
        dd_factura = ft.Dropdown(
            options=[
                ft.dropdown.Option(
                    key=str(f["id"]),
                    text=f"{f['numero']} — ${int(f['deuda']):,}".replace(",", "."),
                )
                for f in pendientes
            ],
            hint_text="Seleccionar factura",
            border_radius=7, text_size=13,
            content_padding=ft.padding.symmetric(4, 10),
            width=280,
        )
        tf_pago_monto = ft.TextField(
            hint_text="Monto", border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            keyboard_type=ft.KeyboardType.NUMBER, width=140,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
        )
        dd_medio = ft.Dropdown(
            options=[
                ft.dropdown.Option("Efectivo"),
                ft.dropdown.Option("Transferencia"),
            ],
            value="Efectivo",
            border_radius=7, text_size=13,
            content_padding=ft.padding.symmetric(4, 10),
            width=160,
        )
        tf_pago_nota = ft.TextField(
            hint_text="Nota opcional", border_radius=7, height=38,
            text_size=13, content_padding=ft.padding.symmetric(8, 10), expand=True,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
        )

        def _on_factura_selected(e):
            factura_id = int(e.control.value) if e.control.value else None
            if factura_id is None:
                tf_pago_monto.value = ""
                tf_pago_monto.update()
                return
            factura = next((f for f in pendientes if f["id"] == factura_id), None)
            if factura:
                tf_pago_monto.value = str(int(factura["deuda"]))
                tf_pago_monto.update()

        dd_factura.on_change = _on_factura_selected

        # Precargar monto si solo hay una factura pendiente
        if len(pendientes) == 1:
            dd_factura.value = str(pendientes[0]["id"])
            tf_pago_monto.value = str(int(pendientes[0]["deuda"]))

        def _guardar_pago(ev):
            if not dd_factura.value:
                _show_message("Seleccioná una factura.", ft.Colors.ORANGE_700)
                return
            raw = (tf_pago_monto.value or "").strip().replace(".", "").replace(",", ".")
            try:
                monto = float(raw)
            except ValueError:
                _show_message("Ingresá un monto válido.", ft.Colors.ORANGE_700)
                return
            if monto <= 0:
                _show_message("El monto debe ser mayor a cero.", ft.Colors.ORANGE_700)
                return
            factura_id = int(dd_factura.value)
            factura = next((f for f in pendientes if f["id"] == factura_id), None)
            if not factura:
                _show_message("Factura no encontrada.", ft.Colors.RED_700)
                return
            resultado = registrar_cobro_factura(
                factura_id=factura_id,
                numero_factura=factura["numero"],
                cliente_id=cliente["id"],
                cliente_nombre=cliente.get("nombre", ""),
                monto=monto,
                medio_pago=dd_medio.value,
                nota=tf_pago_nota.value or "",
            )
            sb_text = f"Pago registrado."
            if resultado["saldo_restante"] > 0:
                sb_text += f" Saldo restante: ${int(resultado['saldo_restante']):,}".replace(",", ".")
            _show_message(sb_text, ft.Colors.GREEN_700)
            _refresh_all(keep_selected=cliente["id"])

        # ── Historial ──
        def _build_mov_row(m: dict, zebra: bool):
            es_debe = m.get("debe", 0) > 0
            es_pago = m.get("tipo") == "Pago"

            actions = []
            if es_pago:
                def _open_edit_mov(ev, mov=m):
                    _editar_movimiento_cc(mov)
                actions.append(
                    ft.IconButton(
                        icon=ft.Icons.EDIT_OUTLINED,
                        icon_size=14,
                        icon_color=t["text_secondary"],
                        on_click=_open_edit_mov,
                        tooltip="Editar pago",
                        style=ft.ButtonStyle(padding=ft.padding.all(2)),
                    )
                )

            return ft.Container(
                content=ft.Row([
                    ft.Text(m.get("fecha", ""), size=11, color=t["text_secondary"], width=120),
                    ft.Text(m.get("tipo", ""), size=11, color=t["text_secondary"], width=80),
                    ft.Text(m.get("descripcion", ""), size=12, color=t["text_primary"], expand=True),
                    ft.Text(
                        f"+${int(m.get('debe', 0)):,}".replace(",", ".") if es_debe
                        else f"-${int(m.get('haber', 0)):,}".replace(",", "."),
                        size=12, weight=ft.FontWeight.W_600,
                        color=ft.Colors.RED_700 if es_debe else ft.Colors.GREEN_700,
                        width=90, text_align=ft.TextAlign.RIGHT,
                    ),
                    *actions,
                ], spacing=8),
                padding=ft.padding.symmetric(8, 12),
                bgcolor=t["bg_card"] if zebra else t["bg_row_odd"],
                border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
            )

        def _editar_movimiento_cc(mov: dict):
            monto_actual = float(mov.get("haber", 0) or 0)
            desc_actual = mov.get("descripcion", "")

            tf_monto = ft.TextField(
                value=str(int(monto_actual)),
                label="Monto",
                keyboard_type=ft.KeyboardType.NUMBER,
                height=40, text_size=13,
                border_color=t["border"], focused_border_color=t["accent"],
                bgcolor=t["bg_input"], color=t["text_primary"],
            )
            tf_desc = ft.TextField(
                value=desc_actual,
                label="Descripción",
                height=40, text_size=13,
                border_color=t["border"], focused_border_color=t["accent"],
                bgcolor=t["bg_input"], color=t["text_primary"],
            )

            def _guardar_cambio(ev, d):
                try:
                    nuevo_monto = float((tf_monto.value or "0").replace(".", "").replace(",", "."))
                except ValueError:
                    _show_message("Monto inválido.", t["accent"])
                    return
                if nuevo_monto <= 0:
                    _show_message("El monto debe ser mayor a cero.", t["accent"])
                    return
                update_movimiento_cc(mov["id"], nuevo_monto, tf_desc.value or "")
                _show_message("Movimiento actualizado.", ft.Colors.GREEN_700)
                page.close(d)
                _refresh_all(keep_selected=cliente["id"])

            def _confirmar_anulacion(ev, d):
                page.close(d)

                def _anular(ev2):
                    anular_cobro(mov["id"])
                    _show_message("Pago anulado.", ft.Colors.RED_700)
                    _refresh_all(keep_selected=cliente["id"])

                confirm = ft.AlertDialog(
                    modal=True,
                    bgcolor=t["bg_card"],
                    title=ft.Text("Anular pago", size=16, weight=ft.FontWeight.W_500),
                    content=ft.Text("¿Estás seguro de anular este pago?", size=13, color=t["text_primary"]),
                    actions=[
                        ft.TextButton("No, cancelar", on_click=lambda ev: page.close(confirm)),
                        ft.ElevatedButton("Sí, anular", bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE,
                                          on_click=lambda ev: _anular(ev)),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.open(confirm)

            dlg = ft.AlertDialog(
                modal=True,
                bgcolor=t["bg_card"],
                title=ft.Text("Editar pago", size=16, weight=ft.FontWeight.W_500),
                content=ft.Container(
                    content=ft.Column([tf_monto, tf_desc], spacing=10, tight=True),
                    width=350,
                ),
                actions=[
                    ft.OutlinedButton(
                        "Anular pago",
                        icon=ft.Icons.DELETE_OUTLINE,
                        style=ft.ButtonStyle(color=ft.Colors.RED_700),
                        on_click=lambda ev: _confirmar_anulacion(ev, dlg),
                    ),
                    ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                    ft.ElevatedButton("Guardar", bgcolor=t["accent"], color=t["accent_text"],
                                      on_click=lambda ev: _guardar_cambio(ev, dlg)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)

        visible_movs = all_movimientos if _show_all_movs["value"] else all_movimientos[:MOV_MAX]
        movs_controls = (
            [_build_mov_row(m, i % 2 == 0) for i, m in enumerate(visible_movs)]
            if all_movimientos else [
                ft.Container(
                    ft.Text("Sin movimientos registrados.", size=13, color=t["text_hint"]),
                    padding=ft.padding.all(16),
                )
            ]
        )
        movs_remaining = len(all_movimientos) - MOV_MAX
        if movs_remaining > 0 and not _show_all_movs["value"]:
            def _load_more_movs(e):
                _show_all_movs["value"] = True
                _render_panel(cliente)
            movs_controls.append(
                ft.Container(
                    content=ft.ElevatedButton(
                        f"Cargar más ({movs_remaining} restantes)",
                        on_click=_load_more_movs,
                        style=ft.ButtonStyle(
                            bgcolor=t.get("bg_header", t["bg_card"]),
                            color=t["accent"],
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10),
                )
            )

        # ── Construir container de pago (linkeado a factura) ──
        _pago_inner = [
            ft.Text("Registrar pago", size=13, weight=ft.FontWeight.W_500,
                    color=t["text_primary"]),
        ]
        if pendientes:
            _pago_inner += [
                ft.Row([dd_factura, dd_medio], spacing=8),
                ft.Row([
                    tf_pago_monto,
                    tf_pago_nota,
                    ft.ElevatedButton(
                        "Registrar pago",
                        bgcolor=ft.Colors.GREEN_700,
                        color=t["accent_text"],
                        on_click=_guardar_pago,
                        style=ft.ButtonStyle(padding=ft.padding.symmetric(8, 16)),
                    ),
                ], spacing=8, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ]
        else:
            _pago_inner.append(
                ft.Text("No hay facturas pendientes.", size=12, color=t["text_hint"])
            )
        _pago_container = ft.Container(
            content=ft.Column(_pago_inner, spacing=8, tight=True),
            bgcolor=t["bg_card"],
            border=ft.border.all(0.5, t["border_light"]),
            border_radius=10,
            padding=14,
        )

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

                    form_col,

                    _pago_container,

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
        def _cancelar_edicion(ev):
            _auto_edit["value"] = False
            _render_panel(cliente)

        btn_row = ft.Row([
            ft.ElevatedButton(
                "Guardar cambios",
                bgcolor=t["accent"], color=t["accent_text"],
                on_click=_guardar_edicion,
                style=ft.ButtonStyle(padding=ft.padding.symmetric(8, 16)),
            ),
            ft.TextButton(
                "Cancelar",
                on_click=_cancelar_edicion,
                style=ft.ButtonStyle(color=t["text_secondary"]),
            ),
        ], spacing=8)
        form_col.controls.append(btn_row)

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
        prefix_icon=ft.Icons.SEARCH,
        bgcolor=t["bg_input"], color=t["text_primary"],
        hint_style=ft.TextStyle(color=t["text_hint"]),
    )

    def _build_list_row(cliente: dict, saldo: float):
        is_selected = selected_id["value"] == cliente["id"]
        saldo_color = ft.Colors.RED_700 if saldo > 0 else (
            ft.Colors.GREEN_700 if saldo < 0 else t["text_hint"]
        )

        def _on_edit(ev, c=cliente):
            if selected_id["value"] == c["id"] and _form_open["value"]:
                _auto_edit["value"] = False
                _render_panel(c)
            else:
                _auto_edit["value"] = True
                _select_cliente(c)

        def _on_delete(ev, c=cliente):
            _do_confirm_delete(c)

        menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_size=16,
            icon_color=t["text_secondary"],
            items=[
                ft.PopupMenuItem(
                    content=ft.Row([
                        ft.Icon(ft.Icons.EDIT_OUTLINED, size=15, color=t["text_primary"]),
                        ft.Text("Editar", size=12, color=t["text_primary"]),
                    ], spacing=6, tight=True),
                    on_click=_on_edit,
                ),
                ft.PopupMenuItem(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DELETE_OUTLINE, size=15, color=ft.Colors.RED_400),
                        ft.Text("Eliminar", size=12, color=ft.Colors.RED_400),
                    ], spacing=6, tight=True),
                    on_click=_on_delete,
                ),
            ],
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(cliente["nombre"], size=13, weight=ft.FontWeight.W_600, expand=True,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, color=t["text_primary"]),
                            menu,
                            ft.Text(_fmt_saldo(saldo), size=12, weight=ft.FontWeight.W_600, color=saldo_color),
                        ],
                        spacing=2,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(cliente.get("telefono", "") or "—", size=11, color=t["text_secondary"]),
                ],
                spacing=2, tight=True,
            ),
            padding=ft.padding.symmetric(10, 14),
            bgcolor=t["bg_selected"] if is_selected else t["bg_card"],
            border=ft.border.only(
                left=ft.border.BorderSide(3, t["accent"]) if is_selected else ft.border.BorderSide(3, ft.Colors.TRANSPARENT),
                bottom=ft.border.BorderSide(0.5, t["border_light"]),
            ),
            ink=True,
            on_click=lambda e, c=cliente: _select_cliente(c),
        )

    def _select_cliente(cliente: dict):
        _show_all_movs["value"] = False
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
        _show_all_movs["value"] = False
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
            _show_message(f"Cliente '{nombre}' creado.", ft.Colors.GREEN_700)
            page.close(dlg)
            _refresh_all(keep_selected=new_id)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
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
                            "Nuevo cliente", icon=ft.Icons.PERSON_ADD_OUTLINED,
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