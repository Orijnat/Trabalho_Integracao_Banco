
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import random

# Conexao com o MongoDB
cliente = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

banco = cliente["QualidadeAr"]
sensores = banco["Sensores"]
medicoes = banco["Medicoes"]

# Inicio do periodo de monitoramento (UTC)
inicio = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)

# 24 horas, com uma leitura a cada 5 minutos
quantidade_por_sensor = 24 * 60 // 5

# Gerador reproduzivel de dados simulados
random.seed(42)

try:
    cliente.admin.command("ping")

    lista_sensores = list(sensores.find().sort("_id", 1))

    if len(lista_sensores) < 6:
        raise ValueError(
            "Cadastre pelo menos 6 sensores antes de gerar as medicoes."
        )

    dados = []

    for sensor in lista_sensores:
        sensor_id = sensor["_id"]

        for indice in range(quantidade_por_sensor):
            horario = inicio + timedelta(minutes=5 * indice)

            medicao = {
                "sensor_id": sensor_id,
                "timestamp": horario,
                "pm25": round(random.uniform(10, 45), 2),
                "pm10": round(random.uniform(20, 80), 2),
                "co2": round(random.uniform(400, 900), 2),
                "temperatura": round(random.uniform(18, 32), 2),
                "umidade": round(random.uniform(40, 85), 2)
            }

            dados.append(medicao)

    # Limpa apenas as medicoes simuladas desse periodo
    fim = inicio + timedelta(hours=24)

    ids = [sensor["_id"] for sensor in lista_sensores]

    medicoes.delete_many({
        "sensor_id": {"$in": ids},
        "timestamp": {"$gte": inicio, "$lt": fim}
    })

    # Insere as novas medicoes
    medicoes.insert_many(dados)

    # Indice solicitado na atividade
    medicoes.create_index([
        ("sensor_id", 1),
        ("timestamp", -1)
    ])

    print("\nMEDICOES GERADAS COM SUCESSO!")
    print("--------------------------------------")
    print("Sensores:", len(lista_sensores))
    print("Horas monitoradas: 24")
    print("Intervalo entre medicoes: 5 minutos")
    print("Medicoes por sensor:", quantidade_por_sensor)
    print("Total de medicoes geradas:", len(dados))
    print("Registros na colecao:", medicoes.count_documents({}))

    print("\nQUANTIDADE POR SENSOR:")
    for sensor in lista_sensores:
        total = medicoes.count_documents({
            "sensor_id": sensor["_id"],
            "timestamp": {"$gte": inicio, "$lt": fim}
        })
        print(sensor["_id"], "-", total, "medicoes")

    print("\nEXEMPLO DE MEDICAO:")
    exemplo = medicoes.find_one({"sensor_id": "S001"})
    print(exemplo)

except Exception as erro:
    print("Erro:", erro)

finally:
    cliente.close()
