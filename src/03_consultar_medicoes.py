
from pymongo import MongoClient
from datetime import datetime

# Conexao com MongoDB
cliente = MongoClient("mongodb://localhost:27017/")
banco = cliente["QualidadeAr"]

# Sensor e periodo desejados
sensor = "S001"
inicio = datetime(2026, 10, 20, 11, 0)
fim = datetime(2026, 10, 20, 12, 0)

# Consulta das medicoes
medicoes = banco["Medicoes"].find({
    "sensor_id": sensor,
    "timestamp": {"$gte": inicio, "$lt": fim}
}).sort("timestamp", 1)

print(f"Medicoes do sensor {sensor}:")

total = 0

for m in medicoes:
    print(
        m["timestamp"],
        "| PM2.5:", m["pm25"],
        "| PM10:", m["pm10"],
        "| CO2:", m["co2"],
        "| Temperatura:", m["temperatura"],
        "| Umidade:", m["umidade"]
    )
    total += 1

print("Total de medicoes:", total)

cliente.close()
