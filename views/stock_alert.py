"""
stock_alert.py
Campana de notificaciones de stock bajo para el layout principal.
Uso:
    bell = StockAlertBell(page, on_go_stock=lambda: _switch(4))
    # Colocar bell.control en el layout
    # Llamar bell.refresh() cuando se quiera actualizar el badge
"""
import flet as ft
from theme import get_theme
from db.database import get_stock_bajo


def _fmt_stock(val) -> str:
    try:
        v = float(val)
        return str(int(v)) if v == int(v) else f"{v:.1f}"
    except Exception:
        return "0"


class StockAlertBell:
    def __init__(self, page: ft.Page, on_go_stock=None):
        self._page = page
        self._on_go_stock = on_go_stock
        self._badge_text = ft.Text("", size=9, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700)
        self._badge = ft.Container(
            content=self._badge_text,
            bgcolor=ft.Colors.RED_600,
            border_radius=99,
            width=16,
            height=16,
            alignment=ft.Alignment(0, 0),
            visible=False,
            # Posicionado sobre el ícono via Stack
        )
        self._icon_btn = ft.IconButton(
            icon=ft.Icons.NOTIFICATIONS_NONE_OUTLINED,
            icon_size=22,
            icon_color=ft.Colors.GREY_600,
            tooltip="Alertas de stock",
            style=ft.ButtonStyle(padding=ft.padding.all(6)),
            on_click=self._open_panel,
        )
        self.control = ft.Stack(
            [
                self._icon_btn,
                ft.Container(
                    content=self._badge,
                    alignment=ft.Alignment(1, -1),
                    right=2,
                    top=2,
                ),
            ],
            width=40,
            height=40,
        )
        self.refresh()

    def refresh(self):
        alertas = get_stock_bajo()
        count = len(alertas)
        self._badge_text.value = str(count) if count < 10 else "9+"
        self._badge.visible = count > 0
        self._icon_btn.icon = (
            ft.Icons.NOTIFICATIONS_ACTIVE if count > 0
            else ft.Icons.NOTIFICATIONS_NONE_OUTLINED
        )
        self._icon_btn.icon_color = ft.Colors.ORANGE_700 if count > 0 else ft.Colors.GREY_600
        if self.control.parent:
            self.control.update()

    def _open_panel(self, e):
        t = get_theme(self._page)
        alertas = get_stock_bajo()

        if not alertas:
            rows = [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_600, size=20),
                            ft.Text("Todo el stock está en orden.", size=13, color=t["text_secondary"]),
                        ],
                        spacing=8,
                    ),
                    padding=ft.padding.symmetric(12, 4),
                )
            ]
        else:
            rows = []
            for p in alertas:
                actual  = float(p.get("stock_actual", 0) or 0)
                minimo  = float(p.get("stock_minimo", 0) or 0)
                sin_stock = actual <= 0

                rows.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    ft.Icon(
                                        ft.Icons.WARNING_AMBER_ROUNDED if not sin_stock else ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                        size=18,
                                        color=ft.Colors.RED_700 if sin_stock else ft.Colors.ORANGE_700,
                                    ),
                                    width=28,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(p.get("detalle", ""), size=13, weight=ft.FontWeight.W_500),
                                        ft.Text(
                                            f"Stock: {_fmt_stock(actual)}  |  Mínimo: {_fmt_stock(minimo)}",
                                            size=11,
                                            color=t["text_secondary"],
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Container(
                                    ft.Text(
                                        "Sin stock" if sin_stock else "Stock bajo",
                                        size=10,
                                        color=t["badge_sin_stock"][1] if sin_stock else t["badge_bajo"][1],
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    bgcolor=t["badge_sin_stock"][0] if sin_stock else t["badge_bajo"][0],
                                    border_radius=20,
                                    padding=ft.padding.symmetric(3, 8),
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=ft.padding.symmetric(10, 4),
                        border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
                    )
                )

        def _ir_stock(ev, d):
            self._page.close(d)
            if self._on_go_stock:
                self._on_go_stock()

        title_text = (
            "Sin alertas de stock"
            if not alertas
            else f"{len(alertas)} producto{'s' if len(alertas) != 1 else ''} {'necesitan' if len(alertas) != 1 else 'necesita'} reposición"
        )

        dlg = ft.AlertDialog(
            modal=False,
            bgcolor=t["bg_card"],
            title=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.NOTIFICATIONS_ACTIVE if alertas else ft.Icons.NOTIFICATIONS_NONE_OUTLINED,
                        color=ft.Colors.ORANGE_700 if alertas else ft.Colors.GREY_500,
                        size=20,
                    ),
                    ft.Text(title_text, size=15, weight=ft.FontWeight.W_600, expand=True),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    rows,
                    spacing=0,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=360,
                height=min(80 + len(alertas) * 60, 400),
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda ev: self._page.close(dlg)),
                *(
                    [
                        ft.ElevatedButton(
                            "Ir a Productos",
                            icon=ft.Icons.INVENTORY_2_OUTLINED,
                            bgcolor=ft.Colors.BLUE_700,
                            color=ft.Colors.WHITE,
                            on_click=lambda ev: _ir_stock(ev, dlg),
                        )
                    ]
                    if alertas
                    else []
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.open(dlg)