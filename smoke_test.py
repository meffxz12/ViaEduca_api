#!/usr/bin/env python3
"""
smoke_test.py — teste rápido do backend PUBLICADO (roda em ~30 s).

    pip install requests
    python smoke_test.py https://SEU-APP.up.railway.app

O que faz: bate nas rotas que o app usa, cria 1 estudante e 1 coordenador de
teste (e-mails qa...@qa-teste-viaeduca.com) e imprime ✔ / ✘ / ⚠ (lento) com o
tempo de cada chamada. Sai com código 1 se algo falhar.

Alguns testes FALHAM DE PROPÓSITO enquanto as correções de backend não forem
aplicadas (ver CORRECOES_backend.md): "token inválido → 401", "CPF inválido é
recusado" e "detalhe de programa sem coordenador".

Limpar os usuários de teste depois (no Postgres do Railway):
    DELETE FROM usuarios WHERE email LIKE 'qa%@qa-teste-viaeduca.com';
"""
import random
import string
import sys
import time

import requests

if len(sys.argv) < 2:
    sys.exit("Uso: python smoke_test.py https://SEU-APP.up.railway.app")

BASE = sys.argv[1].rstrip("/")
TIMEOUT = 30
LENTO_MS = 2500

S = requests.Session()
ctx = {}
resultados = []


# ------------------------------------------------------------------ utilidades
def gerar_cpf():
    n = [random.randint(0, 9) for _ in range(9)]
    for tam in (9, 10):
        s = sum(n[i] * (tam + 1 - i) for i in range(tam))
        d = (s * 10) % 11
        n.append(0 if d == 10 else d)
    cpf = "".join(map(str, n))
    return cpf if cpf != cpf[0] * 11 else gerar_cpf()


def gerar_celular():
    return "989" + "".join(random.choices(string.digits, k=8))


def req(metodo, caminho, token=None, **kw):
    headers = kw.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    inicio = time.perf_counter()
    r = S.request(metodo, BASE + caminho, headers=headers, timeout=TIMEOUT, **kw)
    r.ms = int((time.perf_counter() - inicio) * 1000)
    return r


def js(r):
    try:
        return r.json()
    except Exception:
        return None


def esperar(r, *codigos):
    assert r.status_code in codigos, (
        f"HTTP {r.status_code} (esperado {'/'.join(map(str, codigos))}) "
        f"→ {r.text[:160]!r}"
    )


def teste(nome, funcao):
    try:
        detalhe, ms = funcao()
        marca = "⚠" if ms and ms > LENTO_MS else "✔"
        resultados.append((marca, nome, ms, detalhe))
    except AssertionError as e:
        resultados.append(("✘", nome, None, str(e)))
    except Exception as e:  # rede, JSON, etc.
        resultados.append(("✘", nome, None, f"{type(e).__name__}: {e}"))


def pular(nome, motivo):
    resultados.append(("–", nome, None, f"pulado: {motivo}"))


# ------------------------------------------------------------------ testes públicos
def t_servidor():
    r = req("GET", "/openapi.json")
    esperar(r, 200)
    return "no ar", r.ms


def t_contagem():
    r = req("GET", "/programas/contagem")
    esperar(r, 200)
    total = js(r)["total"]
    assert total > 0, "banco sem programas (seed/restore não rodou?)"
    ctx["total_programas"] = total
    return f"{total} programas", r.ms


def t_listagem():
    r = req("GET", "/programas", params={"limit": 5, "offset": 0})
    esperar(r, 200)
    itens = js(r)
    assert itens, "lista vazia"
    for p in itens:
        nota = p.get("nota_capes")
        assert nota is None or isinstance(nota, str), f"nota_capes deveria ser texto, veio {nota!r}"
    ctx["programa_id"] = itens[0]["id"]
    return f"{len(itens)} itens; nota_capes ok (texto)", r.ms


def t_detalhe_programa():
    r = req("GET", f"/programas/{ctx['programa_id']}")
    esperar(r, 200)
    return "ok", r.ms


def t_listas_base():
    r1 = req("GET", "/areas/grandes-areas")
    esperar(r1, 200)
    grandes = js(r1)
    assert grandes, "sem grandes áreas"
    ctx["grande_area_id"] = grandes[0]["id"]

    r2 = req("GET", "/areas/avaliacao")
    esperar(r2, 200)
    areas = js(r2)
    assert areas, "sem áreas de avaliação"
    ctx["areas"] = areas

    r3 = req("GET", "/instituicao")
    esperar(r3, 200)
    assert js(r3), "sem instituições"
    return f"{len(grandes)} grandes áreas, {len(areas)} áreas, {len(js(r3))} IES", r1.ms + r2.ms + r3.ms


def t_token_invalido():
    r = req("GET", "/auth/me", token="token.totalmente.invalido")
    esperar(r, 401)
    return "401 como deveria", r.ms


# ------------------------------------------------------------------ estudante
def _payload_estudante(cpf, email, celular):
    return {
        "nome_completo": "QA Estudante Teste",
        "cpf": cpf,
        "email": email,
        "senha": "SenhaQA#2026",
        "celular": celular,
        "titulacao_atual": "Graduação",
        "area_titulacao_id": ctx["grande_area_id"],
    }


def t_cpf_invalido():
    body = _payload_estudante("12345678900", "qa.cpf@qa-teste-viaeduca.com", gerar_celular())
    r = req("POST", "/auth/cadastro/estudante", json=body)
    esperar(r, 400, 422)
    return f"recusado com {r.status_code}", r.ms


def t_cadastro_estudante():
    ctx["est_email"] = f"qa{int(time.time())}{random.randint(100, 999)}@qa-teste-viaeduca.com"
    ctx["est_senha"] = "SenhaQA#2026"
    body = _payload_estudante(gerar_cpf(), ctx["est_email"], gerar_celular())
    ctx["est_body"] = body
    r = req("POST", "/auth/cadastro/estudante", json=body)
    esperar(r, 200, 201)
    return "criado", r.ms


def t_cadastro_duplicado():
    r = req("POST", "/auth/cadastro/estudante", json=ctx["est_body"])
    esperar(r, 400, 409, 422)
    return f"duplicata recusada ({r.status_code})", r.ms


def t_login_estudante():
    r = req("POST", "/auth/login", json={"email": ctx["est_email"], "senha": ctx["est_senha"]})
    esperar(r, 200)
    ctx["est_token"] = js(r)["access_token"]
    return "token recebido", r.ms


def t_login_errado():
    r = req("POST", "/auth/login", json={"email": ctx["est_email"], "senha": "errada12345"})
    esperar(r, 400, 401)
    return f"recusado ({r.status_code})", r.ms


def t_me_e_perfil():
    r1 = req("GET", "/auth/me", token=ctx["est_token"])
    esperar(r1, 200)
    r2 = req("GET", "/estudante/perfil", token=ctx["est_token"])
    esperar(r2, 200)
    return "me + perfil ok", r1.ms + r2.ms


def t_home_do_estudante():
    perfil = js(req("GET", "/estudante/perfil", token=ctx["est_token"]))
    r = req("GET", "/programas", params={"limit": 10, "offset": 0,
                                         "grande_area_id": perfil.get("area_titulacao_id")})
    esperar(r, 200)
    return f"{len(js(r))} programas na área do estudante", r.ms


def t_favoritar():
    pid = ctx["programa_id"]
    r1 = req("POST", f"/estudante/favoritos/{pid}", token=ctx["est_token"])
    esperar(r1, 200, 201, 204)
    r2 = req("GET", "/estudante/favoritos", token=ctx["est_token"])
    esperar(r2, 200)
    r3 = req("DELETE", f"/estudante/favoritos/{pid}", token=ctx["est_token"])
    esperar(r3, 200, 204)
    return "favoritar → listar → desfavoritar ok", r1.ms + r2.ms + r3.ms


def t_notificacoes():
    r = req("GET", "/estudante/notificacoes/contagem", token=ctx["est_token"])
    esperar(r, 200)
    return f"nao_lidas={js(r).get('nao_lidas')}", r.ms


def t_editar_perfil():
    r = req("PATCH", "/perfil", token=ctx["est_token"], json={"nome_completo": "QA Estudante Editado"})
    esperar(r, 200)
    assert js(r)["nome_completo"] == "QA Estudante Editado", "nome não mudou"
    return "PATCH /perfil ok", r.ms


def t_trocar_senha():
    r1 = req("POST", "/perfil/alterar-senha", token=ctx["est_token"],
             json={"senha_atual": "errada12345", "nova_senha": "OutraSenha#2026"})
    esperar(r1, 400)
    r2 = req("POST", "/perfil/alterar-senha", token=ctx["est_token"],
             json={"senha_atual": ctx["est_senha"], "nova_senha": "OutraSenha#2026"})
    esperar(r2, 200, 204)
    r3 = req("POST", "/auth/login", json={"email": ctx["est_email"], "senha": "OutraSenha#2026"})
    esperar(r3, 200)
    return "senha errada recusada; troca ok; login com a nova ok", r1.ms + r2.ms + r3.ms


# ------------------------------------------------------------------ coordenador
def _escolher_combinacao():
    """Acha (area, conhecimento, instituicao) com catálogo de programas livres."""
    chamadas = 0
    escolha_qualquer = None
    for area in ctx["areas"][:12]:
        conhs = js(req("GET", "/areas/conhecimento", params={"area_avaliacao_id": area["id"]})) or []
        chamadas += 1
        for c in conhs[:3]:
            insts = js(req("GET", "/instituicao", params={
                "area_avaliacao_id": area["id"], "area_conhecimento_id": c["id"]})) or []
            chamadas += 1
            for i in insts[:4]:
                if escolha_qualquer is None:
                    escolha_qualquer = (area, c, i, [])
                cat = js(req("GET", "/programas/catalogo", params={
                    "instituicao_id": i["id"], "area_avaliacao_id": area["id"],
                    "area_conhecimento_id": c["id"]})) or []
                chamadas += 1
                if cat:
                    return (area, c, i, cat)
                if chamadas >= 60:
                    return escolha_qualquer
    return escolha_qualquer


def t_cadastro_coordenador():
    escolha = _escolher_combinacao()
    assert escolha, "não achei área/IES pra cadastrar o coordenador"
    area, conh, inst, catalogo = escolha
    ctx["catalogo"] = catalogo

    ctx["coord_email"] = f"qa{int(time.time())}{random.randint(100, 999)}@qa-teste-viaeduca.com"
    body = {
        "nome_completo": "QA Coordenador Teste",
        "cpf": gerar_cpf(),
        "email": ctx["coord_email"],
        "email_institucional": ctx["coord_email"],
        "senha": "SenhaQA#2026",
        "celular": gerar_celular(),
        "instituicao_id": inst["id"],
        "area_avaliacao_id": area["id"],
        "area_conhecimento_id": conh["id"],
    }
    r = req("POST", "/auth/cadastro/coordenador", json=body)
    esperar(r, 200, 201)
    ctx["coord_token"] = js(r)["access_token"]
    return f"criado ({len(catalogo)} programas livres no catálogo escolhido)", r.ms


def t_solicitar_vinculo():
    prog = ctx["catalogo"][0]
    body = {
        "linhas_pesquisa": [{"descricao": "Linha QA"}],
        "etapas_processo": [{"ordem": 1, "descricao": "Etapa QA"}],
    }
    r = req("POST", f"/programas/{prog['id']}/solicitar-vinculo", token=ctx["coord_token"], json=body)
    esperar(r, 201)
    r2 = req("GET", "/programas/minha-solicitacao", token=ctx["coord_token"])
    esperar(r2, 200)
    assert js(r2)["status"] == "pendente", f"status={js(r2)['status']}"
    return "solicitação criada e pendente (aprovar no painel admin)", r.ms + r2.ms


# ------------------------------------------------------------------ execução
print(f"\nSmoke test em {BASE}\n")

teste("Servidor responde", t_servidor)
teste("Contagem de programas", t_contagem)
teste("Listagem de programas (nota_capes como texto)", t_listagem)

if "programa_id" in ctx:
    teste("Detalhe de programa (sem coordenador)", t_detalhe_programa)
else:
    pular("Detalhe de programa", "listagem falhou")

teste("Grandes áreas / áreas / instituições", t_listas_base)
teste("Token inválido devolve 401 (e não 500)", t_token_invalido)

if "grande_area_id" in ctx:
    teste("CPF inválido é recusado", t_cpf_invalido)
    teste("Cadastro de estudante", t_cadastro_estudante)
    if "est_body" in ctx:
        teste("Cadastro duplicado é recusado", t_cadastro_duplicado)
        teste("Login do estudante", t_login_estudante)
        teste("Login com senha errada é recusado", t_login_errado)
    if "est_token" in ctx:
        teste("/auth/me e /estudante/perfil", t_me_e_perfil)
        teste("Home do estudante (filtro por grande área)", t_home_do_estudante)
        if "programa_id" in ctx:
            teste("Favoritar / listar / desfavoritar", t_favoritar)
        teste("Contagem de notificações", t_notificacoes)
        teste("Editar perfil (PATCH /perfil)", t_editar_perfil)
        teste("Trocar senha", t_trocar_senha)
else:
    pular("Fluxo do estudante", "listas base falharam")

if "areas" in ctx:
    teste("Cadastro de coordenador", t_cadastro_coordenador)
    if ctx.get("catalogo") and "coord_token" in ctx:
        teste("Solicitar vínculo (fica pendente)", t_solicitar_vinculo)
    elif "coord_token" in ctx:
        pular("Solicitar vínculo", "nenhum programa livre no catálogo escolhido")
else:
    pular("Fluxo do coordenador", "listas base falharam")

# ------------------------------------------------------------------ relatório
print(f"{'':2}{'TESTE':<52}{'TEMPO':>8}   DETALHE")
print("-" * 110)
falhas = lentos = 0
for marca, nome, ms, detalhe in resultados:
    if marca == "✘":
        falhas += 1
    if marca == "⚠":
        lentos += 1
    tempo = f"{ms} ms" if ms is not None else ""
    print(f"{marca:<2}{nome:<52}{tempo:>8}   {detalhe}")

print("-" * 110)
print(f"{len(resultados)} testes · {falhas} falha(s) · {lentos} lento(s) (> {LENTO_MS} ms)")
print("Limpeza: DELETE FROM usuarios WHERE email LIKE 'qa%@qa-teste-viaeduca.com';\n")
sys.exit(1 if falhas else 0)