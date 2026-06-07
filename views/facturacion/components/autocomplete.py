"""
components/autocomplete.py
Autocompletado con modal de búsqueda centrado en pantalla.
No deforma el layout — el dropdown es un AlertDialog de Flet.
"""
from __future__ import annotations
import logging
import threading
import time
import flet as ft

log = logging.getLogger("mvp10")


class AutocompleteField:
    _open_dropdowns: list["AutocompleteField"] = []

    def __init__(
        self,
        page: ft.Page,
        search_fn,
        label_fn,
        sublabel_fn=None,
        on_select=None,
        on_submit_next=None,
        t: dict | None = None,
        **tf_kwargs,
    ) -> None:
        self._page = page
        self._search_fn = search_fn
        self._label_fn = label_fn
        self._sublabel_fn = sublabel_fn
        self._on_select = on_select
        self._on_submit_next = on_submit_next
        self._user_on_change = tf_kwargs.pop("on_change", None)
        expand_val = tf_kwargs.pop("expand", False)
        self._dropdown_visible = False
        self._suppress_search = False
        self._current_results = []
        self._modal_open = False
        self._selected_index = -1
        self._modal_dlg = None
        self._prev_kb = None

        border_color = t["border"] if t else ft.colors.OUTLINE
        focused_color = t["accent"] if t else ft.colors.PRIMARY

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
            on_blur=self._on_blur,
            on_focus=self._on_focus,
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

        # Campo de búsqueda dentro del modal
        tf_modal = ft.TextField(
            value=initial_query,
            hint_text="Buscar producto...",
            border_radius=7,
            height=40,
            text_size=13,
            content_padding=ft.padding.symmetric(8, 10),
            border_color=ft.colors.OUTLINE,
            focused_border_color=ft.colors.PRIMARY,
            prefix_icon=ft.icons.SEARCH,
            autofocus=True,
        )

        results_col = ft.Column(
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            height=300,
        )

        usar_texto_btn = ft.Container(visible=False)

        def _build_results(query: str):
            results_col.controls.clear()

            if not query.strip():
                results_col.controls.append(
                    ft.Container(
                        ft.Text(
                            "Escribí para buscar productos...",
                            size=13, color=ft.colors.SECONDARY,
                        ),
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
                results = self._search_fn(query, limit=8)
            except Exception:
                results = []

            self._current_results = results

            if not results:
                results_col.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.icons.SEARCH_OFF, size=32, color=ft.colors.SECONDARY),
                                ft.Text(
                                    f"No se encontró \"{query}\"",
                                    size=13, color=ft.colors.SECONDARY,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        padding=ft.padding.all(24),
                        alignment=ft.alignment.center,
                    )
                )
                usar_texto_btn.visible = True
            else:
                usar_texto_btn.visible = False
                for i, item in enumerate(results):
                    zebra = i % 2 == 0

                    def _make_row(captured_item, idx):
                        is_selected = idx == self._selected_index
                        return ft.Container(
                            key=f"row_{idx}",
                            content=ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text(
                                                self._label_fn(captured_item),
                                                size=13,
                                                weight=ft.FontWeight.W_500,
                                            ),
                                            *(
                                                [ft.Text(
                                                    self._sublabel_fn(captured_item),
                                                    size=11,
                                                    color=ft.colors.SECONDARY,
                                                )]
                                                if self._sublabel_fn else []
                                            ),
                                        ],
                                        spacing=2,
                                        tight=True,
                                        expand=True,
                                    ),
                                    ft.Icon(
                                        ft.icons.CHEVRON_RIGHT,
                                        size=16,
                                        color=ft.colors.SECONDARY,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=ft.padding.symmetric(12, 16),
                            bgcolor=ft.colors.PRIMARY_CONTAINER if is_selected else (
                                ft.colors.SURFACE if idx % 2 == 0 else ft.colors.SURFACE_VARIANT
                            ),
                            border=ft.border.only(
                                bottom=ft.border.BorderSide(0.5, ft.colors.OUTLINE_VARIANT)
                            ),
                            ink=True,
                            on_click=lambda e, it=captured_item: _select(it),
                        )
                    results_col.controls.append(_make_row(item, i))

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
            "Usar este texto igual",
            icon=ft.icons.EDIT_NOTE,
            on_click=_usar_texto_libre,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.SECONDARY_CONTAINER,
                color=ft.colors.ON_SECONDARY_CONTAINER,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        usar_texto_btn.alignment = ft.alignment.center
        usar_texto_btn.padding = ft.padding.symmetric(8, 0)

        tf_modal.on_change = lambda e: _build_results(e.control.value or "")
        def _on_modal_key(e: ft.KeyboardEvent):
            if not self._current_results:
                return
            n = len(self._current_results)
            if e.key == "Arrow Down":
                self._selected_index = min(self._selected_index + 1, n - 1)
            elif e.key == "Arrow Up":
                self._selected_index = max(self._selected_index - 1, 0)
            elif e.key == "Enter" and self._selected_index >= 0:
                _select(self._current_results[self._selected_index])
                return
            else:
                return
            # Reconstruir la lista con el nuevo highlighted
            _build_results(tf_modal.value or "")
        self._prev_kb = self._page.on_keyboard_event
        self._page.on_keyboard_event = _on_modal_key
        tf_modal.on_submit = lambda e: (
            _select(self._current_results[0])
            if self._current_results else _usar_texto_libre(e)
        )

        self._modal_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.icons.INVENTORY_2_OUTLINED, size=18, color=ft.colors.PRIMARY),
                    ft.Text("Buscar producto", size=15, weight=ft.FontWeight.W_500),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        tf_modal,
                        ft.Divider(height=1, color=ft.colors.OUTLINE_VARIANT),
                        results_col,
                        usar_texto_btn,
                    ],
                    spacing=8,
                    tight=True,
                ),
                width=480,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=lambda e: self._close_modal(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Cargar resultados iniciales si hay texto
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

    def _hide_dropdown(self) -> None:
        self._dropdown_visible = False
        if self in AutocompleteField._open_dropdowns:
            AutocompleteField._open_dropdowns.remove(self)

    @classmethod
    def _close_all_others(cls, current: "AutocompleteField") -> None:
        for ac in list(cls._open_dropdowns):
            if ac is not current:
                ac._hide_dropdown()

    def _on_focus(self, e) -> None:
        AutocompleteField._close_all_others(self)

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
        self._hide_dropdown()
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

    def _on_blur(self, e) -> None:
        pass  # El modal maneja su propio cierre