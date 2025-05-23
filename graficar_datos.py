import requests
import matplotlib.pyplot as plt
from datetime import datetime

# URL de la API
url = 'https://servidorhydroplas.onrender.com/api/data-by-date-range'
params = {
    'start_date': '2025-04-26',
    'end_date': '2025-04-27',
    'column': 'bombaAgua'  # Cambia esto al nombre de la columna que deseas graficar
}


# Realizar la petición a la API
respuesta = requests.get(url, params=params)

# Verificar que la respuesta sea exitosa
if respuesta.status_code == 200:
    datos = respuesta.json()

    # Procesar los datos
    timestamps = [datetime.fromisoformat(item['timestamp']) for item in datos]
    valores_bomba = [item[params['column']] for item in datos]

    # Crear la gráfica
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, valores_bomba, marker='o', linestyle='-', color='blue')
    plt.title('Estado de la Bomba de Agua en el Tiempo')
    plt.xlabel('Fecha y Hora')
    plt.ylabel('Estado de la Bomba (0=Apagada, 1=Encendida)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Mostrar la gráfica
    plt.show()

else:
    print(f'Error al obtener los datos: {respuesta.status_code}')
