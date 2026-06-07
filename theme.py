"""
theme_ropa.py
Paleta Dorado + Azul Oscuro para la app de ropa.
Uso: from theme_ropa import get_theme
     t = get_theme(page)
     container = ft.Container(bgcolor=t["bg_card"])
"""
import flet as ft


def get_theme(page: ft.Page) -> dict:
    dark = page.theme_mode == ft.ThemeMode.DARK

    common = {
        "sidebar_width": 148,
        "title_size": 26,
        "title_weight": ft.FontWeight.W_700,
        "subtitle_size": 11,
        "subtitle_weight": ft.FontWeight.W_600,
        "logo_size": 96,
    }

    if dark:
        dark_theme = {
            "bg_page":          "#0A0F1C",
            "bg_card":          "#111827",
            "bg_row_even":      "#111827",
            "bg_row_odd":       "#0D1520",
            "bg_header":        "#0A0F1C",
            "bg_input":         "#1E293B",
            "bg_selected":      "#1E2A3D",
            "border":           "#2A3A50",
            "border_light":     "#1E2A3D",
            "text_primary":     "#F5F0E8",
            "text_secondary":   "#8A9BB0",
            "text_hint":        "#5A7080",
            "accent":           "#C9A84C",
            "accent_light":     "#E8C97A",
            "accent_dark":      "#9C7A28",
            "accent_text":      "#0D1B2A",
            "badge_pendiente":  ("#3A2800", "#C9A84C"),
            "badge_entregado":  ("#0D2040", "#64B5F6"),
            "badge_pagado":     ("#0A2A1A", "#4CAF50"),
            "badge_cancelado":  ("#252525", "#777777"),
            "badge_en_proceso": ("#1A2A40", "#90CAF9"),
            "badge_sin_stock":  ("#3A0D0D", "#EF9A9A"),
            "badge_bajo":       ("#3A2800", "#C9A84C"),
            "badge_ok":         ("#0A2A1A", "#4CAF50"),
            "badge_compra":     ("#3A0D0D", "#EF9A9A"),
            "badge_pago":       ("#0A2A1A", "#4CAF50"),
            "badge_ajuste":     ("#252525", "#777777"),
        }
        return {**dark_theme, **common}
    else:
        light_theme = {
            "bg_page":          "#FDFAF4",
            "bg_card":          "#FFFFFF",
            "bg_row_even":      "#FFFFFF",
            "bg_row_odd":       "#FAF7F0",
            "bg_header":        "#F5F0E8",
            "bg_input":         "#FFFFFF",
            "bg_selected":      "#FFF8E8",
            "border":           "#DDD5C0",
            "border_light":     "#EDE8DC",
            "text_primary":     "#1A1A2A",
            "text_secondary":   "#6B6050",
            "text_hint":        "#A09080",
            "accent":           "#9C7A28",
            "accent_light":     "#C9A84C",
            "accent_dark":      "#7A5E1A",
            "accent_text":      "#FFFFFF",
            "badge_pendiente":  ("#FFF3D0", "#8A6200"),
            "badge_entregado":  ("#E3F0FF", "#1565C0"),
            "badge_pagado":     ("#E8F5E9", "#2E7D32"),
            "badge_cancelado":  ("#F3F4F6", "#374151"),
            "badge_en_proceso": ("#E8F0FE", "#1A56DB"),
            "badge_sin_stock":  ("#FEECEC", "#B91C1C"),
            "badge_bajo":       ("#FFF3D0", "#8A6200"),
            "badge_ok":         ("#E8F5E9", "#2E7D32"),
            "badge_compra":     ("#FEECEC", "#B91C1C"),
            "badge_pago":       ("#E8F5E9", "#2E7D32"),
            "badge_ajuste":     ("#F3F4F6", "#374151"),
        }
        return {**light_theme, **common}


# ── Helpers de uso frecuente ──────────────────────────────────────────────────

def accent_button(text: str, on_click=None, expand=False) -> ft.ElevatedButton:
    """Botón primario con color dorado."""
    return ft.ElevatedButton(
        text=text,
        bgcolor="#C9A84C",
        color="#0D1B2A",
        on_click=on_click,
        expand=expand,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            overlay_color=ft.colors.with_opacity(0.15, "#FFFFFF"),
        ),
    )


def base_input(hint: str, expand=True, height=38, on_change=None) -> ft.TextField:
    """Input con estilo del tema oscuro."""
    return ft.TextField(
        hint_text=hint,
        border_radius=7,
        height=height,
        text_size=13,
        content_padding=ft.padding.symmetric(8, 10),
        expand=expand,
        bgcolor="#243447",
        border_color="#2E4057",
        focused_border_color="#C9A84C",
        color="#F0E9D6",
        hint_style=ft.TextStyle(color="#5A7080"),
        on_change=on_change,
    )


def base_card(content, padding=16, radius=10) -> ft.Container:
    """Container con estilo card del tema."""
    return ft.Container(
        content=content,
        border_radius=radius,
        padding=padding,
        bgcolor="#1B2B3A",
        border=ft.border.all(1, "#2E4057"),
    )


def page_title(text: str, t: dict) -> ft.Text:
    """Título de sección estilo imagen — grande y bold."""
    return ft.Text(
        text.upper(),
        size=t.get("title_size", 26),
        weight=t.get("title_weight", ft.FontWeight.W_700),
        color=t["text_primary"],
        style=ft.TextStyle(letter_spacing=1.5),
    )


def section_label(text: str, t: dict) -> ft.Text:
    """Etiqueta secundaria pequeña en mayúsculas."""
    return ft.Text(
        text.upper(),
        size=10,
        weight=ft.FontWeight.W_600,
        color=t["text_secondary"],
        style=ft.TextStyle(letter_spacing=1.2),
    )
