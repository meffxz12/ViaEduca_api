import time
import requests

BASE_URL = "https://sucupira.capes.gov.br/api/data/online"
TIMEOUT = 60  # CAPES pode ser lenta, dá mais margem
MAX_TENTATIVAS = 3


def _get_com_retry(url: str, params: dict) -> dict:
    ultimo_erro = None

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resposta = requests.get(url, params=params, timeout=TIMEOUT)
            resposta.raise_for_status()
            return resposta.json()
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            ultimo_erro = e
            espera = 5 * tentativa  # 5s, 10s, 15s...
            print(f"Tentativa {tentativa}/{MAX_TENTATIVAS} falhou ({e}). Tentando de novo em {espera}s...")
            time.sleep(espera)

    raise ultimo_erro


def listar_instituicoes():
    dados = _get_com_retry(
        f"{BASE_URL}/ies",
        params={"page": 0, "size": 10000},
    )
    return dados


def listar_areas_avaliacao(size: int = 50):
    todos = []
    page = 0

    while True:
        dados = _get_com_retry(
            f"{BASE_URL}/area_avaliacao",
            params={"page": page, "size": size},
        )
        pagina = dados["content"]
        todos.extend(pagina)

        if len(pagina) < size:
            break
        page += 1

    return {"content": todos, "size": len(todos)}


def listar_areas_conhecimento(id_area_avaliacao: int):
    resposta = requests.get(
        f"{BASE_URL}/area_avaliacao/{id_area_avaliacao}",
        timeout=TIMEOUT,
    )
    resposta.raise_for_status()
    return resposta.json()


def listar_programas(size: int = 50):
    todos = []
    page = 0

    while True:
        dados = _get_com_retry(
            f"{BASE_URL}/ppg",
            params={"page": page, "size": size},
        )
        pagina = dados["content"]
        todos.extend(pagina)

        print(f"Página {page} ok — {len(pagina)} itens (total até agora: {len(todos)})")

        if len(pagina) < size:
            break

        page += 1

    return {"content": todos, "size": len(todos)}