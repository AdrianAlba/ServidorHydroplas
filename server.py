from fastapi import FastAPI, WebSocket
import uvicorn
import os

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render asigna este automáticamente
    uvicorn.run("main:app", host="0.0.0.0", port=port)
