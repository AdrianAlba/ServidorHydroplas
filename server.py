import asyncio
import os
import websockets

async def handler(websocket):
    print("🔌 Cliente conectado")
    try:
        async for mensaje in websocket:
            print(f"📨 Mensaje recibido: {mensaje}")
            await websocket.send(f"Echo: {mensaje}")  # Solo responde al cliente que envió
    except websockets.exceptions.ConnectionClosed:
        print("❌ Cliente desconectado")

async def main():
    puerto = int(os.environ.get("PORT", 10000))  # Render asigna el puerto en $PORT
    async with websockets.serve(handler, "0.0.0.0", puerto):
        print(f"🌐 Servidor WebSocket escuchando en puerto {puerto}")
        await asyncio.Future()  # Mantiene vivo el servidor

if __name__ == "__main__":
    asyncio.run(main())
