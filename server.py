import asyncio
import os
import websockets
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://adrianalba:tukIweCey0ZrOih9@hydroplastdb.rxpa4k9.mongodb.net/?retryWrites=true&w=majority&appName=hydroplastDB"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


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

    # Crear el documento con los datos del sensor
    datos_sensor = {
        "timestamp": "2025-04-18T15:42:10Z",
        "temperatura": 69,
        "iluminancia": 810.35,
        "nivelAgua": 78.20,
        "ledRojo": 128,
        "ledAzul": 255,
        "bombaAgua": 200
    }

    # Seleccionar la base de datos y colección
    db = client['hydroplastDB']  # Nombre de la base de datos
    coleccion = db['lecturas']   # Nombre de la colección

    # Insertar el documento
    try:
        resultado = coleccion.insert_one(datos_sensor)
        print(f"Documento insertado con ID: {resultado.inserted_id}")
    except Exception as e:
        print(f"Error al insertar documento: {e}")
    
    

    puerto = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", puerto):
        print(f"🌐 Servidor WebSocket escuchando en puerto {puerto}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())






