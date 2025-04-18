import asyncio
import os
import websockets
import json
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Configuración MongoDB
uri = "mongodb+srv://adrianalba:tukIweCey0ZrOih9@hydroplastdb.rxpa4k9.mongodb.net/?retryWrites=true&w=majority&appName=hydroplastDB"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['hydroplastDB']
coleccion = db['lecturas']

clientes_conectados = {}  # websocket -> nombre

# 🔎 Función auxiliar para encontrar el WebSocket de un cliente por nombre
def buscar_cliente_por_nombre(nombre):
    for ws, cliente in clientes_conectados.items():
        if cliente == nombre:
            return ws
    return None

async def guardar_datos_mongodb(datos):
    try:
        resultado = coleccion.insert_one(datos)
        print(f"📝 Datos guardados en MongoDB con ID: {resultado.inserted_id}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar en MongoDB: {e}")
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
                    # Intentar parsear el mensaje como JSON
                    datos_sensor = json.loads(mensaje)
                    
                    # Guardar en MongoDB
                    guardado = await guardar_datos_mongodb(datos_sensor)
                    
                    # Enviar confirmación al clienteWeb
                    ws_web = buscar_cliente_por_nombre("clienteWeb")
                    if ws_web:
                        # Si se guardó correctamente, reenviar los datos
                        if guardado:
                            await ws_web.send(mensaje)
                            print(f"✅ Datos reenviados a clienteWeb y guardados en MongoDB")
                        else:
                            await ws_web.send("❌ Error al guardar datos")
                    else:
                        await websocket.send("⚠️ clienteWeb no está conectado")
                
                except json.JSONDecodeError:
                    print("❌ Error: El mensaje no es un JSON válido")
                    await websocket.send("❌ Error: Formato JSON inválido")

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
    # Verificar conexión MongoDB
    try:
        client.admin.command('ping')
        print("✅ Conexión exitosa a MongoDB")
    except Exception as e:
        print(f"❌ Error conectando a MongoDB: {e}")
    
    asyncio.run(main())
