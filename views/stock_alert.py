"""
stock_alert.py
Campana de notificaciones de stock bajo para el layout principal.
Uso:
    bell = StockAlertBell(page, on_go_stock=lambda: _switch(4))
    # Colocar bell.control en el layout
    # Llamar bell.refresh() cuando se quiera actualizar el badge
"""
import flet as ft
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
        self._badge_text = ft.Text("", size=9, color=ft.colors.WHITE, weight=ft.FontWeight.W_700)
        self._badge = ft.Container(
            content=self._badge_text,
            bgcolor=ft.colors.RED_600,
            border_radius=99,
            width=16,
            height=16,
            alignment=ft.Alignment(0, 0),
            visible=False,
            # Posicionado sobre el ícono via Stack
        )
        self._icon_btn = ft.IconButton(
            icon=ft.icons.NOTIFICATIONS_NONE_OUTLINED,
            icon_size=22,
            icon_color=ft.colors.GREY_600,
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
            ft.icons.NOTIFICATIONS_ACTIVE if count > 0
            else ft.icons.NOTIFICATIONS_NONE_OUTLINED
        )
        self._icon_btn.icon_color = ft.colors.ORANGE_700 if count > 0 else ft.colors.GREY_600
        if self.control.parent:
            self.control.update()

    def _open_panel(self, e):
        alertas = get_stock_bajo()

        if not alertas:
            rows = [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, color=ft.colors.GREEN_600, size=20),
                            ft.Text("Todo el stock está en orden.", size=13, color=ft.colors.GREY_700),
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
                                        ft.icons.WARNING_AMBER_ROUNDED if not sin_stock else ft.icons.REMOVE_CIRCLE_OUTLINE,
                                        size=18,
                                        color=ft.colors.RED_700 if sin_stock else ft.colors.ORANGE_700,
                                    ),
                                    width=28,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(p.get("detalle", ""), size=13, weight=ft.FontWeight.W_500),
                                        ft.Text(
                                            f"Stock: {_fmt_stock(actual)}  |  Mínimo: {_fmt_stock(minimo)}",
                                            size=11,
                                            color=ft.colors.GREY_600,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Container(
                                    ft.Text(
                                        "Sin stock" if sin_stock else "Stock bajo",
                                        size=10,
                                        color=ft.colors.RED_700 if sin_stock else ft.colors.ORANGE_700,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    bgcolor=ft.colors.RED_50 if sin_stock else ft.colors.ORANGE_50,
                                    border_radius=20,
                                    padding=ft.padding.symmetric(3, 8),
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=ft.padding.symmetric(10, 4),
                        border=ft.border.only(bottom=ft.border.BorderSide(0.5, ft.colors.GREY_100)),
                    )
                )

        def _ir_stock(ev, d):
            d.open = False
            if d in self._page.overlay:
                self._page.overlay.remove(d)
            self._page.update()
            if self._on_go_stock:
                self._on_go_stock()

        title_text = (
            "Sin alertas de stock"
            if not alertas
            else f"{len(alertas)} producto{'s' if len(alertas) != 1 else ''} {'necesitan' if len(alertas) != 1 else 'necesita'} reposición"
        )

        dlg = ft.AlertDialog(
            modal=False,
            title=ft.Row(
                [
                    ft.Icon(
                        ft.icons.NOTIFICATIONS_ACTIVE if alertas else ft.icons.NOTIFICATIONS_NONE_OUTLINED,
                        color=ft.colors.ORANGE_700 if alertas else ft.colors.GREY_500,
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
                ft.TextButton("Cerrar", on_click=lambda ev: (setattr(dlg, 'open', False), self._page.overlay.remove(dlg) if dlg in self._page.overlay else None, self._page.update())),
                *(
                    [
                        ft.ElevatedButton(
                            "Ir a Productos",
                            icon=ft.icons.INVENTORY_2_OUTLINED,
                            bgcolor=ft.colors.BLUE_700,
                            color=ft.colors.WHITE,
                            on_click=lambda ev: _ir_stock(ev, dlg),
                        )
                    ]
                    if alertas
                    else []
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()