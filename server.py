import asyncio
import os
import json
from aiohttp import web
import psycopg2
from datetime import datetime
import aiohttp_cors # <--- Importar aiohttp-cors

# ... (tu código de conexión a la DB y funciones existentes) ...
conn = psycopg2.connect(
    host="virginia-postgres.render.com",
    database="hydroplastdb",
    user="hydroplastdb_user",
    password="nPLtrVhiuMDIO1KTIBtQmtSTfO4cJPK9", # Considera usar variables de entorno para la contraseña
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
conn.commit() # Asegúrate de hacer commit después de crear la tabla

clientes_conectados = {}
clientes_por_nombre = {}

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
            datos.get("nivelAgua", datos.get("nivel_agua")), # Aceptar ambas claves por si acaso
            datos.get("ledRojo", datos.get("led_rojo")),
            datos.get("ledAzul", datos.get("led_azul")),
            datos.get("bombaAgua", datos.get("bomba_agua"))
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error guardando datos: {e}")
        conn.rollback() # Es buena práctica hacer rollback en caso de error
        return False

# --- HTTP endpoints ---
async def get_last_reading(request):
    try:
        cur.execute("""
            SELECT timestamp, temperatura, iluminancia, nivel_agua, led_rojo, led_azul, bomba_agua
            FROM mediciones
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            # Asegúrate de que los nombres de las claves coincidan con lo que espera el frontend
            # O ajusta el frontend para que coincida con esto
            return web.json_response({
                'timestamp': row[0].isoformat(),
                'temperatura': row[1],
                'iluminancia': row[2],
                'nivel_agua': row[3], # Nota: frontend espera nivelAgua
                'led_rojo': row[4],   # Nota: frontend espera ledRojo
                'led_azul': row[5],   # Nota: frontend espera ledAzul
                'bomba_agua': row[6]  # Nota: frontend espera bombaAgua
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
    nombre = "desconocido" # Inicializar nombre
    try:
        nombre = await ws.receive_str()
        clientes_por_nombre[nombre] = ws
        print(f"👤 Cliente identificado como: {nombre}")

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                mensaje = msg.data
                print(f"📨 Mensaje de {nombre}: {mensaje}")

                if nombre == "clienteWeb":
                    hydroplast_ws = clientes_por_nombre.get("hydroplast")
                    if hydroplast_ws:
                        await hydroplast_ws.send_str(mensaje)
                        print(f"➡️ Reenviado a hydroplast: {mensaje}")
                    else:
                        await ws.send_str("⚠️ hydroplast no está conectado")

                elif nombre == "hydroplast":
                    try:
                        datos = json.loads(mensaje)
                        if await guardar_datos_sensor(datos):
                            print("✅ Datos guardados en PostgreSQL")

                        # Reenviar datos formateados correctamente para la web si está conectada
                        client_web_ws = clientes_por_nombre.get("clienteWeb")
                        if client_web_ws:
                            # Crear un diccionario con las claves que espera el frontend
                            datos_para_web = {
                                'timestamp': datos["timestamp"],
                                'temperatura': datos["temperatura"],
                                'iluminancia': datos["iluminancia"],
                                'nivelAgua': datos.get("nivelAgua", datos.get("nivel_agua")),
                                'ledRojo': datos.get("ledRojo", datos.get("led_rojo")),
                                'ledAzul': datos.get("ledAzul", datos.get("led_azul")),
                                'bombaAgua': datos.get("bombaAgua", datos.get("bomba_agua"))
                            }
                            await client_web_ws.send_str(json.dumps(datos_para_web))
                            print(f"✅ Datos reenviados a clienteWeb")
                        else:
                            # No enviar mensaje de error a hydroplast, podría confundir al ESP32/Arduino
                            print("⚠️ clienteWeb no está conectado para reenviar datos")

                    except json.JSONDecodeError:
                        print("❌ Error: Mensaje no es JSON válido")
                        # No enviar mensaje de error a hydroplast
                    except Exception as e:
                        print(f"❌ Error procesando mensaje de hydroplast: {e}")
                        # No enviar mensaje de error a hydroplast
            elif msg.type == web.WSMsgType.ERROR:
                print(f'ws connection closed with exception {ws.exception()}')
    finally:
        if nombre in clientes_por_nombre and clientes_por_nombre[nombre] == ws:
            del clientes_por_nombre[nombre]
        print(f"❌ Cliente {nombre} desconectado")
    return ws

# --- Main app setup ---
app = web.Application()

# Configurar CORS
cors = aiohttp_cors.setup(app, defaults={
    # Permitir todos los orígenes. Para producción, podrías restringirlo
    # a tu dominio específico o a `http://localhost:xxxx` (el puerto que use Expo Web)
    "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*", # Permitir cualquier header (incluyendo Content-Type, etc.)
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"] # Permitir métodos necesarios
        )
})

# Añadir rutas y aplicar CORS a la ruta HTTP
app.router.add_get('/ws', ws_handler) # WebSocket no necesita CORS de esta manera usualmente

# Registrar la ruta HTTP y envolverla con CORS
resource = cors.add(app.router.add_resource("/api/last-reading"))
cors.add(resource.add_route("GET", get_last_reading))

if __name__ == "__main__":
    # Usar variable de entorno PORT o default a 10000 como ya tienes
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Server starting on host 0.0.0.0 port {port}")
    web.run_app(app, host="0.0.0.0", port=port)

# Asegúrate de cerrar la conexión a la DB al terminar (aunque run_app lo bloquea)
# Podrías usar señales de limpieza si fuera necesario.
# cur.close()
# conn.close()