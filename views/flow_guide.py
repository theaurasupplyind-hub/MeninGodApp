"""
flow_guide.py
Botón de ayuda (?) que abre un diálogo con los pasos del flujo.
"""
import flet as ft


def HelpButton(steps: list[dict], page: ft.Page, on_switch_tab=None):
    """
    steps: list of dicts
        {"text": "Descripción", "action": ("Label", tab_index)}  # action optional
    """
    def _open_help(e):
        items = []
        for i, step in enumerate(steps):
            row_parts = [
                ft.Container(
                    content=ft.Text(str(i + 1), size=13, weight=ft.FontWeight.W_700, color=ft.colors.WHITE),
                    bgcolor=ft.colors.BLUE_500,
                    width=24, height=24,
                    border_radius=12,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Text(step["text"], size=13, color=ft.colors.GREY_800, expand=True),
            ]
            if step.get("action"):
                label, idx = step["action"]
                btn = ft.ElevatedButton(
                    label,
                    on_click=lambda e, i=idx: (_close_dlg(dlg), on_switch_tab(i) if on_switch_tab else None),
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE,
                        padding=ft.padding.symmetric(6, 14),
                        shape=ft.RoundedRectangleBorder(radius=6),
                    ),
                )
                row_parts.append(btn)
            items.append(
                ft.Container(
                    content=ft.Row(row_parts, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(6, 0),
                    border=ft.border.only(bottom=ft.border.BorderSide(0.5, ft.colors.GREY_100)),
                )
            )

        dlg = ft.AlertDialog(
            modal=False,
            title=ft.Row([
                ft.Icon(ft.icons.HELP_OUTLINE, size=20, color=ft.colors.BLUE_600),
                ft.Text("¿Cómo usar esta pantalla?", size=16, weight=ft.FontWeight.W_600),
            ], spacing=8),
            content=ft.Container(
                content=ft.Column(items, spacing=0, scroll=ft.ScrollMode.AUTO),
                width=420,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda ev: _close_dlg(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _close_dlg(dlg):
        dlg.open = False
        page.update()

    return ft.IconButton(
        icon=ft.icons.HELP_OUTLINE,
        icon_size=20,
        icon_color=ft.colors.GREY_400,
        tooltip="¿Cómo usar?",
        on_click=_open_help,
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )
