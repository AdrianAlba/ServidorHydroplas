import asyncio
import os
import websockets
import json

import psycopg2
from datetime import datetime

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

# 🔎 Función auxiliar para encontrar el WebSocket de un cliente por nombre
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

async def handler(websocket):
    print("🔌 Cliente conectado")
    
    try:
        # Recibir el primer mensaje como nombre
        nombre = await websocket.recv()
        clientes_conectados[websocket] = nombre
        print(f"👤 Cliente identificado como: {nombre}")

        async for mensaje in websocket:
            print(f"📨 Mensaje de {nombre}: {mensaje}")

            if nombre == "clienteWeb":
                # 🔁 Redirigir mensaje a hydroplast
                ws_hydro = buscar_cliente_por_nombre("hydroplast")
                if ws_hydro:
                    await ws_hydro.send(mensaje)
                    print(f"➡️ Reenviado a hydroplast: {mensaje}")
                else:
                    await websocket.send("⚠️ hydroplast no está conectado")

            elif nombre == "hydroplast":
                try:
                    # Convertir mensaje a JSON
                    datos = json.loads(mensaje)
                    
                    # Guardar en base de datos
                    if await guardar_datos_sensor(datos):
                        print("✅ Datos guardados en PostgreSQL")
                    
                    # Enviar a clienteWeb
                    ws_web = buscar_cliente_por_nombre("clienteWeb")
                    if ws_web:
                        await ws_web.send(mensaje)
                        print(f"✅ Datos reenviados a clienteWeb")
                    else:
                        await websocket.send("⚠️ clienteWeb no está conectado")
                
                except json.JSONDecodeError:
                    print("❌ Error: Mensaje no es JSON válido")
                    await websocket.send("❌ Error: Formato JSON inválido")
                except Exception as e:
                    print(f"❌ Error procesando mensaje: {e}")
                    await websocket.send("❌ Error procesando datos")

    except websockets.exceptions.ConnectionClosed:
        print(f"❌ Cliente {clientes_conectados.get(websocket, 'desconocido')} desconectado")
    finally:
        clientes_conectados.pop(websocket, None)

async def main():
    puerto = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", puerto):
        print(f"🌐 Servidor WebSocket escuchando en puerto {puerto}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
