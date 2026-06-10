"""
stress_test.py
Inyecta 1000 registros de prueba en cada tabla para probar
el rendimiento de la UI y el botón "Cargar más".

Usage:
    python stress_test.py              # Poblar datos
    python stress_test.py --limpiar    # Limpiar datos de prueba
"""
import sys
import random
from datetime import datetime, timedelta
from db.database import get_connection

PREFIJO = "TEST-"
BATCH = 100

def generar_fecha(dias_atras=120):
    hoy = datetime.now()
    d = hoy - timedelta(days=random.randint(0, dias_atras))
    return d.replace(hour=random.randint(8, 18), minute=random.randint(0, 59))

def fmt_dt(dt):
    return dt.strftime("%d/%m/%Y %H:%M")

def fmt_date(dt):
    return dt.strftime("%d/%m/%Y")

def batches(n, size=BATCH):
    for i in range(0, n, size):
        yield i, min(i + size, n)

def poblar_datos():
    print("Generando 1000 registros de prueba por tabla...")
    conn = get_connection()
    c = conn.cursor()
    ts = int(datetime.now().timestamp() * 1000)

    # ── 1. Clientes (1000) ────────────────────────────────────────────────
    print("1/10  Clientes...")
    cliente_ids = []
    for i in range(1000):
        c.execute(
            "INSERT INTO clientes (nombre, domicilio, telefono) VALUES (?,?,?)",
            (f"{PREFIJO}Cliente {i}", f"Domicilio {i}", f"11-{random.randint(10000000, 99999999)}"),
        )
        cliente_ids.append(c.lastrowid)
    conn.commit()
    print(f"     {1000} clientes insertados")

    # ── 2. Productos + Variantes (1000 c/u) ───────────────────────────────
    print("2/10  Productos + Variantes...")
    prod_ids = []
    for i in range(1000):
        c.execute(
            "INSERT INTO productos (detalle, precio_unitario, stock_actual, stock_minimo, stock_reservado, tipo_origen) VALUES (?,?,?,?,?,?)",
            (f"{PREFIJO}Producto {i}", round(random.uniform(1000, 50000), 2),
             random.randint(10, 200), 5, 0, "proveedor"),
        )
        prod_ids.append(c.lastrowid)
    conn.commit()
    print(f"     {1000} productos insertados")

    # 1 variante por producto
    var_ids = []
    for pid in prod_ids:
        c.execute(
            "INSERT INTO variantes (producto_id, precio_unitario, stock_actual, stock_minimo, stock_reservado, precio_compra) VALUES (?,?,?,?,?,?)",
            (pid, round(random.uniform(1000, 50000), 2), random.randint(10, 200), 5, 0,
             round(random.uniform(500, 25000), 2)),
        )
        var_ids.append(c.lastrowid)
    conn.commit()
    print(f"     {1000} variantes insertadas")

    # ── 3. Facturas + Items (1000 facturas, ~2000 items) ──────────────────
    print("3/10  Facturas + Items...")
    factura_ids = []
    for i in range(1000):
        dt = generar_fecha()
        total = round(random.uniform(5000, 250000), 2)
        cli_id = random.choice(cliente_ids)
        cli_idx = cliente_ids.index(cli_id)
        cliente = f"{PREFIJO}Cliente {cli_idx}"
        num = f"{PREFIJO}F-{ts + i}"
        c.execute(
            "INSERT INTO facturas (numero, fecha, cliente_nombre, domicilio, telefono, envio, total, tipo_entrega, estado, seña, empresa_envio) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (num, fmt_date(dt), cliente, f"Domicilio {i}", f"11-{random.randint(10000000, 99999999)}",
             0, total, random.choice(["Retira", "Envio"]), "Pendiente",
             round(total * random.uniform(0, 0.3), 2) if random.random() < 0.3 else 0,
             random.choice(["", "Transporte X", "Correo Y"])),
        )
        fid = c.lastrowid
        factura_ids.append(fid)

        # 1-3 items por factura
        n_items = random.randint(1, 3)
        for _ in range(n_items):
            det = f"{PREFIJO}Producto {random.randint(0, 999)}"
            cant = random.randint(1, 5)
            pu = round(random.uniform(1000, 50000), 2)
            c.execute(
                "INSERT INTO factura_items (factura_id, cantidad, detalle, precio_unitario, total) VALUES (?,?,?,?,?)",
                (fid, cant, det, pu, round(cant * pu, 2)),
            )
    conn.commit()
    print(f"     {1000} facturas + items insertadas")

    # ── 4. Movimientos WASI (1000) ─────────────────────────────────────────
    print("4/10  Movimientos WASI...")
    rows = []
    for i in range(1000):
        dt = generar_fecha()
        tipo = "Ingreso" if i < 500 else "Egreso"
        monto = round(random.uniform(1000, 150000), 2)
        cat = "Factura / Venta" if tipo == "Ingreso" else random.choice(["Proveedores", "Sueldos", "Otro"])
        rows.append((fmt_dt(dt), tipo, cat, f"{PREFIJO}Mov {tipo} {i}", monto))
    for start, end in batches(1000):
        c.executemany(
            "INSERT INTO movimientos_wasi (fecha, tipo, categoria, concepto, monto) VALUES (?,?,?,?,?)",
            rows[start:end],
        )
    conn.commit()
    print(f"     {1000} movimientos WASI insertados")

    # ── 5. Cuenta Corriente (1000 movs de clientes) ───────────────────────
    print("5/10  Cuenta Corriente Clientes...")
    rows = []
    for i in range(1000):
        dt = generar_fecha()
        cli_id = random.choice(cliente_ids)
        debe = round(random.uniform(5000, 100000), 2)
        rows.append((cli_id, fmt_date(dt), "Compra", f"{PREFIJO}CC-{ts+i}",
                     f"{PREFIJO}Mov Cliente {i}", debe, 0, debe))
    for start, end in batches(1000):
        c.executemany(
            "INSERT INTO cuenta_corriente (cliente_id, fecha, tipo, referencia, descripcion, debe, haber, saldo) VALUES (?,?,?,?,?,?,?,?)",
            rows[start:end],
        )
    conn.commit()
    print(f"     {1000} movs de clientes insertados")

    # ── 6. Proveedores (1000) ─────────────────────────────────────────────
    print("6/10  Proveedores...")
    proveedor_ids = []
    for i in range(1000):
        c.execute(
            "INSERT INTO proveedores (nombre, telefono, domicilio) VALUES (?,?,?)",
            (f"{PREFIJO}Proveedor {i}", f"11-{random.randint(10000000, 99999999)}", f"Domicilio {i}"),
        )
        proveedor_ids.append(c.lastrowid)
    conn.commit()
    print(f"     {1000} proveedores insertados")

    # ── 7. Cuenta Corriente Proveedores (1000 movs) ───────────────────────
    print("7/10  Cuenta Corriente Proveedores...")
    rows = []
    for i in range(1000):
        dt = generar_fecha()
        prov_id = random.choice(proveedor_ids)
        haber = round(random.uniform(5000, 100000), 2)
        rows.append((prov_id, fmt_date(dt), "Compra", f"{PREFIJO}CCP-{ts+i}",
                     f"{PREFIJO}Mov Prov {i}", 0, haber, -haber))
    for start, end in batches(1000):
        c.executemany(
            "INSERT INTO cuenta_corriente_proveedores (proveedor_id, fecha, tipo, referencia, descripcion, debe, haber, saldo) VALUES (?,?,?,?,?,?,?,?)",
            rows[start:end],
        )
    conn.commit()
    print(f"     {1000} movs de proveedores insertados")

    # ── 8. Compras + Items (1000 compras, ~1500 items) ────────────────────
    print("8/10  Compras + Items...")
    for i in range(1000):
        dt = generar_fecha()
        prov_id = random.choice(proveedor_ids)
        prov_idx = proveedor_ids.index(prov_id)
        prov_nombre = f"{PREFIJO}Proveedor {prov_idx}"
        total = round(random.uniform(10000, 300000), 2)
        num = f"{PREFIJO}C-{ts + i}"
        c.execute(
            "INSERT INTO compras (numero, fecha, proveedor_id, proveedor_nombre, total, notas) VALUES (?,?,?,?,?,?)",
            (num, fmt_date(dt), prov_id, prov_nombre, total, f"{PREFIJO}Compra {i}"),
        )
        cid = c.lastrowid
        n_items = random.randint(1, 2)
        for _ in range(n_items):
            det = f"{PREFIJO}Producto {random.randint(0, 999)}"
            cant = random.randint(1, 10)
            pu = round(random.uniform(500, 25000), 2)
            c.execute(
                "INSERT INTO compra_items (compra_id, cantidad, detalle, precio_unitario, total) VALUES (?,?,?,?,?)",
                (cid, cant, det, pu, round(cant * pu, 2)),
            )
    conn.commit()
    print(f"     {1000} compras + items insertadas")

    # ── 9. Actividad Reciente (1000) ───────────────────────────────────────
    print("9/10  Actividad Reciente...")
    # Asegurar que existe usuario_id=1
    c.execute("SELECT id FROM usuarios WHERE id = 1")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (nombre, pin) VALUES (?,?)", ("admin", "0000"))
        conn.commit()
    tipos = ["factura", "compra", "pago", "ajuste_stock", "reduccion_stock"]
    rows = []
    for i in range(1000):
        dt = generar_fecha(60)
        t = random.choice(tipos)
        rows.append((1, t, f"{PREFIJO}Act-{ts+i}", f"{PREFIJO}Actividad {t} {i}"))
    for start, end in batches(1000):
        c.executemany(
            "INSERT INTO actividad_reciente (usuario_id, tipo, referencia, descripcion) VALUES (?,?,?,?)",
            rows[start:end],
        )
    conn.commit()
    print(f"     {1000} actividades insertadas")

    # ── 10. Movimientos Stock (1000) ───────────────────────────────────────
    print("10/10 Movimientos Stock...")
    tipos_stock = ["compra", "facturacion", "ajuste_manual"]
    for i in range(1000):
        vid = random.choice(var_ids)
        t = random.choice(tipos_stock)
        cant = random.randint(1, 20) * (1 if t == "compra" else -1)
        c.execute("SELECT stock_actual FROM variantes WHERE id = ?", (vid,))
        row = c.fetchone()
        sr = (row[0] if row else 50) + cant
        c.execute(
            "INSERT INTO movimientos_stock (variante_id, tipo, referencia, cantidad, stock_resultante) VALUES (?,?,?,?,?)",
            (vid, t, f"{PREFIJO}MS-{ts+i}", cant, max(0, sr)),
        )
    conn.commit()
    print(f"     {1000} movs de stock insertados")

    conn.close()
    print("\n Stress Test completado")
    print(" Abrí la app y probá el botón 'Cargar más' en cada vista")


def limpiar_datos():
    print("Limpiando datos de prueba...")
    conn = get_connection()
    c = conn.cursor()

    # Orden inverso al de inserción (respetar FKs)
    tablas = [
        ("movimientos_stock", "referencia", 0),
        ("actividad_reciente", "referencia", 0),
        ("compra_items", "detalle", 1),
        ("compras", "numero", 0),
        ("cuenta_corriente_proveedores", "referencia", 0),
        ("cuenta_corriente", "referencia", 0),
        ("movimientos_wasi", "concepto", 0),
        ("factura_items", "detalle", 1),
        ("facturas", "numero", 0),
        ("variantes", "id", 2),
        ("productos", "detalle", 0),
        ("proveedores", "nombre", 0),
        ("clientes", "nombre", 0),
    ]

    total = 0
    for tabla, col, modo in tablas:
        if modo == 0:
            sql = f"DELETE FROM {tabla} WHERE {col} LIKE '{PREFIJO}%'"
        elif modo == 1:
            sql = f"DELETE FROM {tabla} WHERE {col} LIKE '{PREFIJO}%'"
        elif modo == 2:
            # Delete variants linked to test products
            sql = f"DELETE FROM {tabla} WHERE producto_id IN (SELECT id FROM productos WHERE detalle LIKE '{PREFIJO}%')"
        c.execute(sql)
        total += c.rowcount
        print(f"  {tabla}: {c.rowcount} filas eliminadas")

    conn.commit()
    conn.close()
    print(f"\nLimpieza completa: {total} filas eliminadas")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--limpiar":
        limpiar_datos()
    else:
        print("Usá 'python stress_test.py --limpiar' para borrar los datos generados")
        print("-" * 50)
        poblar_datos()
