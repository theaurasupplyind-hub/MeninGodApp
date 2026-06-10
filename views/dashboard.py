from datetime import datetime

import flet as ft

from db.database import get_facturas, get_stats, update_factura_estado, update_factura_envio, get_connection
from db.database import registrar_cobro_factura, get_cliente_by_nombre, get_actividad_reciente, get_actividad_reciente_days
from theme import get_theme

def _fmt(val: float) -> str:
    try:
        return f"${int(float(val)):,}".replace(",", ".")
    except Exception:
        return "$0"


def _get_estado_colors(estado: str, page: ft.Page) -> tuple:
    t = get_theme(page)
    return {
        "Pendiente": t["badge_pendiente"],
        "Pagado":    t["badge_pagado"],
    }.get(estado, t["badge_cancelado"])

def _get_envio_colors(envio_estado: str, page: ft.Page) -> tuple:
    t = get_theme(page)
    return {
        "No enviado": t["badge_cancelado"],
        "Enviado":    t["badge_enviado"],
    }.get(envio_estado, t["badge_cancelado"])


def _metric_card(
    label: str,
    value: str,
    t: dict,
    subtitle: str = "",
    value_color: str = ft.Colors.BLUE_800,
):
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(label, size=12, color=t["text_secondary"]),
                ft.Text(value, size=22, weight=ft.FontWeight.W_500, color=value_color),
                ft.Text(subtitle, size=11, color=t["text_secondary"]),
            ],
            spacing=4,
        ),
        bgcolor=t["bg_header"],
        border_radius=12,
        padding=ft.padding.all(16),
        expand=True,
    )


def _estado_toggle(page: ft.Page, factura_id: int, factura: dict, estado_inicial: str, on_estado_changed=None):
    """Toggle Pendiente ↔ Pagado."""

    val = estado_inicial if estado_inicial in ("Pendiente", "Pagado") else "Pendiente"
    bg, fg = _get_estado_colors(val, page)

    label = ft.Text(val, size=11, color=fg, weight=ft.FontWeight.W_500)

    badge = ft.Container(
        content=ft.Row([label], spacing=2, tight=True),
        bgcolor=bg, border_radius=20,
        padding=ft.padding.symmetric(3, 8),
        tooltip="Click para cambiar estado",
        ink=True,
    )

    def on_click(e):
        nuevo = "Pagado" if label.value == "Pendiente" else "Pendiente"
        label.value = nuevo
        new_bg, new_fg = _get_estado_colors(nuevo, page)
        label.color = new_fg
        badge.bgcolor = new_bg
        badge.update()

        db_estado_previo = None
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT estado FROM facturas WHERE id = ?", (factura_id,))
            row = c.fetchone()
            db_estado_previo = row["estado"] if row else None
            conn.close()
        except Exception:
            pass

        try:
            update_factura_estado(factura_id, nuevo)
        except Exception as ex:
            print(f"[dashboard] Error al actualizar estado: {ex}")

        if nuevo == "Pagado" and db_estado_previo != "Pagado":
            try:
                total = factura.get("total", 0)
                cliente_nombre = factura.get("cliente_nombre", "")
                numero = factura.get("numero", "")
                cliente = get_cliente_by_nombre(cliente_nombre)
                cliente_id = cliente["id"] if cliente else None
                if total > 0:
                    registrar_cobro_factura(
                        factura_id=factura_id,
                        numero_factura=numero,
                        cliente_id=cliente_id,
                        cliente_nombre=cliente_nombre,
                        monto=total,
                        medio_pago="Efectivo",
                        nota="Cobro directo desde Dashboard",
                    )
            except Exception as ex:
                print(f"[dashboard] Error al registrar cobro: {ex}")

        if on_estado_changed:
            on_estado_changed(factura_id, nuevo)

    badge.on_click = on_click
    return badge


def _envio_toggle(page: ft.Page, factura_id: int, envio_inicial: str, on_refresh=None):
    """Toggle No enviado ↔ Enviado."""

    val = envio_inicial if envio_inicial in ("No enviado", "Enviado") else "No enviado"
    bg, fg = _get_envio_colors(val, page)

    label = ft.Text(val, size=11, color=fg, weight=ft.FontWeight.W_500)

    badge = ft.Container(
        content=ft.Row([label], spacing=2, tight=True),
        bgcolor=bg, border_radius=20,
        padding=ft.padding.symmetric(3, 8),
        tooltip="Click para cambiar estado de envío",
        ink=True,
    )

    def on_click(e):
        nuevo = "Enviado" if label.value == "No enviado" else "No enviado"
        label.value = nuevo
        new_bg, new_fg = _get_envio_colors(nuevo, page)
        label.color = new_fg
        badge.bgcolor = new_bg
        badge.update()

        try:
            update_factura_envio(factura_id, nuevo)
        except Exception as ex:
            print(f"[dashboard] Error al actualizar envío: {ex}")

        if on_refresh:
            on_refresh(None)

    badge.on_click = on_click
    return badge

def _cobro_button(page: ft.Page, factura: dict, on_cobro=None):
    """Botón que abre el diálogo de registro de cobro."""
    t = get_theme(page)
    if factura.get("estado") == "Pagado":
        return ft.Container(width=90)  # espacio vacío si ya está pagado

    def _open_cobro(e):
        tf_monto = ft.TextField(
            value=str(int(factura["total"] or 0)),
            border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=140,
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
        tf_nota = ft.TextField(
            hint_text="Nota opcional",
            border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            expand=True,
        )

        def _confirmar(ev, dlg):
            from services.auth_service import AuthService
            raw = (tf_monto.value or "").strip().replace(".", "").replace(",", ".")
            try:
                monto = float(raw)
            except ValueError:
                return
            if monto <= 0:
                return

            cliente = get_cliente_by_nombre(factura.get("cliente_nombre", ""))
            resultado = registrar_cobro_factura(
                factura_id=factura["id"],
                numero_factura=factura["numero"],
                cliente_id=cliente["id"] if cliente else None,
                cliente_nombre=factura.get("cliente_nombre", ""),
                monto=monto,
                medio_pago=dd_medio.value,
                nota=tf_nota.value or "",
            )
            AuthService().track("pago", factura["numero"], f"Cobro ${int(monto):,} — Factura {factura['numero']} — {dd_medio.value}".replace(",", "."))
            page.close(dlg)
            sb_text = f"Cobro registrado."
            if resultado["saldo_restante"] > 0:
                sb_text += f" Saldo restante: ${int(resultado['saldo_restante']):,}".replace(",", ".")
            page.open(ft.SnackBar(ft.Text(sb_text, color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_700, duration=3500))
            if on_cobro:
                on_cobro()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text(f"Registrar cobro — {factura['numero']}", size=15, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"Cliente: {factura.get('cliente_nombre') or '—'}", size=13, weight=ft.FontWeight.W_500),
                        ft.Text(f"Total factura: ${int(factura['total'] or 0):,}".replace(",", "."), size=12, color=t["text_secondary"]),
                        ft.Divider(height=14, color=t["border_light"]),
                        ft.Text("Monto a cobrar", size=12, color=t["text_secondary"]),
                        ft.Row([tf_monto, dd_medio], spacing=8),
                        ft.Text("Nota", size=12, color=t["text_secondary"]),
                        tf_nota,
                    ],
                    spacing=8, tight=True,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                ft.ElevatedButton(
                    "Confirmar cobro",
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                    on_click=lambda ev: _confirmar(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    return ft.IconButton(
        ft.Icons.ATTACH_MONEY,
        icon_size=16,
        icon_color=ft.Colors.GREEN_700,
        tooltip="Registrar cobro",
        on_click=_open_cobro,
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )

from views.flow_guide import HelpButton

def DashboardView(page: ft.Page, on_nueva_factura=None, on_refresh=None, on_estado_changed=None, on_switch_tab=None, on_toggle_fullscreen=None):
    t = get_theme(page)
    MOV_MAX = 100
    _show_all: dict[str, bool] = {"value": False}
    stats = get_stats()
    all_facturas = get_facturas(10000)

    total_all = stats.get("total_all", 0) or 0
    count_all = stats.get("count_all", 0) or 0
    cobrado = stats.get("cobrado", 0) or 0
    pendiente = stats.get("pendiente", 0) or 0
    count_pendiente = stats.get("count_pendiente", 0) or 0
    pct_cobrado = int(cobrado / max(total_all, 1) * 100)

    metrics = ft.Row(
        [
            _metric_card("Total facturado", _fmt(total_all), t, "Acumulado"),
            _metric_card("Cobrado", _fmt(cobrado), t, f"{pct_cobrado}% del total", ft.Colors.GREEN_700),
            _metric_card("Pendiente", _fmt(pendiente), t, f"{count_pendiente} facturas", ft.Colors.ORANGE_700),
            _metric_card("Facturas emitidas", str(count_all), t, "Total"),
        ],
        spacing=12,
    )

    invoices_content = ft.Column(spacing=10, expand=True)

    def _build_invoices_section():
        invoices_content.controls.clear()
        show_all = _show_all["value"]
        display_facturas = all_facturas if show_all else all_facturas[:MOV_MAX]

        rows = []
        for factura in display_facturas:
            estado_actual = factura["estado"] or "Pendiente"
            envio_actual = factura.get("envio_estado") or "No enviado"
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(factura["numero"], size=13, color=ft.Colors.BLUE_600)),
                        ft.DataCell(ft.Text(factura["cliente_nombre"] or "", size=13)),
                        ft.DataCell(ft.Text(factura["fecha"], size=13, color=t["text_secondary"])),
                        ft.DataCell(ft.Text(_fmt(factura["total"] or 0), size=13, weight=ft.FontWeight.W_500)),
                        ft.DataCell(
                            ft.Text(
                                _fmt(factura.get("deuda", 0) or 0),
                                size=13, weight=ft.FontWeight.W_500,
                                color=ft.Colors.RED_700 if (factura.get("deuda") or 0) > 0 else ft.Colors.GREEN_700,
                            )
                        ),
                        ft.DataCell(
                            _estado_toggle(
                                page,
                                factura_id=factura["id"],
                                factura=factura,
                                estado_inicial=estado_actual,
                                on_estado_changed=on_estado_changed,
                            )
                        ),
                        ft.DataCell(
                            _envio_toggle(
                                page,
                                factura_id=factura["id"],
                                envio_inicial=envio_actual,
                                on_refresh=on_refresh,
                            )
                        ),
                        ft.DataCell(
                            _cobro_button(page, factura, on_cobro=on_refresh)
                        ),
                    ]
                )
            )

        invoices_content.controls.append(
            ft.Text("Últimas facturas", size=15, weight=ft.FontWeight.W_500)
        )
        invoices_content.controls.append(ft.Divider(height=1, color=t["border_light"]))

        if rows:
            invoices_content.controls.append(
                ft.ListView(
                    controls=[
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("N° Factura", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"])),
                                ft.DataColumn(ft.Text("Cliente", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"])),
                                ft.DataColumn(ft.Text("Fecha", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"])),
                                ft.DataColumn(
                                    ft.Text("Total", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"]),
                                    numeric=True,
                                ),
                                ft.DataColumn(
                                    ft.Text("Deuda", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"]),
                                    numeric=True,
                                ),
                                ft.DataColumn(ft.Text("Estado", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"])),
                                ft.DataColumn(ft.Text("Envío", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"])),
                                ft.DataColumn(ft.Text("Cobro", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"])),
                            ],
                            rows=rows,
                            border=ft.border.all(0.5, t["border"]),
                            border_radius=8,
                            horizontal_lines=ft.border.BorderSide(0.5, t["border_light"]),
                            column_spacing=20,
                            data_row_max_height=44,
                        )
                    ],
                    expand=True,
                    auto_scroll=False,
                )
            )
        else:
            invoices_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=42, color=t["text_secondary"]),
                            ft.Text("Todavía no hay facturas registradas.", size=15, weight=ft.FontWeight.W_500),
                            ft.Text(
                                "Crea tu primera factura para ver actividad y métricas reales.",
                                size=12,
                                color=t["text_secondary"],
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                )
            )

        remaining = len(all_facturas) - MOV_MAX
        if remaining > 0 and not show_all:
            def _load_more_inv(e):
                _show_all["value"] = True
                _build_invoices_section()
            invoices_content.controls.append(
                ft.Container(
                    content=ft.ElevatedButton(
                        f"Cargar más ({remaining} restantes)",
                        on_click=_load_more_inv,
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

        if invoices_content.page:
            invoices_content.update()

    _build_invoices_section()

    btn_refresh = ft.OutlinedButton(
        "Actualizar",
        icon=ft.Icons.REFRESH,
        on_click=on_refresh,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(10, 16),
        ),
    )

    btn_nueva = ft.ElevatedButton(
        "Nueva factura",
        icon=ft.Icons.ADD,
        on_click=on_nueva_factura,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(10, 18),
        ),
    )

    help_btn = HelpButton([
        {"text": "Creá una factura de venta", "action": ("Ir a Facturación", 1)},
        {"text": "Volvé y marcá Pagado (clic en el badge de estado)"},
        {"text": "Revisá el cobro registrado", "action": ("Ir a Cuenta", 4)},
        {"text": "Revisá la cuenta del cliente", "action": ("Ir a Clientes", 2)},
    ], page, on_switch_tab=on_switch_tab)

    # ── Actividad reciente ─────────────────────────────────────────────────────
    _TIPO_LABELS = {
        "factura": ("Factura", ft.Icons.RECEIPT_LONG_OUTLINED, ft.Colors.BLUE_600),
        "compra": ("Compra", ft.Icons.SHOPPING_CART_OUTLINED, ft.Colors.ORANGE_600),
        "pago": ("Pago", ft.Icons.ATTACH_MONEY, ft.Colors.GREEN_600),
        "ajuste_stock": ("Ajuste", ft.Icons.INVENTORY_2_OUTLINED, ft.Colors.GREY_500),
        "reduccion_stock": ("Reducción", ft.Icons.REMOVE_CIRCLE_OUTLINE, ft.Colors.RED_400),
    }
    actividades = get_actividad_reciente_days(60, 30)

    def _build_act_row(act: dict) -> ft.Control:
        tipo_label, icon, icon_color = _TIPO_LABELS.get(act["tipo"], (act["tipo"], ft.Icons.CIRCLE, t["text_secondary"]))
        return ft.Row(
            [
                ft.Icon(icon, size=14, color=icon_color),
                ft.Column(
                    [
                        ft.Text(f"{act.get('usuario_nombre', '?')} — {tipo_label}", size=12, weight=ft.FontWeight.W_500),
                        ft.Text(act.get("descripcion", "") or act.get("referencia", ""), size=11, color=t["text_secondary"]),
                    ],
                    spacing=1, expand=True,
                ),
                ft.Text(act.get("created_at", "")[5:16], size=10, color=t["text_hint"]),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    act_controls = [_build_act_row(a) for a in actividades]

    if not act_controls:
        act_controls = [
            ft.Row(
                [ft.Icon(ft.Icons.HISTORY_OUTLINED, size=16, color=ft.Colors.GREY_500), ft.Text("Sin actividad reciente", size=12, color=t["text_hint"])],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        ]

    def _open_full_activity(e):
        all_acts = get_actividad_reciente_days(60, 200)
        from datetime import date, timedelta
        today = date.today()
        yesterday = today - timedelta(days=1)

        def _group_label(d: date) -> str:
            if d == today:
                return "Hoy"
            if d == yesterday:
                return "Ayer"
            return d.strftime("%d/%m/%Y")

        groups: list[tuple[str, list[ft.Control]]] = []
        current_key = None
        current_rows: list[ft.Control] = []
        for act in all_acts:
            raw = act.get("created_at", "")[:10]
            try:
                d = datetime.strptime(raw, "%Y-%m-%d").date()
            except Exception:
                d = date.min
            key = _group_label(d)
            if key != current_key and current_rows:
                groups.append((current_key, current_rows))
                current_rows = []
            current_key = key
            current_rows.append(_build_act_row(act))
        if current_rows:
            groups.append((current_key, current_rows))

        sections: list[ft.Control] = []
        for label, rows in groups:
            sections.append(ft.Text(label.upper(), size=11, weight=ft.FontWeight.W_600, color=t["text_secondary"]))
            sections.append(ft.Column(rows, spacing=6))
            sections.append(ft.Divider(height=8, color=t["border_light"]))

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=t["bg_card"],
            title=ft.Text("Historial de actividad (60 días)", size=16, weight=ft.FontWeight.W_500),
            content=ft.Container(
                content=ft.Column(sections, spacing=4, scroll=ft.ScrollMode.AUTO),
                width=700,
                height=500,
                padding=ft.padding.only(top=4),
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda ev: page.close(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    activity_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Actividad reciente", size=15, weight=ft.FontWeight.W_500, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.OPEN_IN_FULL,
                            icon_size=16,
                            tooltip="Ver historial completo (60 días)",
                            on_click=_open_full_activity,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=1, color=t["border_light"]),
                ft.Column(act_controls, spacing=8),
            ],
            spacing=10,
        ),
        bgcolor=t["bg_card"],
        border=ft.border.all(0.5, t["border"]),
        border_radius=12,
        padding=16,
        expand=True,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Dashboard", size=22, weight=ft.FontWeight.W_500),
                                ft.Text(
                                    datetime.now().strftime("%B %Y").capitalize(),
                                    size=13,
                                    color=t["text_secondary"],
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        help_btn,
                        ft.IconButton(
                            icon=ft.Icons.FULLSCREEN,
                            icon_size=18,
                            icon_color=t["text_secondary"],
                            tooltip="Pantalla completa (F11)",
                            on_click=lambda e: on_toggle_fullscreen() if on_toggle_fullscreen else None,
                        ),
                        btn_refresh,
                        btn_nueva,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                metrics,
                ft.Row(
                    [
                        ft.Container(
                            content=invoices_content,
                            bgcolor=t["bg_card"],
                            border=ft.border.all(0.5, t["border"]),
                            border_radius=12,
                            padding=16,
                            expand=3,
                        ),
                        activity_card,
                    ],
                    spacing=16,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=16,
            expand=True,
        ),
        padding=28,
        expand=True,
    )