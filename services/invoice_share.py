# FILE: services/invoice_share.py
import os
import string
import subprocess
from pathlib import Path

from PIL import Image

EDGE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
GENERATED_DIR = Path(os.getenv("APPDATA")) / "MVP 1.0" / "generated"

TEMPLATE_PATH = Path(__file__).parent / "invoice_template.html"


def _escape_html(value: str) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def _build_items_html(items: list[dict]) -> str:
    rows = []
    for item in items:
        detalle = _escape_html(item.get("detalle", ""))
        cantidad = item.get("cantidad", 0)
        precio = item.get("precio_unitario", 0)
        total = item.get("total", 0)
        rows.append(
            f"""
            <div class="item">
              <div class="item-top">
                <div>
                  <div class="item-title">{detalle}</div>
                  <div class="item-qty">Cantidad: {cantidad:g}</div>
                </div>
                <div class="item-total">{f"${total:,.0f}".replace(",", ".")}</div>
              </div>
              <div class="item-unit">Precio unitario: {f"${precio:,.0f}".replace(",", ".")}</div>
            </div>
            """
        )
    return "\n".join(rows)

def _get_brand_html() -> str:
    return '<div style="font-size:32px;font-weight:800;color:#1565C0;">TEST</div>'

def render_invoice_image(data: dict, items: list[dict], output_name: str) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    html_path = GENERATED_DIR / f"{output_name}.html"
    image_path = GENERATED_DIR / f"{output_name}.png"

    total = data.get("total", 0) or 0
    seña = data.get("seña", 0) or 0
    displayed = max(0, total - seña)
    formatted_total = f"${displayed:,.0f}".replace(",", ".")
    items_html = _build_items_html(items)

    if seña > 0:
        sub_fmt = f"${total:,.0f}".replace(",", ".")
        seña_fmt = f"${seña:,.0f}".replace(",", ".")
        seña_deduction = f'<div style="font-size:13px;color:#888;margin-top:6px;">Subtotal: {sub_fmt} &nbsp;|&nbsp; Seña: -{seña_fmt}</div>'
    else:
        seña_deduction = ""
    
    # Leemos el archivo HTML
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"No se encontró la plantilla HTML en {TEMPLATE_PATH}")
        
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_str = f.read()

    # Usamos string.Template para reemplazar las variables $variable
    template = string.Template(template_str)
    
    html = template.safe_substitute(
        brand_html=_get_brand_html(),
        numero=_escape_html(data.get("numero", "")),
        fecha=_escape_html(data.get("fecha", "")),
        cliente_nombre=_escape_html(data.get("cliente", "")) or "-",
        cliente_telefono=_escape_html(data.get("telefono", "")) or "-",
        cliente_domicilio=_escape_html(data.get("domicilio", "")) or "-",
        cliente_transporte=_escape_html(data.get("empresa_envio", "")) or "-",
        items_html=items_html or '<div class="item"><div class="item-title">Sin items cargados.</div></div>',
        formatted_total=formatted_total,
        seña_deduction=seña_deduction,
    )

    html_path.write_text(html, encoding="utf-8")
    _render_html_to_png(html_path, image_path)
    return image_path


def _render_html_to_png(html_path: Path, image_path: Path):
    """Renderiza el HTML a PNG usando Edge headless y recorta el alto real con Pillow."""
    if not EDGE_PATH.exists():
        raise FileNotFoundError("No se encontró Microsoft Edge para renderizar la imagen.")

    # Ancho fijo = ancho de la tarjeta. Alto generoso para que quepa cualquier cantidad de items.
    CARD_WIDTH = 460
    RENDER_HEIGHT = 2400

    subprocess.run(
        [
            str(EDGE_PATH),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={CARD_WIDTH},{RENDER_HEIGHT}",
            f"--screenshot={image_path}",
            html_path.resolve().as_uri(),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Recortar el espacio vacío inferior con Pillow
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        pixels = img.load()
        last_content_row = 0
        for y in range(img.height - 1, -1, -1):
            row_colors = {pixels[x, y] for x in range(0, img.width, 4)}
            # Si la fila no es blanco puro, es contenido
            if row_colors != {(255, 255, 255)}:
                last_content_row = y
                break
        cropped = img.crop((0, 0, img.width, last_content_row + 16))  # +16px de padding inferior
        cropped.save(image_path, "PNG")