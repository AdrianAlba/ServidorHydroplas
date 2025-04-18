import asyncio
import os
import websockets

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
    puerto = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", puerto):
        print(f"🌐 Servidor WebSocket escuchando en puerto {puerto}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
