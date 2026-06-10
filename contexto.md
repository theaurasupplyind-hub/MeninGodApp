# contexto.md — App Ropa Cliente

> Stack: Flet 0.28.3 · Python 3.13 · SQLite
> Propósito: Referencia de sintaxis y patrones válidos para Flet 0.28.3.

---

## 1. Contenedores y Layout

### 1.1 Card base
```python
ft.Container(
    content=...,
    border_radius=10,
    padding=16,
    bgcolor="#1B2B3A",
    border=ft.border.all(1, "#2E4057"),
)
```
*Fuente: `theme.py:122-130` (función `base_card()`)*

### 1.2 Separador invisible
```python
ft.Container(height=4)
```

### 1.3 Row / Column
```python
ft.Row([...], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
ft.Column([...], spacing=12, expand=True)
```
- `Row` + `expand=True` en controles hijos para que ocupen espacio disponible.
- `vertical_alignment=ft.CrossAxisAlignment.CENTER` para centrar verticalmente.

### 1.4 Divider
```python
ft.Divider(height=1, color=ft.Colors.GREY_200)
ft.Divider(height=0.5, thickness=0.5)
```

---

## 2. Inputs y Formularios

### 2.1 TextField base
```python
ft.TextField(
    hint_text="Etiqueta",
    border_radius=7,
    height=38,
    text_size=13,
    content_padding=ft.padding.symmetric(8, 10),
    expand=True,
    border_color="#2E4057",
    focused_border_color="#C9A84C",
    bgcolor="#243447",
    color="#F0E9D6",
    hint_style=ft.TextStyle(color="#5A7080"),
    on_change=on_change,
)
```
*Fuente: `theme.py:104-119` (función `base_input()`)*

### 2.2 Dropdown
```python
ft.Dropdown(
    options=[
        ft.dropdown.Option("Efectivo"),
        ft.dropdown.Option("Transferencia"),
    ],
    value="Efectivo",
    border_radius=7,
    text_size=13,
    content_padding=ft.padding.symmetric(4, 10),
    width=160,
)
```
⚠️ En 0.28.3 el param `height` fue eliminado de `Dropdown`.

### 2.3 KeyboardType.NUMBER
```python
keyboard_type=ft.KeyboardType.NUMBER
```

### 2.4 AutocompleteField
Componente custom en `views/facturacion/components/autocomplete.py`. Uso:
```python
from views.facturacion.components.autocomplete import AutocompleteField

ac = AutocompleteField(
    page=page,
    search_fn=search_clientes,
    label_fn=lambda c: c.get("nombre", ""),
    sublabel_fn=lambda c: c.get("telefono", "") or "",
    hint_text="Nombre del cliente",
    expand=True,
    allow_free_text=True,   # True = permite texto libre, False = solo selección
    search_label="cliente",
    icon=ft.Icons.PEOPLE_OUTLINED,
    on_submit_next=lambda: siguiente_control.focus(),
)
```

---

## 3. Botones

### 3.1 ElevatedButton primario
```python
ft.ElevatedButton(
    text="Guardar",
    bgcolor="#C9A84C",
    color="#0D1B2A",
    on_click=handler,
    style=ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=8),
        overlay_color=ft.Colors.with_opacity(0.15, "#FFFFFF"),
    ),
)
```
*Fuente: `theme.py:89-101` (función `accent_button()`)*

### 3.2 ElevatedButton con icono
```python
ft.ElevatedButton(
    "Nuevo producto",
    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
    on_click=_open_dialog,
    style=ft.ButtonStyle(
        bgcolor=ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.padding.symmetric(10, 18),
    ),
)
```

### 3.3 OutlinedButton
```python
ft.OutlinedButton(
    "Ver PDF",
    icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
    on_click=handler,
    style=ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.padding.symmetric(10, 14),
        color=ft.Colors.GREY_700,
    ),
)
```

### 3.4 OutlinedButton con borde
```python
ft.OutlinedButton(
    "Compartir WhatsApp",
    icon=ft.Icons.SHARE_OUTLINED,
    width=210,
    on_click=handler,
    style=ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.padding.symmetric(10, 14),
        color=ft.Colors.GREEN_700,
        side=ft.BorderSide(1, ft.Colors.GREEN_200),
    ),
)
```

### 3.5 TextButton (cancelar)
```python
ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg))
```

### 3.6 IconButton
```python
ft.IconButton(
    ft.Icons.EDIT_OUTLINED,
    icon_size=16,
    tooltip="Editar",
    icon_color=ft.Colors.BLUE_600,
    on_click=lambda e: handler(),
    style=ft.ButtonStyle(padding=ft.padding.all(4)),
)
```

---

## 4. Tablas y Listas

### 4.1 DataTable
```python
ft.DataTable(
    columns=[
        ft.DataColumn(ft.Text("N° Factura", size=12, weight=ft.FontWeight.W_500)),
        ft.DataColumn(ft.Text("Total", size=12), numeric=True),
    ],
    rows=[
        ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(factura["numero"], size=13)),
                ft.DataCell(ft.Text(_fmt(factura["total"]), size=13)),
            ]
        )
    ],
    border=ft.border.all(0.5, ft.Colors.GREY_300),
    border_radius=8,
    horizontal_lines=ft.border.BorderSide(0.5, ft.Colors.GREY_200),
    column_spacing=20,
    data_row_max_height=44,
)
```

### 4.2 ListView (reemplaza Column para scroll)
```python
ft.ListView(spacing=4, expand=True, auto_scroll=False)
```
Usar `ListView` en lugar de `Column` cuando el contenido puede ser largo y necesita scroll nativo.

### 4.3 Filas zebra
```python
bgcolor="#111827" if zebra else "#0D1520"
# donde zebra = (i % 2 == 0)
```

### 4.4 Badge de estado clickable
```python
ESTADO_CICLO = ["Pendiente", "Entregado", "Pagado"]

def _get_estado_colors(estado, t):
    return {
        "Pendiente": t["badge_pendiente"],
        "Entregado": t["badge_entregado"],
        "Pagado":    t["badge_pagado"],
    }.get(estado, t["badge_cancelado"])

bg, fg = _get_estado_colors(estado, t)
badge = ft.Container(
    content=ft.Row(
        [ft.Text(estado, size=11, color=fg, weight=ft.FontWeight.W_500),
         ft.Icon(ft.Icons.UNFOLD_MORE, size=12, color=fg)],
        spacing=2, tight=True,
    ),
    bgcolor=bg,
    border_radius=20,
    padding=ft.padding.symmetric(3, 8),
    ink=True,
    on_click=on_click_handler,
)
```

---

## 5. Diálogos y Notificaciones

### 5.1 AlertDialog modal
```python
dlg = ft.AlertDialog(
    modal=True,
    title=ft.Text("Nuevo producto", size=16, weight=ft.FontWeight.W_500),
    content=ft.Container(
        content=ft.Column([...], spacing=8, tight=True),
        width=420,
    ),
    actions=[
        ft.TextButton("Cancelar", on_click=lambda ev: page.close(dlg)),
        ft.ElevatedButton("Guardar", bgcolor=..., color=..., on_click=...),
    ],
    actions_alignment=ft.MainAxisAlignment.END,
)
page.open(dlg)
```

### 5.2 SnackBar
```python
def _show_message(text: str, color=ft.Colors.BLUE_700):
    sb = ft.SnackBar(
        ft.Text(text, color=ft.Colors.WHITE),
        bgcolor=color,
        duration=3200,
    )
    page.open(sb)
```

---

## 6. Theme y Estilos

### 6.1 get_theme() dict (theme.py)
```python
from theme import get_theme

def build_view(page):
    t = get_theme(page)
    # Usar t["bg_page"], t["bg_card"], t["accent"], etc.
```
*Fuente: `theme.py` — modo oscuro + claro.*

### 6.2 Helpers de theme.py
```python
from theme import accent_button, base_input, base_card

btn = accent_button("Guardar", on_click=handler, expand=False)
inp = base_input("Nombre", expand=True, height=38, on_change=fn)
card = base_card(content, padding=16, radius=10)
```

### 6.3 Badges de estado como tuplas (bg, fg)
```python
t["badge_pendiente"]  = ("#3A2800", "#C9A84C")
t["badge_entregado"]  = ("#0D2040", "#64B5F6")
t["badge_pagado"]     = ("#0A2A1A", "#4CAF50")
t["badge_cancelado"]  = ("#252525", "#777777")
t["badge_en_proceso"] = ("#1A2A40", "#90CAF9")

t["badge_sin_stock"]  = ("#3A0D0D", "#EF9A9A")
t["badge_bajo"]       = ("#3A2800", "#C9A84C")
t["badge_ok"]         = ("#0A2A1A", "#4CAF50")

t["badge_compra"]     = ("#3A0D0D", "#EF9A9A")
t["badge_pago"]       = ("#0A2A1A", "#4CAF50")
t["badge_ajuste"]     = ("#252525", "#777777")
```

---

## 7. Eventos y Navegación

### 7.1 Keyboard handler (F1, F2)
```python
_prev_kb = page.on_keyboard_event

def _on_keyboard(e: ft.KeyboardEvent):
    if e.key == "F1":
        ctrl.save()
    elif e.key == "F2":
        ctrl.nueva()
    elif _prev_kb:
        _prev_kb(e)

page.on_keyboard_event = _on_keyboard

# Dispose:
view.dispose = lambda: setattr(page, "on_keyboard_event", _prev_kb)
```
⚠️ En 0.28.3, abrir un modal reemplaza `page.on_keyboard_event` — guardá y restaurá el handler previo.

### 7.2 Callbacks comunes
```python
on_click=lambda e: handler()
on_change=lambda e: (actualizar_valor(e.control.value), refrescar())
on_submit=lambda e: siguiente_control.focus()
```

### 7.3 page.update() vs control.update()
- `page.update()` — actualiza toda la página (más lento, usar con moderación).
- `control.update()` — actualiza solo el control (más eficiente).
- Usar `_safe_update(control)` para evitar errores si el control no está montado:
```python
def _safe_update(control):
    if getattr(control, "page", None):
        try: control.update()
        except Exception: pass
```

### 7.4 NavigationRail
```python
TABS = [
    ("Dashboard",   ft.Icons.DASHBOARD_OUTLINED,       ft.Icons.DASHBOARD),
    ("Facturacion", ft.Icons.RECEIPT_LONG_OUTLINED,    ft.Icons.RECEIPT_LONG),
    ("Clientes",    ft.Icons.PEOPLE_OUTLINED,          ft.Icons.PEOPLE),
    ("Productos",   ft.Icons.INVENTORY_2_OUTLINED,     ft.Icons.INVENTORY_2),
    ("Cuenta",      ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, ft.Icons.ACCOUNT_BALANCE_WALLET),
]

rail = ft.NavigationRail(
    selected_index=0,
    label_type=ft.NavigationRailLabelType.ALL,
    min_width=148,
    bgcolor="#111827",
    indicator_color="#C9A84C",
    destinations=[
        ft.NavigationRailDestination(
            icon=icon_out, selected_icon=icon_sel, label=label
        ) for label, icon_out, icon_sel in TABS
    ],
    on_change=lambda e: _switch(e.control.selected_index),
)
```
*Fuente: `main.py:31-227`*

---

## 8. Helpers y Parsers

### 8.1 Formateo de moneda ($1.234)
```python
def fmt(val) -> str:
    try:
        cleaned = str(val).replace(".", "").replace(",", ".") or "0"
        return ("$" + f"{int(float(cleaned)):,}").replace(",", ".")
    except Exception:
        return "$0"
```
*Fuente: `facturacion/controller.py:51-57`*

### 8.2 Parseo de números ("1.234" → 1234.0)
```python
def parse_num(raw: str) -> float:
    try:
        return float(str(raw).replace(".", "").replace(",", ".").strip() or 0)
    except Exception:
        return 0.0
```
*Fuente: `facturacion/controller.py:60-65`*

### 8.3 Formateo de stock (entero sin decimales)
```python
def _fmt_stock(val) -> str:
    try:
        v = float(val)
        return str(int(v)) if v == int(v) else f"{v:.1f}"
    except Exception:
        return "0"
```

### 8.4 ALTER TABLE seguro
```python
def _col_exists(c, table: str, col: str) -> bool:
    cols = {row[1] for row in c.execute(f"PRAGMA table_info({table})")}
    return col in cols

if not _col_exists(c, "facturas", "seña"):
    c.execute("ALTER TABLE facturas ADD COLUMN seña REAL DEFAULT 0")
```

### 8.5 Window properties (0.28.3)
```python
page.window.title_bar_hidden = True
page.window.title_bar_buttons_hidden = True
page.window.width = 1280
page.window.height = 740
page.window.min_width = 980
page.window.min_height = 620
page.window.minimized = True
page.window.maximized = not page.window.maximized
page.window.close()
```

### 8.6 Overlay / dialogs (0.28.3)
```python
page.open(dlg)    # reemplaza page.overlay.append(dlg) + dlg.update()
page.close(dlg)   # reemplaza page.overlay.remove(dlg)
page.open(sb)     # SnackBar también usa page.open()
```

---

## Restricciones de Flet 0.28.3

- `ft.icons` → `ft.Icons` (capitalizado). `ft.colors` → `ft.Colors`.
- `page.window_width` → `page.window.width` (propiedades anidadas).
- `page.overlay.append(dlg)` → `page.open(dlg)`. `page.overlay.remove(dlg)` → `page.close(dlg)`.
- `Dropdown` NO acepta `height` (eliminado en 0.28.3).
- `SURFACE_VARIANT` → `SURFACE_CONTAINER_HIGHEST`.
- `ft.app(main, assets_dir="assets")` funciona (versión sync).
- `page.on_keyboard_event` se reemplaza al abrir modal — guardá/restaurá el handler.
- `page.add()` NO acepta listas → usar `*lista` o agregar uno por uno.
- `on_click` siempre recibe `(e)` como parámetro.
- `bgcolor` acepta string hex `"#RRGGBB"` o `ft.Colors.X`.
- `ft.TextField`: usar `content_padding=ft.padding.symmetric(v, h)`.
- `ft.Dropdown`: `options` son `ft.dropdown.Option(key, text)`.
- Para scroll en Column, usar `ft.ListView` en su lugar.
