import asyncio
import os
import websockets

clientes_conectados = {}  # websocket -> nombre

async def handler(websocket):
    print("🔌 Cliente conectado")
    
    try:
        # Recibir el primer mensaje como nombre o tipo de cliente
        nombre = await websocket.recv()
        clientes_conectados[websocket] = nombre
        print(f"👤 Cliente identificado como: {nombre}")

        # Procesar mensajes posteriores
        async for mensaje in websocket:
            print(f"📨 Mensaje de {nombre}: {mensaje}")

            await websocket.send(f"Echo de {nombre}: {mensaje}")

            # (Opcional) reenviar a los demás clientes
            # await asyncio.gather(*[
            #     cliente.send(f"📡 {nombre} dice: {mensaje}") 
            #     for cliente in clientes_conectados if cliente != websocket
            # ])

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
