"""
flow_guide.py
Botón de ayuda (?) que abre un diálogo con los pasos del flujo.
"""
import flet as ft
from theme import get_theme


def HelpButton(steps: list[dict], page: ft.Page, on_switch_tab=None):
    """
    steps: list of dicts
        {"text": "Descripción", "action": ("Label", tab_index)}  # action optional
    """
    t = get_theme(page)
    def _open_help(e):
        t = get_theme(page)
        items = []
        for i, step in enumerate(steps):
            row_parts = [
                ft.Container(
                    content=ft.Text(str(i + 1), size=13, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.BLUE_500,
                    width=24, height=24,
                    border_radius=12,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Text(step["text"], size=13, color=t["text_primary"], expand=True),
            ]
            if step.get("action"):
                label, idx = step["action"]
                btn = ft.ElevatedButton(
                    label,
                    on_click=lambda e, i=idx: (_close_dlg(dlg), on_switch_tab(i) if on_switch_tab else None),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE,
                        padding=ft.padding.symmetric(6, 14),
                        shape=ft.RoundedRectangleBorder(radius=6),
                    ),
                )
                row_parts.append(btn)
            items.append(
                ft.Container(
                    content=ft.Row(row_parts, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(6, 0),
                    border=ft.border.only(bottom=ft.border.BorderSide(0.5, t["border_light"])),
                )
            )

        dlg = ft.AlertDialog(
            modal=False,
            bgcolor=t["bg_card"],
            title=ft.Row([
                ft.Icon(ft.Icons.HELP_OUTLINE, size=20, color=t["accent"]),
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
        page.close(dlg)

    return ft.IconButton(
        icon=ft.Icons.HELP_OUTLINE,
        icon_size=20,
        icon_color=t["text_secondary"],
        tooltip="¿Cómo usar?",
        on_click=_open_help,
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )
