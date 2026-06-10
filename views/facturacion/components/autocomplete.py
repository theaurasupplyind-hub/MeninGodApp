"""
components/autocomplete.py
Autocompletado con modal de búsqueda centrado en pantalla.
No deforma el layout — el dropdown es un AlertDialog de Flet.

Soporta dos modos:
  - allow_free_text=False: solo seleccionar resultados existentes
  - allow_free_text=True:  si no hay resultados, permite usar el texto libre
"""
from __future__ import annotations
import logging
import flet as ft

log = logging.getLogger("mvp10")


def _stock_badge(stock: float, t: dict | None = None) -> ft.Container:
    if t:
        bg, fg = t["badge_ok"] if stock > 0 else t["badge_sin_stock"]
    else:
        fg = ft.Colors.GREEN_700 if stock > 0 else ft.Colors.RED_700
        bg = "#E8F5E9" if stock > 0 else "#FFEBEE"
    label = f"{int(stock)}" if stock == int(stock) else f"{stock:.1f}"
    return ft.Container(
        ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=fg),
        bgcolor=bg, border_radius=10,
        padding=ft.padding.symmetric(2, 8),
    )


class AutocompleteField:
    def __init__(
        self,
        page: ft.Page,
        search_fn,
        label_fn,
        sublabel_fn=None,
        on_select=None,
        on_submit_next=None,
        t: dict | None = None,
        allow_free_text: bool = True,
        search_label: str = "producto",
        icon: ft.Icons = ft.Icons.INVENTORY_2_OUTLINED,
        **tf_kwargs,
    ) -> None:
        self._page = page
        self._search_fn = search_fn
        self._label_fn = label_fn
        self._sublabel_fn = sublabel_fn
        self._on_select = on_select
        self._on_submit_next = on_submit_next
        self._user_on_change = tf_kwargs.pop("on_change", None)
        self._allow_free_text = allow_free_text
        self._search_label = search_label
        self._icon = icon
        self._t = t
        expand_val = tf_kwargs.pop("expand", False)
        self._suppress_search = False
        self._current_results = []
        self._modal_open = False
        self._selected_index = -1
        self._modal_dlg = None
        self._prev_kb = None

        border_color = t["border"] if t else ft.Colors.OUTLINE
        focused_color = t["accent"] if t else ft.Colors.PRIMARY

        self.field = ft.TextField(
            border_radius=7,
            height=38,
            text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            border_color=border_color,
            focused_border_color=focused_color,
            bgcolor=t["bg_input"] if t else None,
            color=t["text_primary"] if t else None,
            hint_style=ft.TextStyle(color=t["text_hint"]) if t else None,
            on_change=self._on_change,
            on_submit=self._on_submit,
            **tf_kwargs,
        )

        self.control = ft.Column(
            [self.field],
            spacing=0,
            expand=expand_val,
            tight=True,
        )

    # ── Propiedades ────────────────────────────────────────────────────────────

    @property
    def value(self) -> str:
        return self.field.value or ""

    @value.setter
    def value(self, v: str) -> None:
        self.field.value = v

    def focus(self) -> None:
        self.field.focus()

    # ── Modal ──────────────────────────────────────────────────────────────────
    
    def _open_modal(self, initial_query: str = "") -> None:
        if self._modal_open:
            return
        self._modal_open = True
        self._selected_index = -1

        tf_modal = ft.TextField(
            value=initial_query,
            hint_text=f"Buscar {self._search_label}...",
            border_radius=7, height=40, text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            border_color=ft.Colors.OUTLINE,
            focused_border_color=ft.Colors.PRIMARY,
            prefix_icon=ft.Icons.SEARCH,
            autofocus=True,
        )

        results_col = ft.Column(
            spacing=0, scroll=ft.ScrollMode.AUTO, height=300,
        )

        usar_texto_btn = ft.Container(visible=False)

        def _build_results(query: str):
            results_col.controls.clear()

            if not query.strip():
                results_col.controls.append(
                    ft.Container(
                        ft.Text(f"Escribí para buscar {self._search_label}...",
                                size=13, color=ft.Colors.SECONDARY),
                        padding=ft.padding.all(20),
                        alignment=ft.alignment.center,
                    )
                )
                usar_texto_btn.visible = False
                if results_col.page:
                    results_col.update()
                    usar_texto_btn.update()
                return

            try:
                results = self._search_fn(query, limit=10)
            except Exception:
                results = []

            self._current_results = results

            if not results:
                results_col.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.SEARCH_OFF, size=32, color=ft.Colors.SECONDARY),
                                ft.Text(f'No se encontró "{query}"',
                                        size=13, color=ft.Colors.SECONDARY),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        padding=ft.padding.all(24),
                        alignment=ft.alignment.center,
                    )
                )
                usar_texto_btn.visible = self._allow_free_text
            else:
                usar_texto_btn.visible = False
                for i, item in enumerate(results):
                    is_selected = i == self._selected_index
                    label = self._label_fn(item)
                    sub = self._sublabel_fn(item) if self._sublabel_fn else ""
                    stock = float(item.get("stock_actual", 0) or 0)
                    row = ft.Container(
                        key=f"row_{i}",
                        content=ft.Row([
                            ft.Column([
                                ft.Text(label, size=13, weight=ft.FontWeight.W_500),
                                ft.Text(sub, size=11, color=ft.Colors.SECONDARY),
                            ], spacing=2, tight=True, expand=True),
                            _stock_badge(stock, self._t),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=ft.Colors.SECONDARY),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.symmetric(12, 16),
                        bgcolor=ft.Colors.PRIMARY_CONTAINER if is_selected else (
                            ft.Colors.SURFACE if i % 2 == 0 else ft.Colors.SURFACE_CONTAINER_HIGHEST
                        ),
                        border=ft.border.only(bottom=ft.border.BorderSide(0.5, ft.Colors.OUTLINE_VARIANT)),
                        ink=True,
                        on_click=lambda e, it=item: _select(it),
                    )
                    results_col.controls.append(row)

            if results_col.page:
                results_col.update()
            if usar_texto_btn.page:
                usar_texto_btn.update()

        def _select(item: dict):
            self._close_modal()
            self._suppress_search = True
            self.field.value = self._label_fn(item)
            if self.field.page:
                try:
                    self.field.update()
                except Exception:
                    pass
            if self._on_select:
                self._on_select(item)
            self._suppress_search = False
            if self._on_submit_next:
                self._on_submit_next()

        def _usar_texto_libre(e):
            texto = tf_modal.value.strip()
            if not texto:
                return
            self._close_modal()
            self._suppress_search = True
            self.field.value = texto
            if self.field.page:
                try:
                    self.field.update()
                except Exception:
                    pass
            if self._user_on_change:
                class _FakeEvent:
                    pass
                self._user_on_change(_FakeEvent())
            self._suppress_search = False
            if self._on_submit_next:
                self._on_submit_next()

        usar_texto_btn.content = ft.ElevatedButton(
            f"Usar este texto igual",
            icon=ft.Icons.EDIT_NOTE,
            on_click=_usar_texto_libre,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.SECONDARY_CONTAINER,
                color=ft.Colors.ON_SECONDARY_CONTAINER,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        usar_texto_btn.alignment = ft.alignment.center
        usar_texto_btn.padding = ft.padding.symmetric(8, 0)

        tf_modal.on_change = lambda e: _build_results(e.control.value or "")

        def _on_modal_key(e: ft.KeyboardEvent):
            if e.key == "Arrow Down":
                n = len(self._current_results)
                if n == 0:
                    return
                self._selected_index = min(self._selected_index + 1, n - 1)
                _build_results(tf_modal.value or "")
            elif e.key == "Arrow Up":
                n = len(self._current_results)
                if n == 0:
                    return
                self._selected_index = max(self._selected_index - 1, 0)
                _build_results(tf_modal.value or "")
            elif e.key == "Enter":
                if self._current_results:
                    idx = self._selected_index if self._selected_index >= 0 else 0
                    if idx < len(self._current_results):
                        _select(self._current_results[idx])
                elif self._allow_free_text and (tf_modal.value or "").strip():
                    _usar_texto_libre(e)

        self._prev_kb = self._page.on_keyboard_event
        self._page.on_keyboard_event = _on_modal_key

        cap = self._search_label.capitalize()
        self._modal_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=self._t["bg_card"] if self._t else None,
            title=ft.Row([
                ft.Icon(self._icon, size=18, color=ft.Colors.PRIMARY),
                ft.Text(f"Buscar {self._search_label}", size=15, weight=ft.FontWeight.W_500),
            ], spacing=8),
            content=ft.Container(
                content=ft.Column([
                    tf_modal,
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    results_col,
                    usar_texto_btn,
                ], spacing=8, tight=True),
                width=480,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close_modal()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        _build_results(initial_query)
        self._page.open(self._modal_dlg)

    def _close_modal(self):
        if self._modal_dlg:
            try:
                self._page.close(self._modal_dlg)
            except Exception:
                pass
        self._modal_dlg = None
        self._modal_open = False
        self._page.on_keyboard_event = self._prev_kb

    # ── Handlers ───────────────────────────────────────────────────────────────

    def _on_change(self, e) -> None:
        if self._suppress_search:
            return
        query = (self.field.value or "").strip()

        if self._user_on_change:
            try:
                self._user_on_change(e)
            except Exception as exc:
                log.error(f"User on_change error: {exc}", exc_info=True)

        if len(query) >= 1 and not self._modal_open:
            self._open_modal(query)

    def _on_submit(self, e) -> None:
        if self._current_results:
            self._select_item(self._current_results[0])
        elif self._on_submit_next:
            self._on_submit_next()

    def _select_item(self, item: dict):
        self._suppress_search = True
        self.field.value = self._label_fn(item)
        if self.field.page:
            try:
                self.field.update()
            except Exception:
                pass
        if self._on_select:
            self._on_select(item)
        self._suppress_search = False
        if self._on_submit_next:
            self._on_submit_next()