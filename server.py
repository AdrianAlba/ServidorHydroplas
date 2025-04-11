import asyncio
import os
import websockets

clientes_conectados = set()

async def handler(websocket):
    print("🔌 Cliente conectado")
    clientes_conectados.add(websocket)
    try:
        async for mensaje in websocket:
            print(f"📨 Mensaje recibido: {mensaje}")
            await asyncio.gather(*[
                cliente.send(f"📡 {mensaje}") for cliente in clientes_conectados if cliente != websocket
            ])
    except websockets.exceptions.ConnectionClosed:
        print("❌ Cliente desconectado")
    finally:
        clientes_conectados.remove(websocket)

async def main():
    puerto = int(os.environ.get("PORT", 10000))  # Para Render o ejecución local
    async with websockets.serve(handler, "0.0.0.0", puerto):
        print(f"🌐 Servidor WebSocket escuchando en puerto {puerto}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
