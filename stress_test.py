"""
stress_test.py
Script para inyectar y limpiar datos de prueba en WASI.
Ideal para probar la pantalla de Métricas.
"""
import sys
import random
from datetime import datetime, timedelta
from db.database import get_connection

def generar_fecha_aleatoria(dias_atras):
    """Genera una fecha aleatoria entre hoy y 'dias_atras' hacia el pasado."""
    hoy = datetime.now()
    dias_restar = random.randint(0, dias_atras)
    fecha_random = hoy - timedelta(days=dias_restar)
    hora = random.randint(8, 18)
    minuto = random.randint(0, 59)
    return fecha_random.replace(hour=hora, minute=minuto)

def poblar_datos():
    print("🚀 Iniciando Stress Test...")
    conn = get_connection()
    c = conn.cursor()
    
    timestamp_base = int(datetime.now().timestamp() * 1000)
    
    # 1. Generar 300 Facturas en los últimos 4 meses (120 días)
    print("Generando 300 facturas aleatorias...")
    for i in range(300):
        dt = generar_fecha_aleatoria(120)
        fecha_str = dt.strftime("%d/%m/%Y")
        total = round(random.uniform(5000, 250000), 2)
        numero = f"TEST-F-{timestamp_base + i}" # Prefijo TEST para poder borrarlo luego
        
        c.execute("""
            INSERT INTO facturas (numero, fecha, cliente_nombre, total, estado)
            VALUES (?, ?, ?, ?, ?)
        """, (numero, fecha_str, f"Cliente Test {i}", total, "Entregado"))

    # 2. Generar 400 Ingresos en la Cuenta WASI
    print("Generando 400 ingresos aleatorios...")
    for i in range(400):
        dt = generar_fecha_aleatoria(120)
        fecha_str = dt.strftime("%d/%m/%Y %H:%M")
        monto = round(random.uniform(2000, 150000), 2)
        
        c.execute("""
            INSERT INTO movimientos_wasi (fecha, tipo, categoria, concepto, monto)
            VALUES (?, 'Ingreso', 'Factura / Venta', '[Test] Cobro simulado', ?)
        """, (fecha_str, monto))

    # 3. Generar 200 Egresos en la Cuenta WASI
    print("Generando 200 egresos aleatorios...")
    for i in range(200):
        dt = generar_fecha_aleatoria(120)
        fecha_str = dt.strftime("%d/%m/%Y %H:%M")
        monto = round(random.uniform(1000, 80000), 2)
        categoria = random.choice(["Proveedores", "Sueldos", "Otro"])
        
        c.execute("""
            INSERT INTO movimientos_wasi (fecha, tipo, categoria, concepto, monto)
            VALUES (?, 'Egreso', ?, '[Test] Gasto simulado', ?)
        """, (fecha_str, categoria, monto))

    conn.commit()
    conn.close()
    print("✅ ¡Stress Test completado! Abre WASI y revisa la pestaña de Métricas.")


def limpiar_datos():
    print("🧹 Limpiando datos de prueba...")
    conn = get_connection()
    c = conn.cursor()
    
    # Borrar solo lo que creamos con este script
    c.execute("DELETE FROM facturas WHERE numero LIKE 'TEST-F-%'")
    filas_facturas = c.rowcount
    
    c.execute("DELETE FROM movimientos_wasi WHERE concepto LIKE '[Test]%'")
    filas_wasi = c.rowcount
    
    conn.commit()
    conn.close()
    print(f"✅ Limpieza exitosa. Se eliminaron {filas_facturas} facturas y {filas_wasi} movimientos WASI.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--limpiar":
        limpiar_datos()
    else:
        print("Puedes usar 'python stress_test.py --limpiar' para borrar los datos generados.")
        print("-" * 50)
        poblar_datos()