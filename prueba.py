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