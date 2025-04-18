from pymongo import MongoClient

# Conectar a la base de datos MongoDB
try:
    client = MongoClient('mongodb://localhost:27017/')
    print("Conexión a MongoDB exitosa")
except Exception as e:
    print(f"Error al conectar a MongoDB: {e}")

# Crear el documento con los datos del sensor
datos_sensor = {
    "timestamp": "2025-04-18T15:42:10Z",
    "temperatura": 25.87,
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