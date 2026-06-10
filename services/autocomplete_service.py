"""
autocomplete_service.py
Búsqueda fuzzy para autocompletado de clientes, productos y proveedores.
"""
from db.database import get_clientes, get_productos, get_productos_proveedor, get_proveedores, get_variantes_proveedor, get_variantes_con_producto, get_colores, get_tallas, get_colores_by_producto, get_talles_by_producto_color


def search_clientes(query: str, limit: int = 6) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    results = []
    for c in get_clientes():
        haystack = " ".join([
            c.get("nombre", ""),
            c.get("telefono", ""),
        ]).lower()
        if q in haystack:
            results.append(c)
        if len(results) >= limit:
            break
    return results


def search_productos(query: str, limit: int = 10) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    tokens = [t for t in q.split() if t]

    all_variants = get_variantes_con_producto()

    scored = []
    seen_ids = set()
    for v in all_variants:
        detalle = (v.get("producto_detalle") or "").lower()
        color = (v.get("color") or "").lower()
        talla = (v.get("talla") or "").lower()
        full_label = f"{detalle} {color} {talla}"

        score = 0
        all_matched = True
        for token in tokens:
            matched = False
            if token in detalle:
                score += 10
                matched = True
            if token in color:
                score += 8
                matched = True
            if token in talla:
                score += 6
                matched = True
            if not matched:
                all_matched = False

        if score == 0:
            continue

        if all_matched:
            score += 20

        vid = v["variante_id"]
        if vid in seen_ids:
            continue
        seen_ids.add(vid)

        stock = float(v.get("stock_actual", 0) or 0)
        if stock > 0:
            score += 5

        scored.append({
            "score": score,
            "is_variant": True,
            "id": v["producto_id"],
            "detalle": v["producto_detalle"],
            "variante_id": vid,
            "color_id": v.get("color_id"),
            "talla_id": v.get("talla_id"),
            "color": color or "",
            "talla": talla or "",
            "precio_unitario": v.get("precio_unitario", 0),
            "precio_compra": v.get("precio_compra", 0),
            "stock_actual": stock,
        })

    scored.sort(key=lambda x: (-x["score"], x["detalle"], x["color"], x["talla"]))
    return scored[:limit]


def search_proveedores(query: str, limit: int = 6) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    results = []
    for p in get_proveedores():
        haystack = " ".join([
            p.get("nombre", ""),
            p.get("telefono", ""),
        ]).lower()
        if q in haystack:
            results.append(p)
        if len(results) >= limit:
            break
    return results


def search_productos_proveedor(query: str, limit: int = 8) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    results = []
    for p in get_productos_proveedor():
        if q in (p.get("detalle", "") or "").lower():
            results.append({"is_variant": False, **p})
        if len(results) >= limit:
            break
    return results


def search_colores(query: str, producto_id: int = None, limit: int = 8) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    results = []
    colores = get_colores_by_producto(producto_id) if producto_id else get_colores()
    for c in colores:
        if q in (c.get("nombre", "") or "").lower():
            results.append(c)
        if len(results) >= limit:
            break
    return results


def search_talles(query: str, producto_id: int = None, color_id: int = None, limit: int = 8) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    results = []
    if producto_id and color_id:
        talles = get_talles_by_producto_color(producto_id, color_id)
    else:
        talles = get_tallas()
    for t in talles:
        if q in (t.get("nombre", "") or "").lower():
            results.append(t)
        if len(results) >= limit:
            break
    return results
