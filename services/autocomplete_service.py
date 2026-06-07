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


def search_productos(query: str, limit: int = 8) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    results = []

    all_variants = get_variantes_con_producto()
    from collections import defaultdict
    prod_variants: dict[int, list] = defaultdict(list)
    for v in all_variants:
        prod_variants[v["producto_id"]].append(v)

    for p in get_productos():
        if q not in (p.get("detalle", "") or "").lower():
            continue

        # 1. Product entry
        results.append({"is_variant": False, **p})
        if len(results) >= limit:
            return results

        # 2. Curva suggestions for this product immediately
        if p["id"] in prod_variants:
            pvars = prod_variants[p["id"]]
            by_color: dict[str, list] = {}
            for v in pvars:
                by_color.setdefault(v.get("color") or "Sin color", []).append(v)

            for cname, cvars in by_color.items():
                if len(cvars) >= 2:
                    total = sum(float(v.get("precio_unitario", 0) or 0) for v in cvars)
                    results.append({
                        "is_curva": True, "es_surtida": False,
                        "id": p["id"],
                        "detalle": f"Curva {cname}",
                        "producto_detalle": p.get("detalle", ""),
                        "precio_unitario": total,
                        "color_id": cvars[0].get("color_id"),
                        "color": cname,
                        "variante_ids": [v["variante_id"] for v in cvars],
                    })
                    if len(results) >= limit:
                        return results

            if len(by_color) >= 2:
                # Price = one complete set of talles (first color)
                first_color_vars = next(iter(by_color.values()))
                total = sum(float(v.get("precio_unitario", 0) or 0) for v in first_color_vars)
                results.append({
                    "is_curva": True, "es_surtida": True,
                    "id": p["id"],
                    "detalle": "Curva Surtida",
                    "producto_detalle": p.get("detalle", ""),
                    "precio_unitario": total,
                    "variante_ids": [v["variante_id"] for v in pvars],
                })
                if len(results) >= limit:
                    return results

    # 3. Variant search for unmatched variants
    if len(results) < limit:
        for v in all_variants:
            color = v.get("color") or ""
            talla = v.get("talla") or ""
            label = f"{v.get('producto_detalle', '')} {color} {talla}".lower()
            if q in label:
                already = any(
                    r.get("is_variant") and r.get("variante_id") == v["variante_id"]
                    for r in results
                )
                if not already:
                    results.append({
                        "is_variant": True,
                        "id": v["producto_id"],
                        "detalle": v["producto_detalle"],
                        "variante_id": v["variante_id"],
                        "color_id": v.get("color_id"),
                        "talla_id": v.get("talla_id"),
                        "color": color,
                        "talla": talla,
                        "precio_unitario": v.get("precio_unitario", 0),
                        "precio_compra": v.get("precio_compra", 0),
                        "stock_actual": v.get("stock_actual", 0),
                    })
                if len(results) >= limit:
                    return results

    return results


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

    # Search products by name
    for p in get_productos_proveedor():
        if q in (p.get("detalle", "") or "").lower():
            results.append({"is_variant": False, **p})
        if len(results) >= limit:
            return results

    # If room left, search variants by product+color+talla
    if len(results) < limit:
        for v in get_variantes_proveedor():
            color = v.get("color") or ""
            talla = v.get("talla") or ""
            label = f"{v.get('producto_detalle', '')} {color} {talla}".lower()
            if q in label:
                already = any(
                    r.get("is_variant") and r.get("variante_id") == v["variante_id"]
                    for r in results
                )
                if not already:
                    results.append({
                        "is_variant": True,
                        "id": v["producto_id"],
                        "detalle": v["producto_detalle"],
                        "variante_id": v["variante_id"],
                        "color_id": v.get("color_id"),
                        "talla_id": v.get("talla_id"),
                        "color": color,
                        "talla": talla,
                        "precio_unitario": v.get("precio_unitario", 0),
                        "precio_compra": v.get("precio_compra", 0),
                        "stock_actual": v.get("stock_actual", 0),
                    })
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
