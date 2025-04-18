import asyncio
import os
import websockets

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
                # ✅ Enviar confirmación al clienteWeb
                ws_web = buscar_cliente_por_nombre("clienteWeb")
                if ws_web:
                    await ws_web.send(mensaje)
                    print(f"✅ Confirmación enviada a clienteWeb: {mensaje}")
                else:
                    await websocket.send("⚠️ clienteWeb no está conectado")

    except websockets.exceptions.ConnectionClosed:
        print(f"❌ Cliente {clientes_conectados.get(websocket, 'desconocido')} desconectado")
    finally:
        clientes_conectados.pop(websocket, None)

async def main():
    datos_sensor = {
        "timestamp": "2025-04-18T15:42:10Z",
        "temperatura": 69.87,
        "iluminancia": 69.35,
        "nivelAgua": 78.20,
        "ledRojo": 128,
        "ledAzul": 255,
        "bombaAgua": 200
    }
    
    cur.execute("""
        INSERT INTO mediciones (timestamp, temperatura, iluminancia, nivel_agua, led_rojo, led_azul, bomba_agua)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.fromisoformat(datos_sensor["timestamp"].replace('Z', '+00:00')),
            datos_sensor["temperatura"],
            datos_sensor["iluminancia"],
            datos_sensor["nivelAgua"],
            datos_sensor["ledRojo"],
            datos_sensor["ledAzul"],
            datos_sensor["bombaAgua"]
    ))

    # 6. Confirmar cambios y cerrar conexión
    conn.commit()
    cur.close()
    conn.close()

    print("✔️ Dato insertado correctamente en PostgreSQL.")


    puerto = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", puerto):
        print(f"🌐 Servidor WebSocket escuchando en puerto {puerto}")
        await asyncio.Future()

if __name__ == "__main__":



    asyncio.run(main())
