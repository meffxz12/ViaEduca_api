import requests
from models import Instituicao
from sqlalchemy.orm import Session

BASE = "https://apigw-proxy.capes.gov.br/observatorio"
def sincronizar_instituicoes(db: Session):
    dados = listar_instituicoes_dos_programas()

    vistos = set()

    for item in dados:
        if item["key"] in vistos:
            continue

        vistos.add(item["key"])

        existe = (
            db.query(Instituicao)
            .filter(Instituicao.nome == item["value"])
            .first()
        )

        if existe:
            continue

        nova = Instituicao(
            nome=item["nome"],
            sigla=item["sigla"],
        )

        db.add(nova)

    db.commit()

def _buscar_faceta(nome):
    url = f"{BASE}/facetas/data/observatorio/ppg/{nome}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

def listar_instituicoes_dos_programas(
    area_avaliacao=None,
    area_conhecimento=None,
):
    dados = listar_programas(
        area_avaliacao=area_avaliacao,
        area_conhecimento=area_conhecimento,
        instituicao=None,
        page=0,
        size=1000,  # ou outro valor alto
    )

    instituicoes = []
    vistos = set()

    for programa in dados["content"]:
        sigla = programa.get("siglaIes")

        if sigla and sigla not in vistos:
            vistos.add(sigla)

            instituicoes.append({
                "tipo": 3,
                "nome": programa.get("nomeIes") or sigla,
                "sigla": sigla,
                "key": programa.get("idIes") or sigla,
                "value": programa.get("nomeIes") or sigla,
            })

    return instituicoes

def listar_grandes_areas():
    return _buscar_faceta("grande-area-conhecimento")


def listar_areas_avaliacao():
    return _buscar_faceta("area-avaliacao")


def listar_areas_conhecimento():
    return _buscar_faceta("area-conhecimento")


def listar_graus():
    return _buscar_faceta("grau")


def listar_modalidades():
    return _buscar_faceta("modalidade")


def listar_notas():
    return _buscar_faceta("conceito")

def listar_programas(
        area_avaliacao=None,
        area_conhecimento=None,
        instituicao=None,
        page=0,
        size=1000,
):
    filtros = []

    if area_avaliacao:
        filtros.append(f"area-avaliacao:({area_avaliacao})")

    if area_conhecimento:
        filtros.append(f"area-conhecimento:({area_conhecimento})")

    if instituicao:
        filtros.append(f"id-ies:({instituicao})")

    params = {
        "page": page,
        "size": size
    }

    if filtros:
        params["query"] = ";".join(filtros)

    r = requests.get(
        f"{BASE}/data/observatorio/ppg",
        params=params,
        timeout=50
    )

    r.raise_for_status()

    return r.json()