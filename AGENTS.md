# AGENTS.md — MeninGod (Gestion M.I.G.)

## Run

```bash
python main.py
```

Windows desktop app. Flet 0.28.3, SQLite, Python 3.13+. No web server.

## Build

```bash
pyinstaller build.spec
```

Output: `dist/MVP_1.0/`. Note: `build.spec` still references old Flet 0.23.2 paths (`flet_core`, `flet_runtime`) — needs updating for 0.28.3 (`flet.core`).

## Architecture

```
main.py              → Entry point, window bar, NavigationRail, tab routing
theme.py             → get_theme(page) dict, accent_button(), base_input(), base_card()
db/database.py       → SQLite init, CRUD (facturas, clientes, productos, variantes)
services/            → autocomplete_service, invoice_share, whatsapp_service
views/
  facturacion/       → MVC: view.py, controller.py, state.py, components/
  productos/         → stock.py, compras.py, proveedores.py, nuevo_producto.py
  dashboard.py       → Main dashboard with invoice list
  clientes.py        → Client management
  cuenta_wasi.py     → WASI account view
  stock_alert.py     → Low stock bell notification
```

## Critical Business Rules

- **Products are ONLY created from "Nuevo producto" in Productos.** Never from facturacion or compras.
- **Facturacion items**: can be products (linked to `variante_id`) or free-text notes (`is_note=True` when `producto_id is None`).
- **Compras**: product/color/talle searched only (`allow_free_text=False`). Providers searchable with free text.
- **Stock is deducted per `variante_id`**, not by text matching.
- **1 variant = single product** (no chevron, name shows "Detalle Color Talle X"). **2+ variants = chevron expandable**.

## Flet 0.28.3 Gotchas

- `ft.icons` → `ft.Icons`, `ft.colors` → `ft.Colors` (capitalized enums)
- `page.window_width` → `page.window.width`, `page.overlay.append()` → `page.open()/close()`
- `Dropdown` does NOT accept `height` param (removed in 0.28.3)
- `SURFACE_VARIANT` → use `SURFACE_CONTAINER_HIGHEST`
- `ft.app(main, assets_dir="assets")` still works (sync version)
- `page.on_keyboard_event` gets replaced when modal opens — save/restore `_prev_kb`

## AutocompleteField

Component: `views/facturacion/components/autocomplete.py`

Key params: `allow_free_text`, `search_label`, `icon`. Controls whether users can type free text or must select from search results.

## Theme

Use `t = get_theme(page)` everywhere. Key keys: `bg_page`, `bg_card`, `bg_titlebar`, `accent` (#C9A84C gold), `text_primary`, `text_secondary`. Badge keys return `(bg, fg)` tuples.

**Theme toggle**: Icon button in sidebar (between bell and user). Calls `_toggle_theme()` in `main.py` which:
- Switches `page.theme_mode` between `DARK`/`LIGHT`
- Rebuilds sidebar, title bar, and overlay with new colors
- Clears cached views (`_views.clear()`) and re-switches to current tab
- Uses `sidebar_ref`, `rail_ref`, `title_bar_ref`, `toggle_theme_btn`, `divider_ref` dicts for mutable references

## DB

Location: `%APPDATA%/MVP 1.0/mvp10.db`. Migrations use `PRAGMA table_info` check before `ALTER TABLE` — safe for repeated runs.

## Context File

`contexto.md` contains Flet 0.23.2 syntax reference — partially outdated after migration. Use as pattern reference but verify against 0.28.3 API.
