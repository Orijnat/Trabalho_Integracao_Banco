
from pymongo import MongoClient

# Conexao com o MongoDB
cliente = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

# Banco e colecao solicitados no trabalho
banco = cliente["QualidadeAr"]
sensores = banco["Sensores"]

# Cadastro dos seis sensores
dados_sensores = [
    {
        "_id": "S001",
        "modelo": "AirMonitor-200",
        "descricao": "Sensor ambiental do centro",
        "localizacao": {
            "cidade": "Chapecó",
            "uf": "SC",
            "latitude": -27.1009,
            "longitude": -52.6157
        },
        "ativo": True,
        "grandezas": [
            "PM2.5", "PM10", "CO2",
            "temperatura", "umidade"
        ]
    },
    {
        "_id": "S002",
        "modelo": "AirMonitor-200",
        "descricao": "Sensor ambiental da zona norte",
        "localizacao": {
            "cidade": "Chapecó",
            "uf": "SC",
            "latitude": -27.0748,
            "longitude": -52.6240
        },
        "ativo": True,
        "grandezas": [
            "PM2.5", "PM10", "CO2",
            "temperatura", "umidade"
        ]
    },
    {
        "_id": "S003",
        "modelo": "AirMonitor-200",
        "descricao": "Sensor ambiental do centro",
        "localizacao": {
            "cidade": "Xaxim",
            "uf": "SC",
            "latitude": -26.9610,
            "longitude": -52.5340
        },
        "ativo": True,
        "grandezas": [
            "PM2.5", "PM10", "CO2",
            "temperatura", "umidade"
        ]
    },
    {
        "_id": "S004",
        "modelo": "AirMonitor-200",
        "descricao": "Sensor ambiental da zona norte",
        "localizacao": {
            "cidade": "Xaxim",
            "uf": "SC",
            "latitude": -26.9580,
            "longitude": -52.5300
        },
        "ativo": True,
        "grandezas": [
            "PM2.5", "PM10", "CO2",
            "temperatura", "umidade"
        ]
    },
    {
        "_id": "S005",
        "modelo": "AirMonitor-200",
        "descricao": "Sensor ambiental do centro",
        "localizacao": {
            "cidade": "Concórdia",
            "uf": "SC",
            "latitude": -27.2340,
            "longitude": -52.0270
        },
        "ativo": True,
        "grandezas": [
            "PM2.5", "PM10", "CO2",
            "temperatura", "umidade"
        ]
    },
    {
        "_id": "S006",
        "modelo": "AirMonitor-200",
        "descricao": "Sensor ambiental da zona norte",
        "localizacao": {
            "cidade": "Concórdia",
            "uf": "SC",
            "latitude": -27.2300,
            "longitude": -52.0200
        },
        "ativo": True,
        "grandezas": [
            "PM2.5", "PM10", "CO2",
            "temperatura", "umidade"
        ]
    }
]

try:
    cliente.admin.command("ping")

    # Atualiza ou insere cada sensor
    # Evita duplicacoes ao executar novamente
    for sensor in dados_sensores:
        sensores.replace_one(
            {"_id": sensor["_id"]},
            sensor,
            upsert=True
        )

    print("Sensores cadastrados com sucesso!")

    print("\nTotal de sensores:",
          sensores.count_documents({}))

    print("\nSensores cadastrados:")

    for sensor in sensores.find():
        print(
            sensor["_id"],
            "-",
            sensor["localizacao"]["cidade"],
            "-",
            sensor["descricao"]
        )

except Exception as erro:
    print("Erro:", erro)

finally:
    cliente.close()
