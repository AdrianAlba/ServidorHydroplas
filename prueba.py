import psycopg2
from datetime import datetime

# 1. Conexión a PostgreSQL
conn = psycopg2.connect(
    host="virginia-postgres.render.com",
    database="hydroplastdb_gv3z",
    user="hydroplastdb_gv3z_user",
    password="STKh0UAAMtUuPdzxnq2APPFG0yWbxuoS",
    port=5432
)

# 2. Crear cursor
cur = conn.cursor()

# 3. Crear tabla con todos los campos del JSON
cur.execute("""
CREATE TABLE IF NOT EXISTS mediciones (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    temperatura REAL,
    iluminancia REAL,
    nivel_agua REAL,
    led_rojo INTEGER,
    led_azul INTEGER,
    bomba_agua INTEGER
);
""")

# 4. Datos de ejemplo (usando el JSON proporcionado)
datos_sensor = {
    "timestamp": "2025-04-18T15:42:10Z",
    "temperatura": 25.87,
    "iluminancia": 810.35,
    "nivelAgua": 78.20,
    "ledRojo": 128,
    "ledAzul": 255,
    "bombaAgua": 200
}

# 5. Insertar datos
cur.execute("""
INSERT INTO mediciones (timestamp, temperatura, iluminancia, nivel_agua, led_rojo, led_azul, bomba_agua)
VALUES (%s, %s, %s, %s, %s, %s, %s)
""", (
    datetime.fromisoformat(datos_sensor["timestamp"].replace('Z', '+00:00')),
    datos_sensor["temperatura"],
    datos_sensor["iluminancia"],
    datos_sensor["nivelAgua"],
    datos_sensor["ledRojo"],
    datos_sensor["ledAzul"],
    datos_sensor["bombaAgua"]
))

# 6. Confirmar cambios y cerrar conexión
conn.commit()
cur.close()
conn.close()

print("✔️ Dato insertado correctamente en PostgreSQL.")
