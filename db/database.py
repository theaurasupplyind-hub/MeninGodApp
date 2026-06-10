import sqlite3
import logging
import os
from pathlib import Path
from datetime import datetime

log = logging.getLogger("mvp10")

DB_PATH = Path(os.getenv("APPDATA")) / "MVP 1.0" / "mvp10.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    log.info(f"DB path: {DB_PATH}")
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL,
            domicilio   TEXT DEFAULT '',
            telefono    TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero          TEXT UNIQUE NOT NULL,
            fecha           TEXT NOT NULL,
            cliente_nombre  TEXT DEFAULT '',
            domicilio       TEXT DEFAULT '',
            telefono        TEXT DEFAULT '',
            envio           REAL DEFAULT 0,
            total           REAL DEFAULT 0,
            tipo_entrega    TEXT DEFAULT 'Retira',
            fecha_estimada  TEXT DEFAULT '',
            estado          TEXT DEFAULT 'Pendiente',
            notas           TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS factura_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id      INTEGER NOT NULL,
            cantidad        REAL DEFAULT 1,
            detalle         TEXT DEFAULT '',
            precio_unitario REAL DEFAULT 0,
            total           REAL DEFAULT 0,
            FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            detalle         TEXT NOT NULL,
            precio_unitario REAL DEFAULT 0,
            stock_actual    REAL DEFAULT 0,
            stock_minimo    REAL DEFAULT 0,
            stock_reservado REAL DEFAULT 0
        )
    """)

    existing_fi_cols = {row[1] for row in c.execute("PRAGMA table_info(factura_items)")}
    if "producto_id" not in existing_fi_cols:
        c.execute("ALTER TABLE factura_items ADD COLUMN producto_id INTEGER DEFAULT NULL")
    if "curva_color_ids" not in existing_fi_cols:
        c.execute("ALTER TABLE factura_items ADD COLUMN curva_color_ids TEXT DEFAULT NULL")
    if "variante_id" not in existing_fi_cols:
        c.execute("ALTER TABLE factura_items ADD COLUMN variante_id INTEGER DEFAULT NULL")

    c.execute("""
        CREATE TABLE IF NOT EXISTS cuenta_corriente (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id  INTEGER NOT NULL,
            fecha       TEXT NOT NULL,
            tipo        TEXT NOT NULL,
            referencia  TEXT DEFAULT '',
            descripcion TEXT DEFAULT '',
            debe        REAL DEFAULT 0,
            haber       REAL DEFAULT 0,
            saldo       REAL DEFAULT 0,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_wasi (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT NOT NULL,
            tipo        TEXT NOT NULL,
            categoria   TEXT DEFAULT '',
            concepto    TEXT DEFAULT '',
            monto       REAL DEFAULT 0
        )
    """)

    # ── Nuevas tablas para compras y proveedores ─────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL,
            telefono    TEXT DEFAULT '',
            domicilio   TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cuenta_corriente_proveedores (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor_id  INTEGER NOT NULL,
            fecha         TEXT NOT NULL,
            tipo          TEXT NOT NULL,
            referencia    TEXT DEFAULT '',
            descripcion   TEXT DEFAULT '',
            debe          REAL DEFAULT 0,
            haber         REAL DEFAULT 0,
            saldo         REAL DEFAULT 0,
            FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS compras (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            numero            TEXT UNIQUE NOT NULL,
            fecha             TEXT NOT NULL,
            proveedor_id      INTEGER,
            proveedor_nombre  TEXT DEFAULT '',
            total             REAL DEFAULT 0,
            notas             TEXT DEFAULT '',
            FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS compra_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            compra_id       INTEGER NOT NULL,
            cantidad        REAL DEFAULT 1,
            detalle         TEXT DEFAULT '',
            precio_unitario REAL DEFAULT 0,
            total           REAL DEFAULT 0,
            FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE
        )
    """)

    # ── Nuevas tablas del plan ropa ─────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS tipo_producto (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS colores (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            hex    TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tallas (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS variantes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id      INTEGER NOT NULL,
            tipo_producto_id INTEGER,
            color_id         INTEGER,
            talla_id         INTEGER,
            precio_unitario  REAL DEFAULT 0,
            stock_actual     REAL DEFAULT 0,
            stock_minimo     REAL DEFAULT 0,
            stock_reservado  REAL DEFAULT 0,
            FOREIGN KEY (producto_id)      REFERENCES productos(id) ON DELETE CASCADE,
            FOREIGN KEY (tipo_producto_id) REFERENCES tipo_producto(id),
            FOREIGN KEY (color_id)         REFERENCES colores(id),
            FOREIGN KEY (talla_id)         REFERENCES tallas(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS localidades (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre    TEXT NOT NULL,
            provincia TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS curvas_pendientes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id      INTEGER NOT NULL,
            factura_numero  TEXT NOT NULL,
            producto_id     INTEGER NOT NULL,
            detalle_curva   TEXT NOT NULL,
            es_surtida      INTEGER DEFAULT 0,
            color_id        INTEGER,
            variante_ids    TEXT NOT NULL,
            cantidad        REAL DEFAULT 1,
            precio_total    REAL DEFAULT 0,
            resuelta        INTEGER DEFAULT 0,
            FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)

    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(facturas)")}
    if "seña" not in existing_cols:
        c.execute("ALTER TABLE facturas ADD COLUMN seña REAL DEFAULT 0")
    if "empresa_envio" not in existing_cols:
        c.execute("ALTER TABLE facturas ADD COLUMN empresa_envio TEXT DEFAULT ''")
    if "localidad_id" not in existing_cols:
        c.execute("ALTER TABLE facturas ADD COLUMN localidad_id INTEGER DEFAULT NULL")
    if "fecha_envio" not in existing_cols:
        c.execute("ALTER TABLE facturas ADD COLUMN fecha_envio TEXT DEFAULT ''")
    if "envio_estado" not in existing_cols:
        c.execute("ALTER TABLE facturas ADD COLUMN envio_estado TEXT DEFAULT 'No enviado'")

    existing_clientes_cols = {row[1] for row in c.execute("PRAGMA table_info(clientes)")}
    if "localidad_id" not in existing_clientes_cols:
        c.execute("ALTER TABLE clientes ADD COLUMN localidad_id INTEGER DEFAULT NULL")
    if "empresa_envio" not in existing_clientes_cols:
        c.execute("ALTER TABLE clientes ADD COLUMN empresa_envio TEXT DEFAULT ''")

    existing_prod_cols = {row[1] for row in c.execute("PRAGMA table_info(productos)")}
    if "tipo_origen" not in existing_prod_cols:
        c.execute("ALTER TABLE productos ADD COLUMN tipo_origen TEXT NOT NULL DEFAULT 'proveedor'")

    existing_var_cols = {row[1] for row in c.execute("PRAGMA table_info(variantes)")}
    if "precio_compra" not in existing_var_cols:
        c.execute("ALTER TABLE variantes ADD COLUMN precio_compra REAL DEFAULT 0")
    if "precio_compra_anterior" not in existing_var_cols:
        c.execute("ALTER TABLE variantes ADD COLUMN precio_compra_anterior REAL DEFAULT 0")
    if "precio_fabricacion" not in existing_var_cols:
        c.execute("ALTER TABLE variantes ADD COLUMN precio_fabricacion REAL DEFAULT 0")
    if "activo" not in existing_var_cols:
        c.execute("ALTER TABLE variantes ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")

    # ── Seed data for colores / tallas ───────────────────────────────────────
    colores_default = [
        ("Negro", "#000000"), ("Blanco", "#FFFFFF"), ("Rojo", "#E53935"),
        ("Azul", "#1E88E5"), ("Verde", "#43A047"), ("Gris", "#757575"),
        ("Rosa", "#EC407A"), ("Amarillo", "#FDD835"), ("Naranja", "#FB8C00"),
    ]
    for nombre, hex_val in colores_default:
        c.execute("INSERT OR IGNORE INTO colores (nombre, hex) VALUES (?,?)", (nombre, hex_val))

    tallas_default = ["S", "M", "L", "XL", "XXL", "XXXL", "Único"]
    for nombre in tallas_default:
        c.execute("INSERT OR IGNORE INTO tallas (nombre) VALUES (?)", (nombre,))

    # -- Migrate compra_items columns -----------------------------------------
    existing_ci_cols = {row[1] for row in c.execute("PRAGMA table_info(compra_items)")}
    if "variante_id" not in existing_ci_cols:
        c.execute("ALTER TABLE compra_items ADD COLUMN variante_id INTEGER DEFAULT NULL")
    for col in ["producto_id", "color_id", "talla_id"]:
        if col not in existing_ci_cols:
            c.execute(f"ALTER TABLE compra_items ADD COLUMN {col} INTEGER DEFAULT NULL")

    # -- Create missing tables ------------------------------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL UNIQUE,
            pin         TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sesiones (
            id          TEXT PRIMARY KEY,
            usuario_id  INTEGER NOT NULL,
            inicio      TEXT DEFAULT (datetime('now','localtime')),
            fin         TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_stock (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            variante_id       INTEGER,
            producto_id       INTEGER,
            tipo              TEXT NOT NULL,
            referencia        TEXT DEFAULT '',
            cantidad          REAL NOT NULL,
            stock_resultante  REAL DEFAULT 0,
            motivo            TEXT DEFAULT '',
            created_at        TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS actividad (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id  INTEGER,
            tipo        TEXT NOT NULL,
            referencia  TEXT DEFAULT '',
            descripcion TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


# ── Numero de factura / compra ──────────────────────────────────────────────

def _next_numero() -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT MAX(CAST(SUBSTR(numero, 3) AS INTEGER)) FROM facturas WHERE numero LIKE 'F-%'"
    )
    row = c.fetchone()[0]
    conn.close()
    next_num = (row or 10249) + 1
    return f"F-{next_num}"

def _next_numero_compra() -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT MAX(CAST(SUBSTR(numero, 3) AS INTEGER)) FROM compras WHERE numero LIKE 'C-%'"
    )
    row = c.fetchone()[0]
    conn.close()
    next_num = (row or 1001) + 1
    return f"C-{next_num}"


# ── Facturas ─────────────────────────────────────────────────────────────────

def _update_cliente_empresa_envio(conn, cliente_nombre: str, empresa_envio: str) -> None:
    if not cliente_nombre.strip() or not empresa_envio.strip():
        return
    c = conn.cursor()
    c.execute(
        "UPDATE clientes SET empresa_envio = ? WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?))",
        (empresa_envio.strip(), cliente_nombre.strip()),
    )


def save_factura(data: dict, items: list) -> str:
    conn = get_connection()
    c = conn.cursor()
    numero = _next_numero()

    c.execute("""
        INSERT INTO facturas
            (numero, fecha, cliente_nombre, domicilio, telefono,
             envio, total, tipo_entrega, fecha_estimada, estado,
             seña, empresa_envio, localidad_id, fecha_envio)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        numero,
        data.get("fecha", datetime.now().strftime("%d/%m/%Y")),
        data.get("cliente", ""),
        data.get("domicilio", ""),
        data.get("telefono", ""),
        data.get("envio", 0),
        data.get("total", 0),
        data.get("tipo_entrega", "Retira"),
        data.get("fecha_estimada", ""),
        "Pendiente",
        data.get("seña", 0),
        data.get("empresa_envio", ""),
        data.get("localidad_id"),
        data.get("fecha_envio", ""),
    ))
    factura_id = c.lastrowid

    for item in items:
        if item.get("is_note"):
            continue
        c.execute("""
            INSERT INTO factura_items (factura_id, cantidad, detalle, precio_unitario, total, producto_id, variante_id, curva_color_ids)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            factura_id,
            item.get("cantidad", 1),
            item.get("detalle", ""),
            item.get("precio_unitario", 0),
            item.get("total", 0),
            item.get("producto_id"),
            item.get("variante_id"),
            item.get("curva_color_ids"),
        ))
    _update_cliente_empresa_envio(conn, data.get("cliente", ""), data.get("empresa_envio", ""))
    conn.commit()
    conn.close()
    return numero


def update_factura(numero: str, data: dict, items: list) -> str:
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        UPDATE facturas
        SET fecha = ?, cliente_nombre = ?, domicilio = ?, telefono = ?,
            envio = ?, total = ?, tipo_entrega = ?, fecha_estimada = ?,
            seña = ?, empresa_envio = ?, localidad_id = ?, fecha_envio = ?
        WHERE numero = ?
        """,
        (
            data.get("fecha", datetime.now().strftime("%d/%m/%Y")),
            data.get("cliente", ""),
            data.get("domicilio", ""),
            data.get("telefono", ""),
            data.get("envio", 0),
            data.get("total", 0),
            data.get("tipo_entrega", "Retira"),
            data.get("fecha_estimada", ""),
            data.get("seña", 0),
            data.get("empresa_envio", ""),
            data.get("localidad_id"),
            data.get("fecha_envio", ""),
            numero,
        ),
    )

    c.execute("SELECT id FROM facturas WHERE numero = ?", (numero,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Factura no encontrada: {numero}")

    factura_id = row["id"]
    c.execute("DELETE FROM factura_items WHERE factura_id = ?", (factura_id,))

    for item in items:
        if item.get("is_note"):
            continue
        c.execute("""
            INSERT INTO factura_items (factura_id, cantidad, detalle, precio_unitario, total, producto_id, variante_id, curva_color_ids)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            factura_id,
            item.get("cantidad", 1),
            item.get("detalle", ""),
            item.get("precio_unitario", 0),
            item.get("total", 0),
            item.get("producto_id"),
            item.get("variante_id"),
            item.get("curva_color_ids"),
        ))

    _update_cliente_empresa_envio(conn, data.get("cliente", ""), data.get("empresa_envio", ""))
    conn.commit()
    conn.close()
    return numero


def get_facturas(limit: int = 50) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            f.id, f.numero, f.fecha, f.cliente_nombre,
            f.total, f.estado, f.envio_estado,
            MAX(0, f.total - COALESCE(f."seña", 0) - COALESCE(pagos.total_pagado, 0)) AS deuda
        FROM facturas f
        LEFT JOIN (
            SELECT referencia, SUM(haber) AS total_pagado
            FROM cuenta_corriente
            WHERE tipo = 'Pago'
            GROUP BY referencia
        ) pagos ON pagos.referencia = f.numero
        ORDER BY f.id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_factura_by_numero(numero: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM facturas WHERE numero = ?", (numero,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    factura = dict(row)
    c.execute("SELECT * FROM factura_items WHERE factura_id = ?", (factura["id"],))
    factura["items"] = [dict(r) for r in c.fetchall()]
    conn.close()
    return factura


def get_stats() -> dict:
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM facturas")
    row = c.fetchone()
    total_all, count_all = row[1], row[0]

    c.execute("SELECT COALESCE(SUM(total),0) FROM facturas WHERE estado = 'Pagado'")
    cobrado = c.fetchone()[0]

    c.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM facturas WHERE estado = 'Pendiente'")
    row = c.fetchone()
    count_pendiente, pendiente = row[0], row[1]

    conn.close()
    return {
        "total_all":       total_all,
        "count_all":       count_all,
        "cobrado":         cobrado,
        "pendiente":       pendiente,
        "count_pendiente": count_pendiente,
    }


def update_estado(numero: str, estado: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE facturas SET estado = ? WHERE numero = ?", (estado, numero))
    conn.commit()
    conn.close()


def update_factura_estado(factura_id: int, nuevo_estado: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE facturas SET estado = ? WHERE id = ?",
        (nuevo_estado, factura_id)
    )
    conn.commit()
    conn.close()


# ── Clientes ─────────────────────────────────────────────────────────────────

def get_clientes() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM clientes ORDER BY nombre ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_cliente_by_nombre(nombre: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM clientes WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?))", (nombre,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def save_cliente(data: dict) -> int:
    existing = get_cliente_by_nombre(data.get("nombre", ""))
    if existing:
        update_cliente(existing["id"], data)
        return existing["id"]
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO clientes (nombre, domicilio, telefono) VALUES (?,?,?)",
        (
            data.get("nombre", ""),
            data.get("domicilio", ""),
            data.get("telefono", ""),
        ),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_cliente(client_id: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE clientes SET nombre=?, domicilio=?, telefono=? WHERE id=?",
        (
            data.get("nombre", ""),
            data.get("domicilio", ""),
            data.get("telefono", ""),
            client_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_cliente(client_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM clientes WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()


# ── Productos ────────────────────────────────────────────────────────────────

def get_productos() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM productos ORDER BY detalle ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_producto_by_detalle(detalle: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE LOWER(TRIM(detalle)) = LOWER(TRIM(?))", (detalle,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_producto_by_id(producto_id: int) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def save_producto(data: dict) -> int:
    existing = get_producto_by_detalle(data.get("detalle", ""))
    if existing:
        update_data = {"detalle": data.get("detalle", existing["detalle"])}
        if "precio_unitario" in data:
            update_data["precio_unitario"] = data["precio_unitario"]
        else:
            update_data["precio_unitario"] = existing["precio_unitario"]
        if "stock_actual" in data:
            update_data["stock_actual"] = data["stock_actual"]
        else:
            update_data["stock_actual"] = existing["stock_actual"]
        if "stock_minimo" in data:
            update_data["stock_minimo"] = data["stock_minimo"]
        else:
            update_data["stock_minimo"] = existing["stock_minimo"]
        if "tipo_origen" in data:
            update_data["tipo_origen"] = data["tipo_origen"]
        else:
            update_data["tipo_origen"] = existing.get("tipo_origen", "proveedor")
        update_producto(existing["id"], update_data)
        return existing["id"]
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO productos (detalle, precio_unitario, stock_actual, stock_minimo, stock_reservado, tipo_origen) VALUES (?,?,?,?,?,?)",
        (
            data.get("detalle", ""),
            data.get("precio_unitario", 0),
            data.get("stock_actual", 0),
            data.get("stock_minimo", 0),
            0,
            data.get("tipo_origen", "proveedor"),
        ),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_producto(prod_id: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE id = ?", (prod_id,))
    current = dict(c.fetchone() or {})
    c.execute(
        "UPDATE productos SET detalle=?, precio_unitario=?, stock_actual=?, stock_minimo=?, stock_reservado=?, tipo_origen=? WHERE id=?",
        (
            data.get("detalle",         current.get("detalle", "")),
            data.get("precio_unitario", current.get("precio_unitario", 0)),
            data.get("stock_actual",    current.get("stock_actual", 0)),
            data.get("stock_minimo",    current.get("stock_minimo", 0)),
            data.get("stock_reservado", current.get("stock_reservado", 0)),
            data.get("tipo_origen",     current.get("tipo_origen", "proveedor")),
            prod_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_producto(prod_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM productos WHERE id = ?", (prod_id,))
    conn.commit()
    conn.close()


def ajustar_stock(prod_id: int, delta: float):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE productos SET stock_actual = MAX(0, stock_actual + ?) WHERE id = ?",
        (delta, prod_id),
    )
    conn.commit()
    conn.close()


def reservar_stock(prod_id: int, cantidad: float):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT stock_actual, stock_reservado FROM productos WHERE id = ?", (prod_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    disponible = row["stock_actual"]
    a_reservar = min(cantidad, disponible)
    c.execute(
        "UPDATE productos SET stock_actual = stock_actual - ?, stock_reservado = stock_reservado + ? WHERE id = ?",
        (a_reservar, a_reservar, prod_id),
    )
    conn.commit()
    conn.close()


def get_stock_bajo() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM productos
        WHERE stock_minimo > 0 AND stock_actual <= stock_minimo
        ORDER BY (stock_actual - stock_minimo) ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ── Stock: descuento al facturar ────────────────────────────────────────────

def procesar_stock_factura(numero_factura: str, cliente_nombre: str, items: list) -> list:
    for item in items:
        if item.get("is_note"):
            continue
        if item.get("curva_color_ids"):
            continue
        variante_id = item.get("variante_id")
        producto_id = item.get("producto_id")
        cantidad = float(item.get("cantidad", 0) or 0)
        if cantidad <= 0:
            continue

        conn = get_connection()
        c = conn.cursor()

        if variante_id:
            c.execute(
                "UPDATE variantes SET stock_actual = MAX(0, COALESCE(stock_actual,0) - ?) WHERE id = ?",
                (cantidad, variante_id)
            )
            c.execute("SELECT stock_actual FROM variantes WHERE id = ?", (variante_id,))
            stock_resultante = float(c.fetchone()[0] or 0)
            c.execute("""
                INSERT INTO movimientos_stock (variante_id, tipo, referencia, cantidad, stock_resultante, motivo)
                VALUES (?,?,?,?,?,?)
            """, (variante_id, "facturacion", numero_factura, -cantidad, stock_resultante,
                  f"Factura {numero_factura} — {cliente_nombre}"))
        elif producto_id:
            c.execute(
                "UPDATE productos SET stock_actual = MAX(0, COALESCE(stock_actual,0) - ?) WHERE id = ?",
                (cantidad, producto_id)
            )

        conn.commit()
        conn.close()

    return []


def revertir_stock_factura(numero_factura: str):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """SELECT fi.cantidad, fi.producto_id, fi.variante_id
           FROM factura_items fi
           JOIN facturas f ON f.id = fi.factura_id
           WHERE f.numero = ?""",
        (numero_factura,)
    )
    rows = c.fetchall()

    for row in rows:
        cantidad = float(row["cantidad"] or 0)
        if cantidad <= 0:
            continue
        vid = row["variante_id"]
        if vid:
            c.execute(
                "UPDATE variantes SET stock_actual = COALESCE(stock_actual,0) + ? WHERE id = ?",
                (cantidad, vid)
            )
        else:
            pid = row["producto_id"]
            if pid:
                c.execute(
                    "UPDATE productos SET stock_actual = COALESCE(stock_actual,0) + ? WHERE id = ?",
                    (cantidad, pid)
                )

    conn.commit()
    conn.close()


def procesar_stock_curva_color(items_controls: list) -> None:
    """Deduct variant stock for per-color curva items after saving."""
    conn = get_connection()
    c = conn.cursor()
    for item in items_controls:
        ccm = item.get("curva_color_metadata", {}).get("value")
        if not ccm:
            continue
        cantidad = float(item["cant"].value or "1")
        for vid in ccm["variante_ids"]:
            c.execute(
                "UPDATE variantes SET stock_actual = MAX(0, COALESCE(stock_actual,0) - ?) WHERE id = ?",
                (cantidad, int(vid))
            )
    conn.commit()
    conn.close()


def revertir_stock_curva_color(numero: str) -> None:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """SELECT fi.cantidad, fi.curva_color_ids
           FROM factura_items fi
           JOIN facturas f ON f.id = fi.factura_id
           WHERE f.numero = ? AND fi.curva_color_ids IS NOT NULL""",
        (numero,)
    )
    for row in c.fetchall():
        cantidad = float(row["cantidad"] or 0)
        ids_str = row["curva_color_ids"]
        if not ids_str or cantidad <= 0:
            continue
        for vid in ids_str.split(","):
            vid = vid.strip()
            if not vid:
                continue
            c.execute(
                "UPDATE variantes SET stock_actual = COALESCE(stock_actual,0) + ? WHERE id = ?",
                (cantidad, int(vid))
            )
    conn.commit()
    conn.close()


# ── Cuenta corriente (clientes) ─────────────────────────────────────────────

def _saldo_actual_cliente(cliente_id: int, cursor) -> float:
    cursor.execute(
        "SELECT COALESCE(SUM(debe - haber), 0) FROM cuenta_corriente WHERE cliente_id = ?",
        (cliente_id,),
    )
    return cursor.fetchone()[0]


def registrar_movimiento(
    cliente_id: int,
    tipo: str,
    monto: float,
    referencia: str = "",
    descripcion: str = "",
    es_pago: bool = False,
) -> int:
    conn = get_connection()
    c = conn.cursor()
    saldo_previo = _saldo_actual_cliente(cliente_id, c)
    debe  = 0.0 if es_pago else monto
    haber = monto if es_pago else 0.0
    nuevo_saldo = saldo_previo + debe - haber

    c.execute("""
        INSERT INTO cuenta_corriente
            (cliente_id, fecha, tipo, referencia, descripcion, debe, haber, saldo)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        cliente_id,
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        tipo,
        referencia,
        descripcion,
        debe,
        haber,
        nuevo_saldo,
    ))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def get_saldo_cliente(cliente_id: int) -> float:
    conn = get_connection()
    c = conn.cursor()
    saldo = _saldo_actual_cliente(cliente_id, c)
    conn.close()
    return saldo


def get_movimientos_cliente(cliente_id: int, limit: int = 100) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM cuenta_corriente
        WHERE cliente_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (cliente_id, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_resumen_cuentas() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            cl.id,
            cl.nombre,
            cl.telefono,
            COALESCE(SUM(cc.debe - cc.haber), 0) AS saldo
        FROM clientes cl
        LEFT JOIN cuenta_corriente cc ON cc.cliente_id = cl.id
        GROUP BY cl.id
        ORDER BY cl.nombre ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ── Auto-guardar desde factura ──────────────────────────────────────────────

def save_from_factura(cliente_data: dict, items: list, numero_factura: str = "", total: float = 0, seña: float = 0):
    nombre = (cliente_data.get("nombre", "") or "").strip()
    cliente_id = None
    if nombre:
        cliente_id = save_cliente(cliente_data)

    for item in items:
        detalle = (item.get("detalle", "") or "").strip()
        if detalle:
            save_producto({
                "detalle": detalle,
                "precio_unitario": item.get("precio_unitario", 0),
            })

    saldo_pendiente = max(0, total - (seña or 0))
    if cliente_id and saldo_pendiente > 0:
        registrar_movimiento(
            cliente_id=cliente_id,
            tipo="Factura",
            monto=saldo_pendiente,
            referencia=numero_factura,
            descripcion=f"Factura {numero_factura}" + (f" (seña ${int(seña):,})" if seña else ""),
            es_pago=False,
        )


def registrar_cobro_factura(
    factura_id: int,
    numero_factura: str,
    cliente_id: int | None,
    cliente_nombre: str,
    monto: float,
    medio_pago: str,
    nota: str = "",
) -> dict:
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT total FROM facturas WHERE id = ?", (factura_id,))
    row = c.fetchone()
    total_factura = float(row["total"] if row else 0)

    cobrado_previo = 0.0
    if cliente_id:
        c.execute(
            """SELECT COALESCE(SUM(haber), 0) as total_pagado
               FROM cuenta_corriente
               WHERE cliente_id = ? AND referencia = ? AND tipo = 'Pago'""",
            (cliente_id, numero_factura)
        )
        cobrado_previo = float(c.fetchone()["total_pagado"] or 0)

    saldo_restante = max(0, total_factura - cobrado_previo - monto)

    if cliente_id:
        saldo_actual = _saldo_actual_cliente(cliente_id, c)
        nuevo_saldo = saldo_actual - monto
        descripcion = f"Cobro {medio_pago} — Factura {numero_factura}"
        if nota.strip():
            descripcion += f" — {nota.strip()}"
        c.execute("""
            INSERT INTO cuenta_corriente
                (cliente_id, fecha, tipo, referencia, descripcion, debe, haber, saldo)
            VALUES (?, ?, 'Pago', ?, ?, 0, ?, ?)
        """, (
            cliente_id,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            numero_factura,
            descripcion,
            monto,
            nuevo_saldo,
        ))

    concepto = f"Cobro {medio_pago} — Factura {numero_factura} — {cliente_nombre}"
    if nota.strip():
        concepto += f" — {nota.strip()}"
    c.execute("""
        INSERT INTO movimientos_wasi (fecha, tipo, categoria, concepto, monto)
        VALUES (?, 'Ingreso', 'Factura / Venta', ?, ?)
    """, (
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        concepto,
        monto,
    ))

    estado_nuevo = "Pendiente"
    if saldo_restante <= 0:
        estado_nuevo = "Pagado"
        c.execute(
            "UPDATE facturas SET estado = ? WHERE id = ?",
            (estado_nuevo, factura_id)
        )

    conn.commit()
    conn.close()
    return {"saldo_restante": saldo_restante, "estado_nuevo": estado_nuevo}


# ── Cuenta WASI (Caja / Bancos) ─────────────────────────────────────────────

def get_saldo_wasi() -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN tipo = 'Ingreso' THEN monto ELSE 0 END), 0) as total_ingresos,
            COALESCE(SUM(CASE WHEN tipo = 'Egreso' THEN monto ELSE 0 END), 0) as total_egresos
        FROM movimientos_wasi
    """)
    row = c.fetchone()
    conn.close()
    
    ingresos = row["total_ingresos"]
    egresos = row["total_egresos"]
    return {
        "ingresos": ingresos,
        "egresos": egresos,
        "saldo": ingresos - egresos
    }


def get_movimientos_wasi(limit: int = 100) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM movimientos_wasi 
        ORDER BY id DESC 
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def registrar_movimiento_wasi(tipo: str, categoria: str, concepto: str, monto: float):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO movimientos_wasi (fecha, tipo, categoria, concepto, monto)
        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        tipo,
        categoria,
        concepto,
        monto
    ))
    conn.commit()
    conn.close()


# ── Proveedores ──────────────────────────────────────────────────────────────

def get_proveedores() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM proveedores ORDER BY nombre ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_proveedor_by_nombre(nombre: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM proveedores WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?))", (nombre,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def save_proveedor(data: dict) -> int:
    existing = get_proveedor_by_nombre(data.get("nombre", ""))
    if existing:
        update_proveedor(existing["id"], data)
        return existing["id"]
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO proveedores (nombre, telefono, domicilio) VALUES (?,?,?)",
        (
            data.get("nombre", ""),
            data.get("telefono", ""),
            data.get("domicilio", ""),
        ),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_proveedor(prov_id: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE proveedores SET nombre=?, telefono=?, domicilio=? WHERE id=?",
        (
            data.get("nombre", ""),
            data.get("telefono", ""),
            data.get("domicilio", ""),
            prov_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_proveedor(prov_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM proveedores WHERE id = ?", (prov_id,))
    conn.commit()
    conn.close()


# ── Cuenta corriente proveedores ───────────────────────────────────────────

def _saldo_actual_proveedor(proveedor_id: int, cursor) -> float:
    cursor.execute(
        "SELECT COALESCE(SUM(debe - haber), 0) FROM cuenta_corriente_proveedores WHERE proveedor_id = ?",
        (proveedor_id,),
    )
    return cursor.fetchone()[0]


def registrar_movimiento_proveedor(
    proveedor_id: int,
    tipo: str,
    monto: float,
    referencia: str = "",
    descripcion: str = "",
    es_pago: bool = False,
) -> int:
    conn = get_connection()
    c = conn.cursor()
    saldo_previo = _saldo_actual_proveedor(proveedor_id, c)
    debe  = monto if es_pago else 0.0
    haber = 0.0 if es_pago else monto
    nuevo_saldo = saldo_previo + debe - haber

    c.execute("""
        INSERT INTO cuenta_corriente_proveedores
            (proveedor_id, fecha, tipo, referencia, descripcion, debe, haber, saldo)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        proveedor_id,
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        tipo,
        referencia,
        descripcion,
        debe,
        haber,
        nuevo_saldo,
    ))

    # Registrar egreso en movimientos_wasi
    if es_pago and monto > 0:
        c.execute("SELECT nombre FROM proveedores WHERE id = ?", (proveedor_id,))
        prov_row = c.fetchone()
        prov_nombre = dict(prov_row)["nombre"] if prov_row else ""
        c.execute("""
            INSERT INTO movimientos_wasi (fecha, tipo, categoria, concepto, monto)
            VALUES (?, 'Egreso', 'Proveedores', ?, ?)
        """, (
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            f"Pago a proveedor — {prov_nombre}" + (f" — {descripcion}" if descripcion.strip() else ""),
            monto,
        ))

    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def get_movimientos_proveedor(proveedor_id: int, limit: int = 100) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM cuenta_corriente_proveedores
        WHERE proveedor_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (proveedor_id, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_resumen_proveedores() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            p.id,
            p.nombre,
            p.telefono,
            COALESCE(SUM(cc.debe - cc.haber), 0) AS saldo
        FROM proveedores p
        LEFT JOIN cuenta_corriente_proveedores cc ON cc.proveedor_id = p.id
        GROUP BY p.id
        ORDER BY p.nombre ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ── Compras ─────────────────────────────────────────────────────────────────

def save_compra(data: dict, items: list) -> str:
    conn = get_connection()
    c = conn.cursor()
    numero = _next_numero_compra()

    # Auto-crear proveedor si se pasó nombre sin ID
    proveedor_id = data.get("proveedor_id")
    proveedor_nombre = (data.get("proveedor_nombre", "") or "").strip()
    if not proveedor_id and proveedor_nombre:
        existing = get_proveedor_by_nombre(proveedor_nombre)
        if existing:
            proveedor_id = existing["id"]
        else:
            c.execute(
                "INSERT INTO proveedores (nombre, telefono, domicilio) VALUES (?,?,?)",
                (proveedor_nombre, "", "")
            )
            proveedor_id = c.lastrowid

    c.execute("""
        INSERT INTO compras
            (numero, fecha, proveedor_id, proveedor_nombre, total, notas)
        VALUES (?,?,?,?,?,?)
    """, (
        numero,
        data.get("fecha", datetime.now().strftime("%d/%m/%Y")),
        proveedor_id,
        proveedor_nombre,
        data.get("total", 0),
        data.get("notas", ""),
    ))
    compra_id = c.lastrowid

    for item in items:
        if item.get("detalle", "").strip():
            c.execute("""
                INSERT INTO compra_items (compra_id, cantidad, detalle, precio_unitario, total, variante_id, producto_id, color_id, talla_id)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                compra_id,
                item.get("cantidad", 1),
                item.get("detalle", ""),
                item.get("precio_unitario", 0),
                item.get("total", 0),
                item.get("variante_id"),
                item.get("_producto_id"),
                item.get("_color_id"),
                item.get("_talla_id"),
            ))

            detalle = item.get("detalle", "").strip()
            cantidad = float(item.get("cantidad", 0) or 0)
            precio = float(item.get("precio_unitario", 0) or 0)
            variante_id = item.get("variante_id")
            if detalle and cantidad > 0:
                if variante_id:
                    c.execute("UPDATE variantes SET precio_compra_anterior = precio_compra, precio_compra = ?, stock_actual = stock_actual + ? WHERE id = ?",
                              (precio, cantidad, variante_id))
                else:
                    prod = get_producto_by_detalle(detalle)
                    if prod:
                        c.execute(
                            "UPDATE productos SET stock_actual = stock_actual + ?, precio_unitario = ? WHERE id = ?",
                            (cantidad, precio, prod["id"])
                        )
                    else:
                        c.execute(
                            "INSERT INTO productos (detalle, precio_unitario, stock_actual, stock_minimo, stock_reservado) VALUES (?,?,?,0,0)",
                            (detalle, precio, cantidad)
                        )

    # Registrar en cuenta corriente del proveedor (haber: le debemos)
    total = data.get("total", 0)
    if proveedor_id and total > 0:
        saldo_previo = _saldo_actual_proveedor(proveedor_id, c)
        nuevo_saldo = saldo_previo + total
        c.execute("""
            INSERT INTO cuenta_corriente_proveedores
                (proveedor_id, fecha, tipo, referencia, descripcion, debe, haber, saldo)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            proveedor_id,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Compra",
            numero,
            f"Compra {numero}",
            0,
            total,
            nuevo_saldo,
        ))

    # Registrar egreso en movimientos_wasi
    if total > 0:
        c.execute("""
            INSERT INTO movimientos_wasi (fecha, tipo, categoria, concepto, monto)
            VALUES (?, 'Egreso', 'Compras', ?, ?)
        """, (
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            f"Compra {numero} — {proveedor_nombre}",
            total,
        ))

    conn.commit()
    conn.close()
    return numero


def get_compras(limit: int = 50) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT c.id, c.numero, c.fecha, c.proveedor_nombre, c.total,
               GROUP_CONCAT(ci.detalle, ', ') AS resumen
        FROM compras c
        LEFT JOIN compra_items ci ON ci.compra_id = c.id
        GROUP BY c.id
        ORDER BY c.id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_compra_by_numero(numero: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM compras WHERE numero = ?", (numero,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    compra = dict(row)
    c.execute("SELECT * FROM compra_items WHERE compra_id = ?", (compra["id"],))
    compra["items"] = [dict(r) for r in c.fetchall()]
    conn.close()
    return compra


def update_compra(numero: str, data: dict, items: list) -> str:
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id, total, proveedor_id FROM compras WHERE numero = ?", (numero,))
    old = c.fetchone()
    if not old:
        conn.close()
        raise ValueError(f"Compra no encontrada: {numero}")
    old_id = old["id"]
    old_total = old["total"]
    old_proveedor_id = old["proveedor_id"]

    # Revertir stock de items anteriores
    c.execute("SELECT detalle, cantidad, variante_id FROM compra_items WHERE compra_id = ?", (old_id,))
    for old_item in c.fetchall():
        detalle = old_item["detalle"]
        cantidad = float(old_item["cantidad"] or 0)
        variante_id = old_item["variante_id"]
        if detalle and cantidad > 0:
            if variante_id:
                c.execute(
                    "UPDATE variantes SET stock_actual = MAX(0, stock_actual - ?) WHERE id = ?",
                    (cantidad, variante_id)
                )
            else:
                prod = get_producto_by_detalle(detalle)
                if prod:
                    c.execute(
                        "UPDATE productos SET stock_actual = MAX(0, stock_actual - ?) WHERE id = ?",
                        (cantidad, prod["id"])
                    )

    # Revertir cuenta corriente proveedor vieja
    if old_proveedor_id and old_total > 0:
        saldo_previo = _saldo_actual_proveedor(old_proveedor_id, c)
        nuevo_saldo = saldo_previo + old_total
        c.execute("""
            INSERT INTO cuenta_corriente_proveedores
                (proveedor_id, fecha, tipo, referencia, descripcion, debe, haber, saldo)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            old_proveedor_id,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Ajuste",
            numero,
            f"Reversión compra {numero}",
            old_total,
            0,
            nuevo_saldo,
        ))
        # Eliminar egreso viejo de movimientos_wasi
        c.execute(
            "DELETE FROM movimientos_wasi WHERE concepto LIKE ? AND tipo = 'Egreso'",
            (f"Compra {numero}%",)
        )

    # Auto-crear proveedor nuevo si hace falta
    proveedor_id = data.get("proveedor_id")
    proveedor_nombre = (data.get("proveedor_nombre", "") or "").strip()
    if not proveedor_id and proveedor_nombre:
        existing = get_proveedor_by_nombre(proveedor_nombre)
        if existing:
            proveedor_id = existing["id"]
        else:
            c.execute(
                "INSERT INTO proveedores (nombre, telefono, domicilio) VALUES (?,?,?)",
                (proveedor_nombre, "", "")
            )
            proveedor_id = c.lastrowid

    # Actualizar cabecera
    c.execute("""
        UPDATE compras
        SET fecha = ?, proveedor_id = ?, proveedor_nombre = ?, total = ?, notas = ?
        WHERE numero = ?
    """, (
        data.get("fecha", datetime.now().strftime("%d/%m/%Y")),
        proveedor_id,
        proveedor_nombre,
        data.get("total", 0),
        data.get("notas", ""),
        numero,
    ))

    c.execute("DELETE FROM compra_items WHERE compra_id = ?", (old_id,))

    for item in items:
        if item.get("detalle", "").strip():
            c.execute("""
                INSERT INTO compra_items (compra_id, cantidad, detalle, precio_unitario, total, variante_id, producto_id, color_id, talla_id)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                old_id,
                item.get("cantidad", 1),
                item.get("detalle", ""),
                item.get("precio_unitario", 0),
                item.get("total", 0),
                item.get("variante_id"),
                item.get("_producto_id"),
                item.get("_color_id"),
                item.get("_talla_id"),
            ))

            detalle = item.get("detalle", "").strip()
            cantidad = float(item.get("cantidad", 0) or 0)
            precio = float(item.get("precio_unitario", 0) or 0)
            variante_id = item.get("variante_id")
            if detalle and cantidad > 0:
                if variante_id:
                    c.execute("UPDATE variantes SET precio_compra_anterior = precio_compra, precio_compra = ?, stock_actual = stock_actual + ? WHERE id = ?",
                              (precio, cantidad, variante_id))
                else:
                    prod = get_producto_by_detalle(detalle)
                    if prod:
                        c.execute(
                            "UPDATE productos SET stock_actual = stock_actual + ?, precio_unitario = ? WHERE id = ?",
                            (cantidad, precio, prod["id"])
                        )
                    else:
                        c.execute(
                            "INSERT INTO productos (detalle, precio_unitario, stock_actual, stock_minimo, stock_reservado) VALUES (?,?,?,0,0)",
                            (detalle, precio, cantidad)
                        )

    # Registrar nueva cuenta corriente
    total = data.get("total", 0)
    if proveedor_id and total > 0:
        saldo_previo = _saldo_actual_proveedor(proveedor_id, c)
        nuevo_saldo = saldo_previo + total
        c.execute("""
            INSERT INTO cuenta_corriente_proveedores
                (proveedor_id, fecha, tipo, referencia, descripcion, debe, haber, saldo)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            proveedor_id,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Compra",
            numero,
            f"Compra {numero}",
            0,
            total,
            nuevo_saldo,
        ))
        # Registrar nuevo egreso en movimientos_wasi
        c.execute("""
            INSERT INTO movimientos_wasi (fecha, tipo, categoria, concepto, monto)
            VALUES (?, 'Egreso', 'Compras', ?, ?)
        """, (
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            f"Compra {numero} — {proveedor_nombre}",
            total,
        ))

    conn.commit()
    conn.close()
    return numero


def delete_compra(numero: str):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id, total, proveedor_id FROM compras WHERE numero = ?", (numero,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    compra_id = row["id"]
    total = row["total"]
    proveedor_id = row["proveedor_id"]

    # Revertir stock
    c.execute("SELECT detalle, cantidad FROM compra_items WHERE compra_id = ?", (compra_id,))
    for item in c.fetchall():
        detalle = item["detalle"]
        cantidad = float(item["cantidad"] or 0)
        if detalle and cantidad > 0:
            prod = get_producto_by_detalle(detalle)
            if prod:
                c.execute(
                    "UPDATE productos SET stock_actual = MAX(0, stock_actual - ?) WHERE id = ?",
                    (cantidad, prod["id"])
                )

    # Revertir cuenta corriente
    if proveedor_id and total > 0:
        saldo_previo = _saldo_actual_proveedor(proveedor_id, c)
        nuevo_saldo = saldo_previo + total
        c.execute("""
            INSERT INTO cuenta_corriente_proveedores
                (proveedor_id, fecha, tipo, referencia, descripcion, debe, haber, saldo)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            proveedor_id,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Ajuste",
            numero,
            f"Eliminación compra {numero}",
            total,
            0,
            nuevo_saldo,
        ))

    # Eliminar egreso de movimientos_wasi
    c.execute(
        "DELETE FROM movimientos_wasi WHERE concepto LIKE ? AND tipo = 'Egreso'",
        (f"Compra {numero}%",)
    )

    c.execute("DELETE FROM compras WHERE id = ?", (compra_id,))
    conn.commit()
    conn.close()


def get_stats_compras() -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM compras")
    row = c.fetchone()
    conn.close()
    return {"count": row[0], "total": row[1]}


# ── Tipo producto ─────────────────────────────────────────────────────────────

def get_tipos_producto() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre FROM tipo_producto ORDER BY nombre")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def save_tipo_producto(nombre: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO tipo_producto (nombre) VALUES (?)", (nombre.strip(),)
    )
    c.execute("SELECT id FROM tipo_producto WHERE nombre = ?", (nombre.strip(),))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row["id"]


# ── Colores ───────────────────────────────────────────────────────────────────

def get_colores() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre, hex FROM colores ORDER BY nombre")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def save_color(nombre: str, hex: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO colores (nombre, hex) VALUES (?,?)",
        (nombre.strip(), hex.strip())
    )
    c.execute("SELECT id FROM colores WHERE nombre = ?", (nombre.strip(),))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row["id"]


# ── Tallas ────────────────────────────────────────────────────────────────────

def get_tallas() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre FROM tallas ORDER BY id")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def save_talla(nombre: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO tallas (nombre) VALUES (?)", (nombre.strip(),)
    )
    c.execute("SELECT id FROM tallas WHERE nombre = ?", (nombre.strip(),))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row["id"]


# ── Variantes ─────────────────────────────────────────────────────────────────

def get_variantes_by_producto(producto_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            v.id, v.precio_unitario, v.stock_actual, v.stock_minimo, v.stock_reservado,
            v.precio_compra, v.precio_fabricacion,
            v.color_id, v.talla_id,
            tp.nombre AS tipo, col.nombre AS color, tal.nombre AS talla
        FROM variantes v
        LEFT JOIN tipo_producto tp  ON v.tipo_producto_id = tp.id
        LEFT JOIN colores col       ON v.color_id = col.id
        LEFT JOIN tallas tal        ON v.talla_id = tal.id
        WHERE v.producto_id = ? AND v.activo = 1
        ORDER BY v.id
    """, (producto_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def save_variante(producto_id: int, data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO variantes
            (producto_id, tipo_producto_id, color_id, talla_id,
             precio_unitario, stock_actual, stock_minimo, stock_reservado,
             precio_compra, precio_fabricacion)
        VALUES (?,?,?,?,?,?,?,0,?,?)
    """, (
        producto_id,
        data.get("tipo_producto_id"),
        data.get("color_id"),
        data.get("talla_id"),
        data.get("precio_unitario", 0),
        data.get("stock_actual", 0),
        data.get("stock_minimo", 0),
        data.get("precio_compra", 0),
        data.get("precio_fabricacion", 0),
    ))
    variante_id = c.lastrowid
    conn.commit()
    conn.close()
    return variante_id


def update_variante(variante_id: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE variantes
        SET tipo_producto_id = ?, color_id = ?, talla_id = ?,
            precio_unitario = ?, stock_actual = ?, stock_minimo = ?
        WHERE id = ?
    """, (
        data.get("tipo_producto_id"),
        data.get("color_id"),
        data.get("talla_id"),
        data.get("precio_unitario", 0),
        data.get("stock_actual", 0),
        data.get("stock_minimo", 0),
        variante_id,
    ))
    conn.commit()
    conn.close()


def delete_variante(variante_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM variantes WHERE id = ?", (variante_id,))
    conn.commit()
    conn.close()


def get_variantes_activas(producto_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            v.id, v.precio_unitario, v.stock_actual, v.stock_minimo, v.stock_reservado,
            v.precio_compra, v.precio_fabricacion,
            tp.nombre AS tipo, col.nombre AS color, tal.nombre AS talla
        FROM variantes v
        LEFT JOIN tipo_producto tp  ON v.tipo_producto_id = tp.id
        LEFT JOIN colores col       ON v.color_id = col.id
        LEFT JOIN tallas tal        ON v.talla_id = tal.id
        WHERE v.producto_id = ? AND v.activo = 1
        ORDER BY v.id
    """, (producto_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def desactivar_variante(variante_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE variantes SET activo = 0 WHERE id = ?", (variante_id,))
    conn.commit()
    conn.close()


def ajustar_stock_variante(variante_id: int, delta: float):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE variantes SET stock_actual = MAX(0, stock_actual + ?) WHERE id = ?",
        (delta, variante_id),
    )
    conn.commit()
    conn.close()


def get_productos_proveedor() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE tipo_origen = 'proveedor' ORDER BY detalle ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_variantes_proveedor() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            p.id as producto_id, p.detalle as producto_detalle,
            v.id as variante_id, v.precio_unitario, v.precio_compra, v.stock_actual,
            v.color_id, v.talla_id,
            c.nombre as color, t.nombre as talla
        FROM productos p
        JOIN variantes v ON v.producto_id = p.id AND v.activo = 1
        LEFT JOIN colores c ON v.color_id = c.id
        LEFT JOIN tallas t ON v.talla_id = t.id
        WHERE p.tipo_origen = 'proveedor'
        ORDER BY p.detalle, c.nombre, t.nombre
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_variantes_con_producto() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            p.id as producto_id, p.detalle as producto_detalle,
            v.id as variante_id, v.precio_unitario, v.precio_compra, v.stock_actual,
            v.color_id, v.talla_id,
            c.nombre as color, t.nombre as talla
        FROM productos p
        JOIN variantes v ON v.producto_id = p.id AND v.activo = 1
        LEFT JOIN colores c ON v.color_id = c.id
        LEFT JOIN tallas t ON v.talla_id = t.id
        ORDER BY p.detalle, c.nombre, t.nombre
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_variante_by_id(variante_id: int) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT v.*, c.nombre as color, t.nombre as talla
        FROM variantes v
        LEFT JOIN colores c ON v.color_id = c.id
        LEFT JOIN tallas t ON v.talla_id = t.id
        WHERE v.id = ?
    """, (variante_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# ── Helpers for cascading autocomplete ────────────────────────────────────────

def get_color_by_nombre(nombre: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre FROM colores WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?))", (nombre,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_talla_by_nombre(nombre: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre FROM tallas WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?))", (nombre,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_colores_by_producto(producto_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT col.id, col.nombre, col.hex
        FROM variantes v
        JOIN colores col ON v.color_id = col.id
        WHERE v.producto_id = ? AND v.activo = 1
        ORDER BY col.nombre
    """, (producto_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_talles_by_producto_color(producto_id: int, color_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT tal.id, tal.nombre
        FROM variantes v
        JOIN tallas tal ON v.talla_id = tal.id
        WHERE v.producto_id = ? AND v.color_id = ? AND v.activo = 1
        ORDER BY tal.id
    """, (producto_id, color_id))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_variante_by_producto_color_talla(producto_id: int, color_id: int, talla_id: int) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT v.*, c.nombre as color, t.nombre as talla
        FROM variantes v
        LEFT JOIN colores c ON v.color_id = c.id
        LEFT JOIN tallas t ON v.talla_id = t.id
        WHERE v.producto_id = ? AND v.color_id = ? AND v.talla_id = ? AND v.activo = 1
    """, (producto_id, color_id, talla_id))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# ── Localidades ───────────────────────────────────────────────────────────────

def get_localidades() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre, provincia FROM localidades ORDER BY provincia, nombre")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def save_localidad(nombre: str, provincia: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO localidades (nombre, provincia) VALUES (?,?)",
        (nombre.strip(), provincia.strip())
    )
    localidad_id = c.lastrowid
    conn.commit()
    conn.close()
    return localidad_id


def get_or_create_localidad(nombre: str, provincia: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM localidades WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?))",
        (nombre,)
    )
    row = c.fetchone()
    if row:
        conn.close()
        return row["id"]
    c.execute(
        "INSERT INTO localidades (nombre, provincia) VALUES (?,?)",
        (nombre.strip(), provincia.strip())
    )
    localidad_id = c.lastrowid
    conn.commit()
    conn.close()
    return localidad_id


# ── Curvas pendientes ─────────────────────────────────────────────────────────

def save_curva_pendiente(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO curvas_pendientes
            (factura_id, factura_numero, producto_id, detalle_curva,
             es_surtida, color_id, variante_ids, cantidad, precio_total)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        data["factura_id"],
        data["factura_numero"],
        data["producto_id"],
        data["detalle_curva"],
        1 if data.get("es_surtida") else 0,
        data.get("color_id"),
        data["variante_ids"],
        data.get("cantidad", 1),
        data.get("precio_total", 0),
    ))
    pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid


def get_curvas_pendientes() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT cp.*, f.fecha, f.cliente_nombre
        FROM curvas_pendientes cp
        JOIN facturas f ON f.id = cp.factura_id
        WHERE cp.resuelta = 0
        ORDER BY f.id DESC, cp.id
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_curvas_por_factura(factura_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM curvas_pendientes
        WHERE factura_id = ? ORDER BY id
    """, (factura_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def resolver_curva(curva_id: int, distribucion: list[dict]) -> None:
    conn = get_connection()
    c = conn.cursor()
    for d in distribucion:
        delta = float(d.get("cantidad", 0))
        if delta > 0:
            c.execute(
                "UPDATE variantes SET stock_actual = MAX(0, stock_actual - ?) WHERE id = ?",
                (delta, d["variante_id"])
            )
    c.execute("UPDATE curvas_pendientes SET resuelta = 1 WHERE id = ?", (curva_id,))
    conn.commit()
    conn.close()


# ── User / Auth ─────────────────────────────────────────────────────────────────

def get_usuarios() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre, created_at FROM usuarios ORDER BY id")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    print(f"[DB] get_usuarios → {len(rows)} usuario(s): {[r['nombre'] for r in rows]}")
    return rows


def get_usuario_by_nombre(nombre: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE nombre = ?", (nombre,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def crear_usuario(nombre: str, pin: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO usuarios (nombre, pin) VALUES (?,?)", (nombre, pin))
    conn.commit()
    conn.close()


def verificar_pin(nombre: str, pin: str) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE nombre = ? AND pin = ?", (nombre, pin))
    row = c.fetchone()
    conn.close()
    if row:
        print(f"[DB] verificar_pin('{nombre}', '****') → OK (id={row['id']})")
    else:
        print(f"[DB] verificar_pin('{nombre}', '****') → NO MATCH")
    return dict(row) if row else None


def registrar_sesion(usuario_id: int) -> str:
    import uuid
    session_id = str(uuid.uuid4())
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sesiones (id, usuario_id, inicio) VALUES (?,?, datetime('now','localtime'))", (session_id, usuario_id))
    conn.commit()
    conn.close()
    print(f"[DB] registrar_sesion(usuario_id={usuario_id}) → session_id={session_id}")
    return session_id


def cerrar_sesion(session_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sesiones SET fin = datetime('now','localtime') WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def get_usuarios_conectados() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT s.id AS session_id, u.id AS usuario_id, u.nombre, s.inicio
        FROM sesiones s
        JOIN usuarios u ON u.id = s.usuario_id
        WHERE s.fin IS NULL
        ORDER BY s.inicio DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def registrar_actividad(usuario_id: int, tipo: str, referencia: str = "", descripcion: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO actividad (usuario_id, tipo, referencia, descripcion)
        VALUES (?,?,?,?)
    """, (usuario_id, tipo, referencia, descripcion))
    conn.commit()
    conn.close()


# ── Actividad reciente ──────────────────────────────────────────────────────────

def get_actividad_reciente(limit: int = 50) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT a.*, u.nombre AS usuario_nombre
        FROM actividad a
        LEFT JOIN usuarios u ON u.id = a.usuario_id
        ORDER BY a.id DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_actividad_reciente_days(days: int = 60, limit: int = 200) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT a.*, u.nombre AS usuario_nombre
        FROM actividad a
        LEFT JOIN usuarios u ON u.id = a.usuario_id
        WHERE a.created_at >= datetime('now', ? || ' days', 'localtime')
        ORDER BY a.id DESC LIMIT ?
    """, (f"-{days}", limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ── Facturas ────────────────────────────────────────────────────────────────────

def update_factura_envio(factura_id: int, envio_estado: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE facturas SET envio_estado = ? WHERE id = ?", (envio_estado, factura_id))
    conn.commit()
    conn.close()


def get_pagos_by_factura(numero_factura: str) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM cuenta_corriente WHERE referencia = ? AND tipo = 'Pago' ORDER BY id DESC",
        (numero_factura,)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def delete_factura(numero: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM facturas WHERE numero = ?", (numero,))
    factura = c.fetchone()
    if not factura:
        conn.close()
        return
    factura = dict(factura)
    c.execute("SELECT * FROM factura_items WHERE factura_id = ?", (factura["id"],))
    items = [dict(r) for r in c.fetchall()]
    for item in items:
        cantidad = float(item.get("cantidad") or 0)
        vid = item.get("variante_id")
        if vid:
            c.execute(
                "UPDATE variantes SET stock_actual = COALESCE(stock_actual,0) + ? WHERE id = ?",
                (cantidad, vid)
            )
        elif item.get("producto_id"):
            c.execute(
                "UPDATE productos SET stock_actual = MAX(0, COALESCE(stock_actual,0) + ?) WHERE id = ?",
                (cantidad, item["producto_id"])
            )
        cci = item.get("curva_color_ids")
        if cci and cantidad > 0:
            for cvid in cci.split(","):
                cvid = cvid.strip()
                if cvid:
                    c.execute(
                        "UPDATE variantes SET stock_actual = COALESCE(stock_actual,0) + ? WHERE id = ?",
                        (cantidad, int(cvid))
                    )
    c.execute("DELETE FROM factura_items WHERE factura_id = ?", (factura["id"],))
    c.execute("DELETE FROM facturas WHERE id = ?", (factura["id"],))
    # Eliminar señas y cobros huérfanos de movimientos_wasi
    c.execute(
        "DELETE FROM movimientos_wasi WHERE concepto LIKE ? AND tipo = 'Ingreso'",
        (f"%Factura {numero}%",)
    )
    conn.commit()
    conn.close()


# ── Cliente CC ─────────────────────────────────────────────────────────────────

def get_facturas_pendientes_cliente(cliente_nombre: str) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT f.id, f.numero, f.total, f.seña
        FROM facturas f
        WHERE f.cliente_nombre = ? AND f.estado != 'Pagado'
        ORDER BY f.id DESC
    """, (cliente_nombre,))
    rows = []
    for row in [dict(r) for r in c.fetchall()]:
        c.execute(
            "SELECT COALESCE(SUM(haber), 0) FROM cuenta_corriente WHERE referencia = ? AND tipo = 'Pago'",
            (row["numero"],)
        )
        pagado = float(c.fetchone()[0] or 0)
        deuda = max(0, row["total"] - float(row.get("seña", 0) or 0) - pagado)
        if deuda > 0:
            row["deuda"] = deuda
            rows.append(row)
    conn.close()
    return rows


def update_movimiento_cc(mov_id: int, monto: float, descripcion: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE cuenta_corriente SET haber = ?, descripcion = ? WHERE id = ?",
        (monto, descripcion, mov_id)
    )
    conn.commit()
    conn.close()


def delete_movimiento_cc(mov_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM cuenta_corriente WHERE id = ?", (mov_id,))
    conn.commit()
    conn.close()


def anular_cobro(cobro_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM cuenta_corriente WHERE id = ?", (cobro_id,))
    mov = c.fetchone()
    if not mov:
        conn.close()
        return
    mov = dict(mov)
    c.execute("DELETE FROM cuenta_corriente WHERE id = ?", (cobro_id,))
    if mov.get("referencia"):
        c.execute(
            "UPDATE facturas SET estado = 'Pendiente' WHERE numero = ?",
            (mov["referencia"],)
        )
    c.execute(
        "DELETE FROM movimientos_wasi WHERE concepto LIKE ? AND monto = ?",
        (f"%{mov.get('referencia', '')}%", float(mov.get("haber", 0) or 0))
    )
    conn.commit()
    conn.close()


# ── Stock movements ─────────────────────────────────────────────────────────────

def registrar_movimiento_stock(
    variante_id: int,
    tipo: str,
    referencia: str | None = None,
    cantidad: float = 0,
    motivo: str | None = None,
):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT stock_actual FROM variantes WHERE id = ?", (variante_id,))
    row = c.fetchone()
    stock_resultante = float(row[0]) if row else 0
    c.execute("""
        INSERT INTO movimientos_stock (variante_id, tipo, referencia, cantidad, stock_resultante, motivo)
        VALUES (?,?,?,?,?,?)
    """, (variante_id, tipo, referencia or "", cantidad, stock_resultante, motivo or ""))
    conn.commit()
    conn.close()


def get_movimientos_stock(variante_id: int = 0, producto_id: int = 0) -> list:
    conn = get_connection()
    c = conn.cursor()
    if producto_id:
        c.execute("""
            SELECT ms.* FROM movimientos_stock ms
            JOIN variantes v ON v.id = ms.variante_id
            WHERE v.producto_id = ?
            ORDER BY ms.id DESC
        """, (producto_id,))
    else:
        c.execute(
            "SELECT * FROM movimientos_stock WHERE variante_id = ? ORDER BY id DESC",
            (variante_id,)
        )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_movimientos_by_producto(producto_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT ms.* FROM movimientos_stock ms
        JOIN variantes v ON v.id = ms.variante_id
        WHERE v.producto_id = ?
        ORDER BY ms.id DESC
    """, (producto_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_curvas_by_producto(producto_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM curvas_pendientes WHERE producto_id = ? AND resuelta = 0 ORDER BY id",
        (producto_id,)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ── Proveedor CC ────────────────────────────────────────────────────────────────

def get_saldo_proveedor(proveedor_id: int) -> float:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT COALESCE(SUM(debe - haber), 0) FROM cuenta_corriente_proveedores WHERE proveedor_id = ?",
        (proveedor_id,)
    )
    saldo = float(c.fetchone()[0] or 0)
    conn.close()
    return saldo


def get_compras_by_proveedor(proveedor_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT c.id, c.numero, c.fecha, c.total,
               GROUP_CONCAT(ci.detalle, ', ') AS resumen
        FROM compras c
        LEFT JOIN compra_items ci ON ci.compra_id = c.id
        WHERE c.proveedor_id = ?
        GROUP BY c.id
        ORDER BY c.id DESC
    """, (proveedor_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def update_movimiento_proveedor(mov_id: int, monto: float, descripcion: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE cuenta_corriente_proveedores SET debe = ?, descripcion = ? WHERE id = ?",
        (monto, descripcion, mov_id)
    )
    conn.commit()
    conn.close()


def delete_movimiento_proveedor(mov_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM cuenta_corriente_proveedores WHERE id = ?", (mov_id,))
    conn.commit()
    conn.close()
