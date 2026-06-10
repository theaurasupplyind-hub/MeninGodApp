import logging
import flet as ft

log = logging.getLogger("mvp10")

from db.database import (
    get_saldo_wasi,
    get_movimientos_wasi,
)

def _fmt(val: float) -> str:
    try:
        return f"${int(float(val)):,}".replace(",", ".")
    except Exception:
        return "$0"

from views.flow_guide import HelpButton

def CuentaWasiView(page: ft.Page, t: dict, on_switch_tab=None):
    # ── Paneles ───────────────────────────────────────────────────────────────
    MOV_MAX = 100
    _show_all: dict[str, bool] = {"value": False}

    movimientos_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    
    saldo_text = ft.Text("$0", size=42, weight=ft.FontWeight.W_800, color=t["accent"])
    ingresos_text = ft.Text("$0", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.GREEN_700)
    egresos_text = ft.Text("$0", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.RED_700)

    def _show_message(text: str, color=t["accent"]):
        sb = ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color, duration=3200)
        page.open(sb)

    # ── Renderizado de la lista ───────────────────────────────────────────────
    def _build_row(mov: dict, zebra: bool):
        is_ingreso = mov.get("tipo") == "Ingreso"
        color_monto = ft.Colors.GREEN_700 if is_ingreso else ft.Colors.RED_700
        signo = "+" if is_ingreso else "-"
        concepto = mov.get("concepto", "")

        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(mov.get("fecha", ""), size=12, color=t["text_secondary"], width=120),
                    ft.Container(
                        ft.Text(mov.get("categoria", ""), size=11, color=color_monto, weight=ft.FontWeight.W_600),
                        bgcolor=t["bg_card"] if is_ingreso else t["bg_row_odd"],
                        border_radius=20, padding=ft.padding.symmetric(3, 9), width=120,
                    ),
                    ft.Text(concepto, size=13, color=t["text_primary"], expand=True),
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
            saldo_text.color = ft.Colors.RED_700
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

        all_movimientos = get_movimientos_wasi(limit=100000)
        if not all_movimientos:
            movimientos_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=42, color=t["text_hint"]),
                            ft.Text("No hay movimientos registrados.", size=15, weight=ft.FontWeight.W_500, color=t["text_primary"]),
                        ],
                        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0), padding=ft.padding.all(40), expand=True,
                )
            )
        else:
            visible = all_movimientos if _show_all["value"] else all_movimientos[:MOV_MAX]
            for i, m in enumerate(visible):
                movimientos_col.controls.append(_build_row(m, i % 2 == 0))
            remaining = len(all_movimientos) - MOV_MAX
            if remaining > 0 and not _show_all["value"]:
                def _load_more_movs(e):
                    _show_all["value"] = True
                    _refresh_data()
                movimientos_col.controls.append(
                    ft.Container(
                        content=ft.ElevatedButton(
                            f"Cargar más ({remaining} restantes)",
                            on_click=_load_more_movs,
                            style=ft.ButtonStyle(
                                bgcolor=t.get("bg_header", t["bg_card"]),
                                color=t["accent"],
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                        ),
                        alignment=ft.alignment.center,
                        padding=ft.padding.all(14),
                    )
                )

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
        {"text": "Los ingresos se registran automáticamente al cobrar facturas"},
        {"text": "Los egresos se registran automáticamente al pagar proveedores o registrar compras"},
        {"text": "Todo se sincroniza en tiempo real desde cada vista"},
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