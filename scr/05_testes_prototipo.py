"""
Teste do prototipo MongoDB + Redis (Etapa II, item 1.4)

Usa dados DIFERENTES dos dados reais:
  - sensores de teste (T001, T002, T003) em outras cidades
  - data diferente (03/11/2026, 14:00-15:00 UTC)
  - valores previsiveis, para conferir o resultado esperado

No final, remove tudo o que foi criado (MongoDB e Redis),
sem afetar os dados reais.
"""
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import redis
import unicodedata

mongo = MongoClient("mongodb://localhost:27017/",
                    serverSelectionTimeoutMS=5000)
banco = mongo["QualidadeAr"]
redis_db = redis.Redis(host="localhost", port=6379,
                       decode_responses=True)

INICIO = datetime(2026, 11, 3, 14, 0, tzinfo=timezone.utc)
FIM = INICIO + timedelta(hours=1)

passou = 0
falhou = 0


def checar(descricao, condicao):
    global passou, falhou
    if condicao:
        passou += 1
        print(f"  [OK]    {descricao}")
    else:
        falhou += 1
        print(f"  [FALHA] {descricao}")


def normalizar(nome):
    texto = unicodedata.normalize("NFKD", nome)
    return "".join(c for c in texto
                   if not unicodedata.combining(c)
                   ).lower().replace(" ", "_")


def media(valores):
    return sum(valores) / len(valores)


def proximo(a, b):
    return abs(float(a) - float(b)) <= 0.011


# ---------------------------------------------------------
# Dados de teste
# ---------------------------------------------------------
def novo_sensor(id_, cidade, lat, lon):
    return {
        "_id": id_, "modelo": "AirMonitor-TESTE",
        "descricao": "Sensor de teste",
        "localizacao": {"cidade": cidade, "uf": "SC",
                        "latitude": lat, "longitude": lon},
        "ativo": True,
        "grandezas": ["PM2.5", "PM10", "CO2",
                      "temperatura", "umidade"]
    }


SENSORES = [
    novo_sensor("T001", "Pinhalzinho", -26.8480, -52.9900),
    novo_sensor("T002", "Pinhalzinho", -26.8450, -52.9850),
    novo_sensor("T003", "São Carlos", -27.0770, -53.0050),
]
IDS = [s["_id"] for s in SENSORES]

# Quantidade de leituras e valores base por sensor.
# T001 e T002 tem quantidades diferentes (12 x 6) de proposito:
# a media da cidade deve ser ponderada pelas medicoes.
CONFIG = {
    "T001": {"qt": 12, "pm25": 10, "pm10": 20, "co2": 400,
             "temp": 20, "umid": 50},
    "T002": {"qt": 6, "pm25": 40, "pm10": 70, "co2": 700,
             "temp": 28, "umid": 80},
    "T003": {"qt": 12, "pm25": 25, "pm10": 45, "co2": 550,
             "temp": 23, "umid": 60},
}


def gerar_medicoes():
    docs = []
    for sid, c in CONFIG.items():
        for i in range(c["qt"]):
            docs.append({
                "sensor_id": sid,
                "timestamp": INICIO + timedelta(minutes=5 * i),
                "pm25": float(c["pm25"] + i),
                "pm10": float(c["pm10"] + 2 * i),
                "co2": float(c["co2"] + 10 * i),
                "temperatura": c["temp"] + 0.5 * i,
                "umidade": float(c["umid"] + i),
            })
    # Leituras FORA da janela (nao podem entrar no resumo):
    # exatamente no fim (limite exclusivo) e 5 min antes do inicio
    for ts in (FIM, INICIO - timedelta(minutes=5)):
        docs.append({"sensor_id": "T001", "timestamp": ts,
                     "pm25": 999.0, "pm10": 999.0, "co2": 9999.0,
                     "temperatura": 99.0, "umidade": 99.0})
    return docs


def esperado(sensor_ids):
    """Calcula o resultado esperado so com Python, sem o MongoDB."""
    linhas = [d for d in gerar_medicoes()
              if d["sensor_id"] in sensor_ids
              and INICIO <= d["timestamp"] < FIM]
    return {
        "qt_medicoes": len(linhas),
        "pm25_media": media([l["pm25"] for l in linhas]),
        "pm10_media": media([l["pm10"] for l in linhas]),
        "co2_media": media([l["co2"] for l in linhas]),
        "temperatura_media": media([l["temperatura"] for l in linhas]),
        "umidade_media": media([l["umidade"] for l in linhas]),
        "pm25_max": max(l["pm25"] for l in linhas),
        "pm10_max": max(l["pm10"] for l in linhas),
    }


# ---------------------------------------------------------
# Agregacao (mesmo pipeline do 04_agregar_dados.py,
# restrito aos sensores de teste)
# ---------------------------------------------------------
def pipeline(grupo):
    return [
        {"$match": {"sensor_id": {"$in": IDS},
                    "timestamp": {"$gte": INICIO, "$lt": FIM}}},
        {"$lookup": {"from": "Sensores", "localField": "sensor_id",
                     "foreignField": "_id", "as": "sensor"}},
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
            "pm10_max": {"$max": "$pm10"}}},
    ]


def gravar_redis(chave, resumo):
    dados = {
        "inicio_periodo": INICIO.isoformat(),
        "fim_periodo": FIM.isoformat(),
        **{k: str(round(v, 2)) if isinstance(v, float) else str(v)
           for k, v in resumo.items()}
    }
    redis_db.hset(chave, mapping=dados)


def conferir_hash(chave, exp):
    h = redis_db.hgetall(chave)
    checar(f"{chave} existe no Redis", bool(h))
    if not h:
        return
    checar(f"{chave}: qt_medicoes = {exp['qt_medicoes']}",
           int(h["qt_medicoes"]) == exp["qt_medicoes"])
    for campo in ("pm25_media", "pm10_media", "co2_media",
                  "temperatura_media", "umidade_media",
                  "pm25_max", "pm10_max"):
        checar(f"{chave}: {campo} = {exp[campo]:.2f} "
               f"(Redis: {h[campo]})",
               proximo(h[campo], exp[campo]))


# ---------------------------------------------------------
# Execucao
# ---------------------------------------------------------
def limpar():
    banco["Medicoes"].delete_many({"sensor_id": {"$in": IDS}})
    banco["Sensores"].delete_many({"_id": {"$in": IDS}})
    chaves = (redis_db.keys("qualidadear:sensor:T00*")
              + redis_db.keys("qualidadear:cidade:SC:pinhalzinho")
              + redis_db.keys("qualidadear:cidade:SC:sao_carlos"))
    if chaves:
        redis_db.delete(*chaves)


try:
    mongo.admin.command("ping")
    redis_db.ping()
    limpar()  # garante ambiente limpo

    print("=== PREPARACAO ===")
    banco["Sensores"].insert_many(SENSORES)
    docs = gerar_medicoes()
    banco["Medicoes"].insert_many(docs)
    print(f"Inseridos {len(SENSORES)} sensores e {len(docs)} medicoes de teste")

    # Teste 1: consulta por sensor e intervalo
    print("\n=== TESTE 1: consulta por sensor e intervalo ===")
    consulta = list(banco["Medicoes"].find({
        "sensor_id": "T001",
        "timestamp": {"$gte": INICIO,
                      "$lt": INICIO + timedelta(minutes=30)}
    }).sort("timestamp", 1))
    checar("T001 14:00-14:30 retorna 6 medicoes", len(consulta) == 6)
    checar("Resultado ordenado por timestamp",
           all(consulta[i]["timestamp"] < consulta[i + 1]["timestamp"]
               for i in range(len(consulta) - 1)))
    checar("Primeira medicao tem pm25 = 10.0",
           consulta and consulta[0]["pm25"] == 10.0)

    # Teste 2: janela horaria exclui medicoes fora do periodo
    print("\n=== TESTE 2: limites da janela horaria ===")
    total_janela = banco["Medicoes"].count_documents({
        "sensor_id": "T001",
        "timestamp": {"$gte": INICIO, "$lt": FIM}})
    checar("T001 tem 12 medicoes na janela (14 outras ficam de fora)",
           total_janela == 12)

    # Teste 3: resumo por sensor
    print("\n=== TESTE 3: resumo por sensor (Redis) ===")
    for r in banco["Medicoes"].aggregate(pipeline("$sensor_id")):
        sid = r.pop("_id")
        gravar_redis(f"qualidadear:sensor:{sid}", r)
    for sid in IDS:
        conferir_hash(f"qualidadear:sensor:{sid}", esperado([sid]))
    t1 = redis_db.hgetall("qualidadear:sensor:T001")
    checar("T001: pm25_max ignora leitura fora da janela (999)",
           float(t1["pm25_max"]) == 21.0)

    # Teste 4: resumo por cidade
    print("\n=== TESTE 4: resumo por cidade (Redis) ===")
    grupo = {"uf": "$sensor.localizacao.uf",
             "cidade": "$sensor.localizacao.cidade"}
    for r in banco["Medicoes"].aggregate(pipeline(grupo)):
        ident = r.pop("_id")
        chave = (f"qualidadear:cidade:{ident['uf']}:"
                 f"{normalizar(ident['cidade'])}")
        gravar_redis(chave, r)
    conferir_hash("qualidadear:cidade:SC:pinhalzinho",
                  esperado(["T001", "T002"]))
    conferir_hash("qualidadear:cidade:SC:sao_carlos",
                  esperado(["T003"]))

    # Teste 5: media global x media das medias (sensores com qt diferentes)
    print("\n=== TESTE 5: media ponderada da cidade ===")
    h = redis_db.hgetall("qualidadear:cidade:SC:pinhalzinho")
    media_medias = (float(redis_db.hget("qualidadear:sensor:T001", "pm25_media"))
                    + float(redis_db.hget("qualidadear:sensor:T002", "pm25_media"))) / 2
    print(f"  pm25 da cidade (global): {h['pm25_media']}")
    print(f"  media simples das medias dos sensores: {media_medias:.2f}")
    checar("Media global difere da media simples das medias",
           not proximo(h["pm25_media"], media_medias))

    # Teste 6: nome normalizado da chave
    print("\n=== TESTE 6: normalizacao do nome da cidade ===")
    checar("'São Carlos' -> chave sem acento e minuscula",
           redis_db.exists("qualidadear:cidade:SC:sao_carlos") == 1)

except Exception as erro:
    falhou += 1
    print("Erro durante os testes:", erro)

finally:
    try:
        limpar()
        print("\nDados de teste removidos do MongoDB e do Redis.")
    except Exception as erro:
        print("Nao foi possivel limpar os dados de teste:", erro)
    print("\n==============================")
    print(f"RESULTADO: {passou} testes OK, {falhou} falhas")
    print("==============================")
    mongo.close()
    redis_db.close()
