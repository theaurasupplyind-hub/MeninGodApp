"""
productos/proveedores.py
Gestión de proveedores con cuenta corriente.
"""
import logging
log = logging.getLogger("mvp10")

import flet as ft
from theme import get_theme

from db.database import (
    get_proveedores, save_proveedor, update_proveedor, delete_proveedor,
    get_resumen_proveedores, get_movimientos_proveedor, registrar_movimiento_proveedor,
    get_saldo_proveedor, get_compras_by_proveedor,
    update_movimiento_proveedor, delete_movimiento_proveedor,
)


def _fmt_saldo(val: float) -> str:
    try:
        v = float(val)
        signo = "-" if v < 0 else ""
        return f"{signo}${abs(int(v)):,}".replace(",", ".")
    except Exception:
        return "$0"


from views.flow_guide import HelpButton

def ProveedoresView(page: ft.Page, on_switch_tab=None):
    t = get_theme(page)
    MOV_MAX = 100
    _show_all_movs: dict[str, bool] = {"value": False}
    search_filter: dict[str, str] = {"value": ""}
    selected_id: dict[str, int | None] = {"value": None}

    def _show_message(text: str, color=t["accent"]):
        page.open(ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color, duration=3200))

    def _tf(hint, width=None):
        return ft.TextField(
            hint_text=hint,
            border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            width=width,
            border_color=t["border"],
            focused_border_color=t["accent"], bgcolor=t["bg_input"], color=t["text_primary"],
        )

    right_panel = ft.Container(expand=True)

    def _render_empty_panel():
        right_panel.content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=48, color=t["border"]),
                    ft.Text("Seleccioná un proveedor", size=15, color=t["text_hint"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
        if right_panel.page:
            right_panel.update()

    def _render_panel(proveedor: dict):
        selected_id["value"] = proveedor["id"]
        all_movimientos = get_movimientos_proveedor(proveedor["id"], limit=100000)
        movimientos = all_movimientos
        saldo = sum(m.get("debe", 0) - m.get("haber", 0) for m in movimientos)
        saldo_color = ft.Colors.ERROR if saldo > 0 else (
            ft.Colors.GREEN_700 if saldo < 0 else t["text_secondary"]
        )

        tf_nombre    = _tf("Nombre")
        tf_domicilio = _tf("Domicilio")
        tf_telefono  = _tf("Teléfono")
        
        tf_nombre.value    = proveedor.get("nombre", "")
        tf_domicilio.value = proveedor.get("domicilio", "")
        tf_telefono.value  = proveedor.get("telefono", "")

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
            content=ft.Row([ft.Icon(ft.Icons.EDIT_OUTLINED, size=15), btn_editar_label], spacing=4),
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
            update_proveedor(proveedor["id"], {
                "nombre": nombre,
                "domicilio": (tf_domicilio.value or "").strip(),
                "telefono": (tf_telefono.value or "").strip(),
            })
            _show_message(f"Proveedor '{nombre}' actualizado.", ft.Colors.GREEN_700)
            _refresh_all(keep_selected=proveedor["id"])

        # Registrar pago a proveedor
        tf_pago_monto = ft.TextField(
            hint_text="Monto", border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            keyboard_type=ft.KeyboardType.NUMBER, width=140,
        )
        tf_pago_desc = ft.TextField(
            hint_text="Descripción (opcional)", border_radius=7, height=38,
            text_size=13, content_padding=ft.padding.symmetric(8, 10), expand=True,
        )

        def _guardar_pago(ev):
            raw = (tf_pago_monto.value or "").strip().replace(".", "").replace(",", ".")
            try:
                monto = float(raw)
            except ValueError:
                _show_message("Ingresá un monto válido.", t["accent"])
                return
            if monto <= 0:
                _show_message("El monto debe ser mayor a cero.", t["accent"])
                return
            registrar_movimiento_proveedor(
                proveedor_id=proveedor["id"],
                tipo="Pago",
                monto=monto,
                referencia="",
                descripcion=(tf_pago_desc.value or "").strip() or "Pago manual",
                es_pago=True,
            )
            _show_message(f"Pago registrado.", ft.Colors.GREEN_700)
            _refresh_all(keep_selected=proveedor["id"])

        def _editar_movimiento_proveedor(mov: dict):
            monto_actual = float(mov.get("debe", 0) or 0)
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
                update_movimiento_proveedor(mov["id"], nuevo_monto, tf_desc.value or "")
                _show_message("Movimiento actualizado.", ft.Colors.GREEN_700)
                page.close(d)
                _refresh_all(keep_selected=proveedor["id"])

            def _confirmar_anulacion(ev, d):
                page.close(d)

                def _anular(ev2):
                    delete_movimiento_proveedor(mov["id"])
                    _show_message("Pago anulado.", ft.Colors.RED_700)
                    _refresh_all(keep_selected=proveedor["id"])

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

        def _build_mov_row(m: dict, zebra: bool):
            es_debe = m.get("debe", 0) > 0
            es_pago = m.get("tipo") == "Pago"

            actions = []
            if es_pago:
                def _open_edit_mov(ev, mov=m):
                    _editar_movimiento_proveedor(mov)
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
                    ft.Text(m.get("descripcion", ""), size=12, expand=True),
                    ft.Text(
                        f"+${int(m.get('debe', 0)):,}".replace(",", ".") if es_debe
                        else f"-${int(m.get('haber', 0)):,}".replace(",", "."),
                        size=12, weight=ft.FontWeight.W_600,
                        color=ft.Colors.ERROR if es_debe else ft.Colors.GREEN_700,
                        width=90, text_align=ft.TextAlign.RIGHT,
                    ),
                    *actions,
                ], spacing=8),
                padding=ft.padding.symmetric(8, 12),
                bgcolor=t["bg_row_even"] if zebra else t["bg_row_odd"],
                border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
            )

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
                _render_panel(proveedor)
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

        def _confirm_delete(ev):
            nombre = proveedor.get("nombre", "")
            compras = get_compras_by_proveedor(proveedor["id"])
            saldo = get_saldo_proveedor(proveedor["id"])
            razones = []
            if compras:
                razones.append(f"Tiene {len(compras)} compra(s) asociada(s).")
            if saldo != 0:
                razones.append(f"Saldo pendiente: {_fmt_saldo(saldo)}.")

            if razones:
                dlg = ft.AlertDialog(
                    modal=True,
                    bgcolor=t["bg_card"],
                    title=ft.Text("No se puede eliminar", color=ft.Colors.ERROR, weight=ft.FontWeight.W_600),
                    content=ft.Column([
                        ft.Text(f"No se puede eliminar a '{nombre}'."),
                        ft.Text(""),
                        ft.Text("\n".join(razones)),
                        ft.Text(""),
                        ft.Text("Eliminá todas las compras y saldá la cuenta antes de eliminar.", size=12, color=t["text_secondary"]),
                    ], spacing=2, tight=True),
                    actions=[
                        ft.TextButton("Cerrar", on_click=lambda ev: page.close(dlg)),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.open(dlg)
                return

            def _do_delete(ev2, d):
                try:
                    delete_proveedor(proveedor["id"])
                    _show_message(f"'{nombre}' eliminado.", ft.Colors.ERROR)
                    page.close(d)
                    selected_id["value"] = None
                    _refresh_all()
                except Exception as ex:
                    _show_message(f"Error al eliminar: {ex}", ft.Colors.ERROR)
                    page.close(d)

            dlg = ft.AlertDialog(
                modal=True,
                bgcolor=t["bg_card"],
                title=ft.Text("Eliminar proveedor"),
                content=ft.Text(f"¿Seguro que querés eliminar a '{nombre}'?"),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                    ft.ElevatedButton("Eliminar", bgcolor=ft.Colors.ERROR, color=t["accent_text"],
                                      on_click=lambda ev: _do_delete(ev, dlg)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)

        save_btn = ft.ElevatedButton(
            "Guardar cambios",
            bgcolor=t["accent"], color=t["accent_text"],
            on_click=_guardar_edicion,
            style=ft.ButtonStyle(padding=ft.padding.symmetric(8, 16)),
        )
        form_col.controls.append(save_btn)

        right_panel.content = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(proveedor.get("nombre", ""), size=18, weight=ft.FontWeight.W_700),
                                    ft.Text(proveedor.get("telefono", "") or "Sin teléfono", size=12, color=t["text_secondary"]),
                                    ft.Text(proveedor.get("domicilio", "") or "Sin domicilio", size=12, color=t["text_secondary"]),
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
                    ft.Row([btn_editar,
                            ft.TextButton(
                                content=ft.Row([ft.Icon(ft.Icons.DELETE_OUTLINE, size=15, color=ft.Colors.ERROR),
                                                ft.Text("Eliminar", size=13, color=ft.Colors.ERROR)], spacing=4),
                                on_click=_confirm_delete,
                            )], spacing=0),
                    form_col,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Registrar pago", size=13, weight=ft.FontWeight.W_500),
                                ft.Row([tf_pago_monto, tf_pago_desc,
                                        ft.ElevatedButton(
                                            "Registrar",
                                            bgcolor=ft.Colors.GREEN_700,
                                            color=ft.Colors.WHITE,
                                            on_click=_guardar_pago,
                                            style=ft.ButtonStyle(padding=ft.padding.symmetric(8, 16)),
                                        )], spacing=8),
                            ],
                            spacing=8, tight=True,
                        ),
                        bgcolor=t["bg_card"],
                        border=ft.border.all(0.5, t["border"]),
                        border_radius=10,
                        padding=14,
                    ),
                    ft.Text("Movimientos", size=13, weight=ft.FontWeight.W_500),
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
        if right_panel.page:
            right_panel.update()

    list_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    tf_search = ft.TextField(
        hint_text="Buscar...",
        border_radius=7, height=34, text_size=12,
        content_padding=ft.padding.symmetric(6, 10),
        border_color=t["border"],
        focused_border_color=t["accent"],
        prefix_icon=ft.Icons.SEARCH,
    )

    def _build_list_row(proveedor: dict, saldo: float):
        is_selected = selected_id["value"] == proveedor["id"]
        saldo_color = ft.Colors.ERROR if saldo > 0 else (
            ft.Colors.GREEN_700 if saldo < 0 else t["text_hint"]
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(proveedor["nombre"], size=13, weight=ft.FontWeight.W_600, expand=True,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(_fmt_saldo(saldo), size=12, weight=ft.FontWeight.W_600, color=saldo_color),
                        ],
                        spacing=4,
                    ),
                    ft.Text(proveedor.get("telefono", "") or "—", size=11, color=t["text_secondary"]),
                ],
                spacing=2, tight=True,
            ),
            padding=ft.padding.symmetric(10, 14),
            bgcolor=t["bg_selected"] if is_selected else t["bg_row_even"],
            border=ft.border.only(
                left=ft.border.BorderSide(3, t["accent"]) if is_selected else ft.border.BorderSide(3, ft.Colors.TRANSPARENT),
                bottom=ft.border.BorderSide(0.5, t["border_light"]),
            ),
            ink=True,
            on_click=lambda e, p=proveedor: _select_proveedor(p),
        )

    def _select_proveedor(proveedor: dict):
        _show_all_movs["value"] = False
        selected_id["value"] = proveedor["id"]
        _refresh_list()
        _render_panel(proveedor)

    def _refresh_list():
        saldos_map = {r["id"]: r["saldo"] for r in get_resumen_proveedores()}
        proveedores = get_proveedores()
        query = search_filter["value"].lower()
        if query:
            proveedores = [
                p for p in proveedores
                if query in (p.get("nombre", "") + " " + p.get("telefono", "")).lower()
            ]

        proveedores.sort(key=lambda c: (-(saldos_map.get(c["id"], 0) > 0), c["nombre"].lower()))

        list_col.controls.clear()
        if not proveedores:
            list_col.controls.append(
                ft.Container(
                    ft.Text("Sin resultados.", size=12, color=t["text_hint"]),
                    padding=ft.padding.all(16),
                )
            )
        else:
            for p in proveedores:
                list_col.controls.append(_build_list_row(p, saldos_map.get(p["id"], 0)))

        if list_col.page:
            list_col.update()

    def _refresh_all(keep_selected: int | None = None):
        _show_all_movs["value"] = False
        _refresh_list()
        if keep_selected is not None:
            todos = get_proveedores()
            match = next((p for p in todos if p["id"] == keep_selected), None)
            if match:
                _render_panel(match)
        elif selected_id["value"] is None:
            _render_empty_panel()

    def _on_search(e):
        search_filter["value"] = (e.control.value or "").strip()
        _refresh_list()

    tf_search.on_change = _on_search

    def _open_nuevo_proveedor(e=None):
        tf_n = _tf("Nombre del proveedor")
        tf_d = _tf("Domicilio")
        tf_t = _tf("Teléfono")

        def _guardar(ev, dlg):
            nombre = (tf_n.value or "").strip()
            if not nombre:
                _show_message("El nombre es obligatorio.", t["accent"])
                return
            new_id = save_proveedor({
                "nombre": nombre,
                "domicilio": (tf_d.value or "").strip(),
                "telefono": (tf_t.value or "").strip(),
            })
            _show_message(f"Proveedor '{nombre}' creado.", ft.Colors.GREEN_700)
            page.close(dlg)
            _refresh_all(keep_selected=new_id)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text("Nuevo proveedor", size=16, weight=ft.FontWeight.W_500),
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

    _refresh_list()
    saldos_map = {r["id"]: r["saldo"] for r in get_resumen_proveedores()}
    todos = get_proveedores()
    todos.sort(key=lambda c: (-(saldos_map.get(c["id"], 0) > 0), c["nombre"].lower()))
    if todos:
        selected_id["value"] = todos[0]["id"]
        _render_panel(todos[0])
    else:
        _render_empty_panel()

    help_btn = HelpButton([
        {"text": "Andá a Compras para registrar una compra", "action": ("Ir a Compras", 0)},
        {"text": "Volvé — la deuda aparece automáticamente"},
        {"text": "Registrá pagos desde el panel derecho"},
    ], page, on_switch_tab)

    view = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Proveedores", size=16, weight=ft.FontWeight.W_500, expand=True),
                        help_btn,
                        ft.ElevatedButton(
                            "Nuevo proveedor", icon=ft.Icons.PERSON_ADD_OUTLINED,
                            on_click=_open_nuevo_proveedor,
                            style=ft.ButtonStyle(
                                bgcolor=t["accent"], color=t["accent_text"],
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(10, 18),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=ft.Row(
                        [
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
                            right_panel,
                        ],
                        spacing=0, expand=True,
                    ),
                    expand=True,
                    border=ft.border.all(0.5, t["border"]),
                    border_radius=12,
                    bgcolor=t["bg_page"],
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
            ],
            spacing=8, expand=True,
        ),
        padding=ft.padding.only(top=8),
        expand=True,
    )

    view.refresh_data = lambda: _refresh_all(keep_selected=selected_id["value"])
    return view
