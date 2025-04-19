import asyncio
import os
import json
from aiohttp import web
import psycopg2
from datetime import datetime

# Conexión a PostgreSQL
conn = psycopg2.connect(
    host="virginia-postgres.render.com",
    database="hydroplastdb",
    user="hydroplastdb_user",
    password="nPLtrVhiuMDIO1KTIBtQmtSTfO4cJPK9",
    port=5432
)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS mediciones (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    temperatura REAL,
    iluminancia REAL,
    nivel_agua REAL,
    led_rojo INTEGER,
    led_azul INTEGER,
    bomba_agua INTEGER
);
""")

clientes_conectados = {}  # websocket -> nombre
clientes_por_nombre = {}  # nombre -> websocket

def buscar_cliente_por_nombre(nombre):
    for ws, cliente in clientes_conectados.items():
        if cliente == nombre:
            return ws
    return None

async def guardar_datos_sensor(datos):
    try:
        cur.execute("""
            INSERT INTO mediciones (timestamp, temperatura, iluminancia, nivel_agua, led_rojo, led_azul, bomba_agua)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.fromisoformat(datos["timestamp"].replace('Z', '+00:00')),
            datos["temperatura"],
            datos["iluminancia"],
            datos["nivelAgua"],
            datos["ledRojo"],
            datos["ledAzul"],
            datos["bombaAgua"]
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error guardando datos: {e}")
        return False

# --- HTTP endpoints ---
async def get_last_reading(request):
    try:
        cur.execute("""
            SELECT * FROM mediciones 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            return web.json_response({
                'timestamp': row[1].isoformat(),
                'temperatura': row[2],
                'iluminancia': row[3],
                'nivel_agua': row[4],
                'led_rojo': row[5],
                'led_azul': row[6],
                'bomba_agua': row[7]
            })
        return web.json_response({'error': 'No data found'}, status=404)
    except Exception as e:
        print(f"Error getting last reading: {e}")
        return web.json_response({'error': str(e)}, status=500)

# --- WebSocket handler ---
async def ws_handler(request):
    ws = web.WebSocketResponse(protocols=["arduino"])
    await ws.prepare(request)

    print("🔌 Cliente conectado por WebSocket")
    try:
        nombre = await ws.receive_str()
        clientes_por_nombre[nombre] = ws  # Guardar por nombre
        print(f"👤 Cliente identificado como: {nombre}")

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                mensaje = msg.data
                print(f"📨 Mensaje de {nombre}: {mensaje}")

                if nombre == "clienteWeb":
                    if "hydroplast" in clientes_por_nombre:
                        hydroplast_ws = clientes_por_nombre["hydroplast"]
                        await hydroplast_ws.send_str(mensaje)
                        print(f"➡️ Reenviado a hydroplast: {mensaje}")
                    else:
                        await ws.send_str("⚠️ hydroplast no está conectado")

                elif nombre == "hydroplast":
                    try:
                        datos = json.loads(mensaje)
                        if await guardar_datos_sensor(datos):
                            print("✅ Datos guardados en PostgreSQL")
                        if "clienteWeb" in clientes_por_nombre:
                            client_web_ws = clientes_por_nombre["clienteWeb"]
                            await client_web_ws.send_str(mensaje)
                            print(f"✅ Datos reenviados a clienteWeb")
                        else:
                            await ws.send_str("⚠️ clienteWeb no está conectado")
                    except json.JSONDecodeError:
                        print("❌ Error: Mensaje no es JSON válido")
                        await ws.send_str("❌ Error: Formato JSON inválido")
                    except Exception as e:
                        print(f"❌ Error procesando mensaje: {e}")
                        await ws.send_str("❌ Error procesando datos")
            elif msg.type == web.WSMsgType.ERROR:
                print(f'ws connection closed with exception {ws.exception()}')
    finally:
        # Eliminar de la estructura correcta
        if nombre in clientes_por_nombre and clientes_por_nombre[nombre] == ws:
            del clientes_por_nombre[nombre]
        print(f"❌ Cliente {nombre} desconectado")
    return ws
# --- Main app setup ---
app = web.Application()
app.router.add_get('/ws', ws_handler)  # WebSocket endpoint
app.router.add_get('/api/last-reading', get_last_reading)  # HTTP endpoint

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)


