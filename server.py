from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔌 Cliente conectado")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"📨 Recibido: {data}")
            await websocket.send_text(f"Echo: {data}")
    except:
        print("❌ Cliente desconectado")
