import logging
import flet as ft

log = logging.getLogger("mvp10")

from db.database import (
    get_saldo_wasi,
    get_movimientos_wasi,
    registrar_movimiento_wasi
)

def _fmt(val: float) -> str:
    try:
        return f"${int(float(val)):,}".replace(",", ".")
    except Exception:
        return "$0"

from views.flow_guide import HelpButton

def CuentaWasiView(page: ft.Page, t: dict, on_switch_tab=None):
    # ── Paneles ───────────────────────────────────────────────────────────────
    movimientos_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    
    saldo_text = ft.Text("$0", size=42, weight=ft.FontWeight.W_800, color=t["accent"])
    ingresos_text = ft.Text("$0", size=16, weight=ft.FontWeight.W_600, color=ft.colors.GREEN_700)
    egresos_text = ft.Text("$0", size=16, weight=ft.FontWeight.W_600, color=ft.colors.RED_700)

    def _show_message(text: str, color=t["accent"]):
        sb = ft.SnackBar(ft.Text(text, color=ft.colors.WHITE), bgcolor=color, duration=3200)
        page.open(sb)

    # ── Registrar Movimiento (Modal) ──────────────────────────────────────────
    def _open_registro(tipo_movimiento: str):
        # tipo_movimiento: "Ingreso" o "Egreso"
        is_ingreso = tipo_movimiento == "Ingreso"
        
        opciones_categoria = [
            ft.dropdown.Option("Otro")
        ]
        
        if is_ingreso:
            opciones_categoria.insert(0, ft.dropdown.Option("Factura / Venta"))
        else:
            opciones_categoria.insert(0, ft.dropdown.Option("Proveedores"))
            opciones_categoria.insert(1, ft.dropdown.Option("Sueldos"))

        dd_categoria = ft.Dropdown(
            options=opciones_categoria,
            value=opciones_categoria[0].key,
            border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(4, 10),
            border_color=t["border"], focused_border_color=t["accent"],
            color=t["text_primary"], bgcolor=t["bg_input"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
        )
        
        tf_concepto = ft.TextField(
            hint_text="Descripción del movimiento...",
            border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
        )
        
        tf_monto = ft.TextField(
            hint_text="0.00",
            border_radius=7, height=38, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=t["border"], focused_border_color=t["accent"],
            bgcolor=t["bg_input"], color=t["text_primary"],
            hint_style=ft.TextStyle(color=t["text_hint"]),
        )

        def _guardar(ev, d):
            raw_monto = (tf_monto.value or "").strip().replace(".", "").replace(",", ".")
            try:
                monto = float(raw_monto)
            except ValueError:
                _show_message("Ingresá un monto válido.", t["accent"])
                return
            
            if monto <= 0:
                _show_message("El monto debe ser mayor a cero.", t["accent"])
                return
            
            registrar_movimiento_wasi(
                tipo=tipo_movimiento,
                categoria=dd_categoria.value,
                concepto=(tf_concepto.value or "").strip(),
                monto=monto
            )
            
            _show_message(f"{tipo_movimiento} registrado correctamente.", ft.colors.GREEN_700)
            page.close(d)
            _refresh_data()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Registrar {tipo_movimiento}", size=16, weight=ft.FontWeight.W_500, color=t["text_primary"]),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Categoría", size=12, color=t["text_secondary"]),
                        dd_categoria,
                        ft.Text("Concepto / Detalle", size=12, color=t["text_secondary"]),
                        tf_concepto,
                        ft.Text("Monto", size=12, color=t["text_secondary"]),
                        tf_monto,
                    ],
                    spacing=8, tight=True,
                ),
                width=380,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
                ft.ElevatedButton(
                    "Guardar",
                    bgcolor=ft.colors.GREEN_700 if is_ingreso else ft.colors.RED_700,
                    color=t["accent_text"],
                    on_click=lambda ev: _guardar(ev, dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── Renderizado de la lista ───────────────────────────────────────────────
    def _build_row(mov: dict, zebra: bool):
        is_ingreso = mov.get("tipo") == "Ingreso"
        color_monto = ft.colors.GREEN_700 if is_ingreso else ft.colors.RED_700
        signo = "+" if is_ingreso else "-"
        
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(mov.get("fecha", ""), size=12, color=t["text_secondary"], width=120),
                    ft.Container(
                        ft.Text(mov.get("categoria", ""), size=11, color=color_monto, weight=ft.FontWeight.W_600),
                        bgcolor=t["bg_card"] if is_ingreso else t["bg_row_odd"],
                        border_radius=20, padding=ft.padding.symmetric(3, 9), width=120,
                    ),
                    ft.Text(mov.get("concepto", ""), size=13, color=t["text_primary"], expand=True),
                    ft.Text(
                        f"{signo} {_fmt(mov.get('monto', 0))}",
                        size=14, color=color_monto, weight=ft.FontWeight.W_600, width=120,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(12, 16),
            bgcolor=t["bg_card"] if zebra else t["bg_row_odd"],
            border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
        )

    def _refresh_data():
        # Actualizar Tarjetas de Saldo
        saldos = get_saldo_wasi()
        saldo_text.value = _fmt(saldos["saldo"])
        ingresos_text.value = _fmt(saldos["ingresos"])
        egresos_text.value = _fmt(saldos["egresos"])
        
        # Color del saldo según si es positivo o negativo
        if saldos["saldo"] < 0:
            saldo_text.color = ft.colors.RED_700
        else:
            saldo_text.color = t["accent"]

        if saldo_text.page:
            saldo_text.update()
            ingresos_text.update()
            egresos_text.update()

        # Actualizar Lista
        movimientos_col.controls.clear()
        movimientos_col.controls.append(
            ft.Container(
                ft.Row(
                    [
                        ft.Text("Fecha", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=120),
                        ft.Text("Categoría", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=120),
                        ft.Text("Concepto", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], expand=True),
                        ft.Text("Monto", size=11, weight=ft.FontWeight.W_500, color=t["text_secondary"], width=120, text_align=ft.TextAlign.RIGHT),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.symmetric(10, 16),
                bgcolor=t["bg_header"],
                border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border"])),
            )
        )

        movimientos = get_movimientos_wasi()
        if not movimientos:
            movimientos_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.RECEIPT_LONG_OUTLINED, size=42, color=t["text_hint"]),
                            ft.Text("No hay movimientos registrados.", size=15, weight=ft.FontWeight.W_500, color=t["text_primary"]),
                        ],
                        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0), padding=ft.padding.all(40), expand=True,
                )
            )
        else:
            for i, m in enumerate(movimientos):
                movimientos_col.controls.append(_build_row(m, i % 2 == 0))

        if movimientos_col.page:
            movimientos_col.update()

    _refresh_data()

    # ── Layout Principal ──────────────────────────────────────────────────────
    summary_cards = ft.Row(
        [
            ft.Container(
                content=ft.Column([ft.Text("SALDO TOTAL", size=11, color=t["text_secondary"], weight=ft.FontWeight.W_600), saldo_text], spacing=0),
                bgcolor=t["bg_card"], border_radius=12, padding=24, expand=True,
                border=ft.border.all(1, t["border_light"])
            ),
            ft.Container(
                content=ft.Column([ft.Text("TOTAL INGRESOS", size=11, color=t["text_secondary"]), ingresos_text], spacing=4),
                bgcolor=t["bg_card"], border_radius=12, padding=24, width=200,
                border=ft.border.all(0.5, t["border"])
            ),
            ft.Container(
                content=ft.Column([ft.Text("TOTAL EGRESOS", size=11, color=t["text_secondary"]), egresos_text], spacing=4),
                bgcolor=t["bg_card"], border_radius=12, padding=24, width=200,
                border=ft.border.all(0.5, t["border"])
            ),
        ],
        spacing=16,
    )

    help_btn = HelpButton([
        {"text": "Cobrá facturas desde Dashboard", "action": ("Ir a Dashboard", 0)},
        {"text": "Volvé — los ingresos aparecen automáticamente"},
        {"text": "Registrá salidas manuales con el botón superior"},
    ], page, on_switch_tab)

    view = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Cuenta", size=22, weight=ft.FontWeight.W_500, color=t["text_primary"]),
                                ft.Text("Control general de ingresos y salidas (proveedores, sueldos, etc.)", size=13, color=t["text_secondary"]),
                            ],
                            spacing=2, expand=True,
                        ),
                        help_btn,
                        ft.ElevatedButton(
                            "Registrar Salida", icon=ft.icons.ARROW_DOWNWARD, 
                            bgcolor=t["bg_card"], color=ft.colors.RED_700,
                            on_click=lambda e: _open_registro("Egreso"),
                            style=ft.ButtonStyle(side=ft.BorderSide(1, ft.colors.RED_700)),
                        ),
                        ft.ElevatedButton(
                            "Registrar Ingreso", icon=ft.icons.ARROW_UPWARD, 
                            bgcolor=t["accent"], color=t["accent_text"],
                            on_click=lambda e: _open_registro("Ingreso")
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                summary_cards,
                ft.Container(
                    content=movimientos_col,
                    expand=True, border=ft.border.all(0.5, t["border"]), 
                    border_radius=12, bgcolor=t["bg_card"],
                ),
            ],
            spacing=16, expand=True,
        ),
        padding=28, expand=True,
        bgcolor=t["bg_page"],
    )

    view.refresh_data = _refresh_data
    return view