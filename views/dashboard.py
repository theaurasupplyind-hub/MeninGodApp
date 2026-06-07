from datetime import datetime

import flet as ft

from db.database import get_facturas, get_stats, update_factura_estado, get_connection
from db.database import registrar_cobro_factura, get_cliente_by_nombre
from theme import get_theme

def _fmt(val: float) -> str:
    try:
        return f"${int(float(val)):,}".replace(",", ".")
    except Exception:
        return "$0"


# Ciclo de estados al hacer click
ESTADO_CICLO = ["Pendiente", "Entregado", "Pagado"]

def _get_estado_colors(estado: str, page: ft.Page) -> tuple:
    t = get_theme(page)
    return {
        "Cobrada":   t["badge_pagado"],
        "Pendiente": t["badge_pendiente"],
        "Vencida":   t["badge_sin_stock"],
        "Entregado": t["badge_entregado"],
        "Pagado":    t["badge_pagado"],
    }.get(estado, (t["badge_cancelado"]))


def _metric_card(
    label: str,
    value: str,
    t: dict,
    subtitle: str = "",
    value_color: str = ft.colors.BLUE_800,
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


def _status_badge_clickable(page: ft.Page, factura_id: int, factura: dict, estado_inicial: str, on_estado_changed=None):
    """Badge de estado interactivo que cicla entre Pendiente -> Entregado -> Pagado al hacer click."""

    estado_ref = [estado_inicial if estado_inicial in ESTADO_CICLO else "Pendiente"]

    def _get_colors(estado: str):
        return _get_estado_colors(estado, page)

    bg, fg = _get_colors(estado_ref[0])

    label = ft.Text(
        estado_ref[0],
        size=11,
        color=fg,
        weight=ft.FontWeight.W_500,
    )

    arrow_icon = ft.Icon(ft.icons.UNFOLD_MORE, size=12, color=fg)

    badge = ft.Container(
        content=ft.Row(
            [label, arrow_icon],
            spacing=2,
            tight=True,
        ),
        bgcolor=bg,
        border_radius=20,
        padding=ft.padding.symmetric(3, 8),
        tooltip="Click para cambiar estado",
        ink=True,
    )

    def on_click(e):
        idx = ESTADO_CICLO.index(estado_ref[0]) if estado_ref[0] in ESTADO_CICLO else 0
        nuevo_estado = ESTADO_CICLO[(idx + 1) % len(ESTADO_CICLO)]
        estado_ref[0] = nuevo_estado

        new_bg, new_fg = _get_colors(nuevo_estado)
        label.value = nuevo_estado
        label.color = new_fg
        arrow_icon.color = new_fg
        badge.bgcolor = new_bg
        badge.update()

        # Consultar estado previo en DB para evitar duplicar cobros
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
            update_factura_estado(factura_id, nuevo_estado)
        except Exception as ex:
            print(f"[dashboard] Error al actualizar estado: {ex}")

        if nuevo_estado == "Pagado" and db_estado_previo != "Pagado":
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
            on_estado_changed(factura_id, nuevo_estado)

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
            border_radius=7, height=38, text_size=13,
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
            page.close(dlg)
            sb_text = f"Cobro registrado."
            if resultado["saldo_restante"] > 0:
                sb_text += f" Saldo restante: ${int(resultado['saldo_restante']):,}".replace(",", ".")
            page.open(ft.SnackBar(ft.Text(sb_text, color=ft.colors.WHITE), bgcolor=ft.colors.GREEN_700, duration=3500))
            if on_cobro:
                on_cobro()

        dlg = ft.AlertDialog(
            modal=True,
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
                    icon=ft.icons.CHECK_CIRCLE_OUTLINE,
                    bgcolor=ft.colors.GREEN_700,
                    color=ft.colors.WHITE,
                    on_click=lambda ev: _confirmar(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    return ft.IconButton(
        ft.icons.ATTACH_MONEY,
        icon_size=16,
        icon_color=ft.colors.GREEN_700,
        tooltip="Registrar cobro",
        on_click=_open_cobro,
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )

from views.flow_guide import HelpButton

def DashboardView(page: ft.Page, on_nueva_factura=None, on_refresh=None, on_estado_changed=None, on_switch_tab=None):
    t = get_theme(page)
    stats = get_stats()
    facturas = get_facturas(20)

    total_all = stats.get("total_all", 0) or 0
    count_all = stats.get("count_all", 0) or 0
    cobrado = stats.get("cobrado", 0) or 0
    pendiente = stats.get("pendiente", 0) or 0
    count_pendiente = stats.get("count_pendiente", 0) or 0
    pct_cobrado = int(cobrado / max(total_all, 1) * 100)

    metrics = ft.Row(
        [
            _metric_card("Total facturado", _fmt(total_all), t, "Acumulado"),
            _metric_card("Cobrado", _fmt(cobrado), t, f"{pct_cobrado}% del total", ft.colors.GREEN_700),
            _metric_card("Pendiente", _fmt(pendiente), t, f"{count_pendiente} facturas", ft.colors.ORANGE_700),
            _metric_card("Facturas emitidas", str(count_all), t, "Total"),
        ],
        spacing=12,
    )

    rows = []
    for factura in facturas:
        estado_actual = factura["estado"] or "Pendiente"
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(factura["numero"], size=13, color=ft.colors.BLUE_600)),
                    ft.DataCell(ft.Text(factura["cliente_nombre"] or "", size=13)),
                    ft.DataCell(ft.Text(factura["fecha"], size=13, color=t["text_secondary"])),
                    ft.DataCell(ft.Text(_fmt(factura["total"] or 0), size=13, weight=ft.FontWeight.W_500)),
                    ft.DataCell(
                        _status_badge_clickable(
                            page,
                            factura_id=factura["id"],
                            factura=factura,
                            estado_inicial=estado_actual,
                            on_estado_changed=on_estado_changed,
                        )
                    ),
                    ft.DataCell(
                        _cobro_button(page, factura, on_cobro=on_refresh)
                    ),
                ]
            )
        )

    table_content: ft.Control
    if rows:
        table_content = ft.ListView(
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
                        ft.DataColumn(ft.Text("Estado", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"])),
                        ft.DataColumn(ft.Text("Cobro", size=12, weight=ft.FontWeight.W_500, color=t["text_secondary"])),
                    ],
                    rows=rows,
                    border=ft.border.all(0.5, ft.colors.GREY_300),
                    border_radius=8,
                    horizontal_lines=ft.border.BorderSide(0.5, ft.colors.GREY_200),
                    column_spacing=20,
                    data_row_max_height=44,
                )
            ],
            expand=True,
            auto_scroll=False,
        )
    else:
        table_content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.RECEIPT_LONG_OUTLINED, size=42, color=ft.colors.GREY_400),
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

    btn_refresh = ft.OutlinedButton(
        "Actualizar",
        icon=ft.icons.REFRESH,
        on_click=on_refresh,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(10, 16),
        ),
    )

    btn_nueva = ft.ElevatedButton(
        "Nueva factura",
        icon=ft.icons.ADD,
        on_click=on_nueva_factura,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.BLUE_700,
            color=ft.colors.WHITE,
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
                        btn_refresh,
                        btn_nueva,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                metrics,
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Últimas facturas", size=15, weight=ft.FontWeight.W_500),
                            ft.Divider(height=1, color=t["border_light"]),
                            table_content,
                        ],
                        spacing=10,
                        expand=True,
                    ),
                    bgcolor=t["bg_card"],
                    border=ft.border.all(0.5, t["border"]),
                    border_radius=12,
                    padding=16,
                    expand=True,
                ),
            ],
            spacing=16,
            expand=True,
        ),
        padding=28,
        expand=True,
    )