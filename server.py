import asyncio
import os
import json
from aiohttp import web
import psycopg2
from datetime import datetime
import aiohttp_cors

# ... (tu código de conexión a la DB y funciones existentes) ...
conn = psycopg2.connect(
    host="virginia-postgres.render.com",
    database="hydroplastdb_gv3z",
    user="hydroplastdb_gv3z_user",
    password="STKh0UAAMtUuPdzxnq2APPFG0yWbxuoS",
    port=5432
)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS mediciones (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    temperatura REAL,
    iluminancia REAL,
    nivelagua REAL,
    ledrojo INTEGER,
    ledazul INTEGER,
    bombaagua INTEGER,
    particulasagua INTEGER
);
""")
conn.commit() # Asegúrate de hacer commit después de crear la tabla

clientes_conectados = {}
clientes_por_nombre = {}
last_db_write_time = None # Variable to track the last DB write time

def buscar_cliente_por_nombre(nombre):
    for ws, cliente in clientes_conectados.items():
        if cliente == nombre:
            return ws
    return None

async def guardar_datos_sensor(datos):
    try:
        cur.execute("""
            INSERT INTO mediciones (timestamp, temperatura, iluminancia, nivelagua, ledrojo, ledazul, bombaagua, particulasagua)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.fromisoformat(datos["timestamp"].replace('Z', '+00:00')),
            datos["temperatura"],
            datos["iluminancia"],
            datos.get("nivelAgua", datos.get("nivelagua")),
            datos.get("ledRojo", datos.get("ledrojo")),
            datos.get("ledAzul", datos.get("ledazul")),
            datos.get("bombaAgua", datos.get("bombaagua")),
            datos.get("particulasAgua", datos.get("particulasagua", 0))  # Default a 0 si no existe
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error guardando datos: {e}")
        conn.rollback()
        return False

# --- HTTP endpoints ---
async def get_last_reading(request):
    try:
        cur.execute("""
            SELECT timestamp, temperatura, iluminancia, nivelagua, ledrojo, ledazul, bombaagua, particulasagua
            FROM mediciones
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            return web.json_response({
                'timestamp': row[0].isoformat(),
                'temperatura': row[1],
                'iluminancia': row[2],
                'nivelAgua': row[3],
                'ledRojo': row[4],
                'ledAzul': row[5],
                'bombaAgua': row[6],
                'particulasAgua': row[7]
            })
        return web.json_response({'error': 'No data found'}, status=404)
    except Exception as e:
        print(f"Error getting last reading: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_history(request):
    try:
        limit = int(request.query.get('limit', 10))
        if limit > 100:
            limit = 100
            
        cur.execute("""
            SELECT timestamp, temperatura, iluminancia, nivelagua, ledrojo, ledazul, bombaagua, particulasagua
            FROM mediciones
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))
        
        rows = cur.fetchall()
        
        if rows:
            result = []
            for row in rows:
                result.append({
                    'timestamp': row[0].isoformat(),
                    'temperatura': row[1],
                    'iluminancia': row[2],
                    'nivelAgua': row[3],
                    'ledRojo': row[4],
                    'ledAzul': row[5],
                    'bombaAgua': row[6],
                    'particulasAgua': row[7]
                })
            return web.json_response(result)
        return web.json_response({'error': 'No data found'}, status=404)
    except ValueError:
        return web.json_response({'error': 'Invalid limit parameter'}, status=400)
    except Exception as e:
        print(f"Error getting history: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_data_by_date_range(request):
    try:
        # Obtener parámetros de la consulta
        start_date = request.query.get('start_date')
        end_date = request.query.get('end_date')
        column = request.query.get('column', 'temperatura')  # Por defecto usamos temperatura
        
        # Validar parámetros
        if not start_date or not end_date:
            return web.json_response({
                'error': 'Se requieren los parámetros start_date y end_date'
            }, status=400)
        
        # Validar que la columna solicitada exista en la tabla
        valid_columns = ['temperatura', 'iluminancia', 'nivelAgua', 'ledRojo', 'ledAzul', 'bombaAgua','particulasAgua']
        print(column);
        if column not in valid_columns:
            return web.json_response({
                'error': f'Columna inválida. Opciones válidas: {", ".join(valid_columns)}'
            }, status=400)
        
        # Formatear fechas con hora completa
        start_datetime = f"{start_date} 00:00:00"
        end_datetime = f"{end_date} 23:59:59"
        
        # Construir consulta SQL de forma segura
        query = f"""
            SELECT timestamp, {column}
            FROM mediciones
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY timestamp
        """
        
        cur.execute(query, (start_datetime, end_datetime))
        rows = cur.fetchall()
        
        if rows:
            result = []
            for row in rows:
                result.append({
                    'timestamp': row[0].isoformat(),
                    column: row[1]
                })
            return web.json_response(result)
        
        return web.json_response([], status=200)  # Devuelve una lista vacía si no hay datos
        
    except Exception as e:
        print(f"Error en get_data_by_date_range: {e}")
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

                elif nombre == "hydroplastDisplay": # New condition for hydroplastDisplay
                    if "hydroplast" in clientes_por_nombre:
                        hydroplast_ws = clientes_por_nombre["hydroplast"]
                        await hydroplast_ws.send_str(mensaje)
                        print(f"➡️ Mensaje de hydroplastDisplay reenviado a hydroplast: {mensaje}")
                    else:
                        await ws.send_str("⚠️ hydroplast no está conectado para recibir el mensaje.")

                elif nombre == "hydroplast":
                    global last_db_write_time # Use the global variable
                    try:
                        datos = json.loads(mensaje) # Parse message to 'datos' dict

                        # Always forward the raw message to other clients
                        if "clienteWeb" in clientes_por_nombre:
                            client_web_ws = clientes_por_nombre["clienteWeb"]
                            await client_web_ws.send_str(mensaje) # Forward original JSON string
                            print(f"✅ Datos reenviados a clienteWeb")
                        
                        if "hydroplastDisplay" in clientes_por_nombre:
                            hydroplast_display_ws = clientes_por_nombre["hydroplastDisplay"]
                            await hydroplast_display_ws.send_str(mensaje) # Forward original JSON string
                            print(f"✅ Datos reenviados a hydroplastDisplay")

                        # Logic to save to DB every 5 seconds
                        current_time = datetime.now()
                        should_save_to_db = False

                        if last_db_write_time is None or \
                           (current_time - last_db_write_time).total_seconds() >= 5:
                            should_save_to_db = True
                        
                        if should_save_to_db:
                            if await guardar_datos_sensor(datos): # Use parsed 'datos' for saving
                                print("✅ Datos guardados en PostgreSQL")
                                last_db_write_time = current_time # Update last write time
                            else:
                                print("❌ Error al guardar datos en PostgreSQL")
                        else:
                            print("ℹ️ Datos de hydroplast recibidos, en espera del intervalo de 5s para guardar.")

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

history_resource = cors.add(app.router.add_resource("/api/history"))
cors.add(history_resource.add_route("GET", get_history))

# Añadir la nueva ruta a la aplicación
date_range_resource = cors.add(app.router.add_resource("/api/data-by-date-range"))
cors.add(date_range_resource.add_route("GET", get_data_by_date_range))


if __name__ == "__main__":
    # Usar variable de entorno PORT o default a 10000 como ya tienes
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Server starting on host 0.0.0.0 port {port}")
    web.run_app(app, host="0.0.0.0", port=port)

# Asegúrate de cerrar la conexión a la DB al terminar (aunque run_app lo bloquea)
# Podrías usar señales de limpieza si fuera necesario.
# cur.close()
# conn.close()