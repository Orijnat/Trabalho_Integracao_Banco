
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import redis
import unicodedata

# Conexao com os bancos
mongo = MongoClient("mongodb://localhost:27017/")
banco = mongo["QualidadeAr"]
redis_db = redis.Redis(
    host="localhost", port=6379,
    decode_responses=True
)

# Ultima hora dos dados simulados
inicio = datetime(2026, 10, 20, 23, 0, tzinfo=timezone.utc)
fim = inicio + timedelta(hours=1)

def normalizar(nome):
    texto = unicodedata.normalize("NFKD", nome)
    return "".join(
        letra for letra in texto
        if not unicodedata.combining(letra)
    ).lower().replace(" ", "_")

def calcular(grupo):
    return [
        {"$match": {
            "timestamp": {"$gte": inicio, "$lt": fim}
        }},
        {"$lookup": {
            "from": "Sensores",
            "localField": "sensor_id",
            "foreignField": "_id",
            "as": "sensor"
        }},
        {"$unwind": "$sensor"},
        {"$group": {
            "_id": grupo,
            "qt_medicoes": {"$sum": 1},
            "pm25_media": {"$avg": "$pm25"},
            "pm10_media": {"$avg": "$pm10"},
            "co2_media": {"$avg": "$co2"},
            "temperatura_media": {"$avg": "$temperatura"},
            "umidade_media": {"$avg": "$umidade"},
            "pm25_max": {"$max": "$pm25"},
            "pm10_max": {"$max": "$pm10"}
        }},
        {"$project": {
            "_id": 1,
            "qt_medicoes": 1,
            "pm25_media": 1,
            "pm10_media": 1,
            "co2_media": 1,
            "temperatura_media": 1,
            "umidade_media": 1,
            "pm25_max": 1,
            "pm10_max": 1
        }}
    ]

try:
    mongo.admin.command("ping")
    redis_db.ping()

    medicoes = banco["Medicoes"]

    # Resumos por sensor e por cidade
    grupos = [
        ("sensor", "$sensor_id"),
        ("cidade", {
            "uf": "$sensor.localizacao.uf",
            "cidade": "$sensor.localizacao.cidade"
        })
    ]

    for tipo, agrupamento in grupos:
        resultados = medicoes.aggregate(calcular(agrupamento))

        print(f"\n=== RESUMOS POR {tipo.upper()} ===")

        for resumo in resultados:
            identificador = resumo.pop("_id")

            if tipo == "sensor":
                chave = f"qualidadear:sensor:{identificador}"
            else:
                uf = identificador["uf"]
                cidade = normalizar(identificador["cidade"])
                chave = f"qualidadear:cidade:{uf}:{cidade}"

            dados = {
                "inicio_periodo": inicio.isoformat(),
                "fim_periodo": fim.isoformat(),
                **{
                    campo: str(round(valor, 2))
                    if isinstance(valor, float) else str(valor)
                    for campo, valor in resumo.items()
                }
            }

            redis_db.hset(chave, mapping=dados)

            print(f"\n{chave}")
            print(redis_db.hgetall(chave))

    print("\nIntegracao MongoDB + Redis concluida!")

except Exception as erro:
    print("Erro:", erro)

finally:
    mongo.close()
    redis_db.close()
