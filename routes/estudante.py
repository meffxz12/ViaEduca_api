"""
routes/estudante.py — busca de programa, favoritar e notificações

Todas as rotas exigem estudante logado (Depends(exigir_estudante)), já
que a busca marca `favoritado` por estudante e favoritos/notificações
são sempre pessoais.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud import estudante as crud
from crud import programas as crud_programas
from dependencies import pegar_sessao, exigir_estudante
from models import Usuario
from schemas.estudante import (
    ProgramaBuscaItem,
    ProgramaFavoritoResponse,
    NotificacaoResponse,
    ContadorNotificacoesResponse,
    EstudantePerfilResponse,
)

estudante_router = APIRouter(prefix="/estudante", tags=["Estudante"])


# ------------------------------------------------------------------
# GET /estudante/programas — busca, com flag de favorito por item
# ------------------------------------------------------------------
@estudante_router.get("/programas", response_model=list[ProgramaBuscaItem])
def buscar_programas(
    nivel: Optional[str] = None,
    instituicao_id: Optional[int] = None,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    programas = crud_programas.listar_programas(db, nivel=nivel, instituicao_id=instituicao_id)
    favoritados = crud.ids_programas_favoritados(db, usuario_logado.id)

    return [
        ProgramaBuscaItem(
            id=p.id,
            nome=p.nome,
            nivel=p.nivel,
            nota_capes=p.nota_capes,
            favoritado=p.id in favoritados,
        )
        for p in programas
    ]


# ------------------------------------------------------------------
# POST /estudante/favoritos/{programa_id} — favoritar (idempotente)
# ------------------------------------------------------------------
@estudante_router.post(
    "/favoritos/{programa_id}",
    response_model=ProgramaFavoritoResponse,
    status_code=status.HTTP_201_CREATED,
)
def favoritar_programa(
    programa_id: int,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    programa = crud_programas.buscar_programa(db, programa_id)
    if programa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programa não encontrado")

    return crud.favoritar_programa(db, usuario_logado.id, programa_id)


# ------------------------------------------------------------------
# DELETE /estudante/favoritos/{programa_id} — desfavoritar
# ------------------------------------------------------------------
@estudante_router.delete(
    "/favoritos/{programa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def desfavoritar_programa(
    programa_id: int,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    removido = crud.desfavoritar_programa(db, usuario_logado.id, programa_id)
    if not removido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Você não tinha favoritado esse programa")


# ------------------------------------------------------------------
# GET /estudante/favoritos — lista os programas favoritados
# ------------------------------------------------------------------
@estudante_router.get("/favoritos", response_model=list[ProgramaFavoritoResponse])
def listar_favoritos(
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    return crud.listar_favoritos(db, usuario_logado.id)


# ------------------------------------------------------------------
# GET /estudante/notificacoes — lista (mais recentes primeiro)
# ------------------------------------------------------------------
@estudante_router.get("/notificacoes", response_model=list[NotificacaoResponse])
def listar_notificacoes(
    apenas_nao_lidas: bool = False,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    notificacoes = crud.listar_notificacoes(
        db, usuario_logado.id, apenas_nao_lidas=apenas_nao_lidas
    )
    return [_montar_notificacao_response(n) for n in notificacoes]


# ------------------------------------------------------------------
# GET /estudante/notificacoes/contagem — pro badge de não lidas
# ------------------------------------------------------------------
@estudante_router.get("/notificacoes/contagem", response_model=ContadorNotificacoesResponse)
def contar_notificacoes_nao_lidas(
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    return ContadorNotificacoesResponse(nao_lidas=crud.contar_nao_lidas(db, usuario_logado.id))


# ------------------------------------------------------------------
# PATCH /estudante/notificacoes/lidas — marca todas como lidas
# (Rota fixa "lidas" vem ANTES de "/{notificacao_id}/lida" no arquivo pra
# não ser capturada por engano pela rota com parâmetro dinâmico.)
# ------------------------------------------------------------------
@estudante_router.patch("/notificacoes/lidas", response_model=ContadorNotificacoesResponse)
def marcar_todas_notificacoes_lidas(
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    crud.marcar_todas_lidas(db, usuario_logado.id)
    return ContadorNotificacoesResponse(nao_lidas=0)


# ------------------------------------------------------------------
# PATCH /estudante/notificacoes/{notificacao_id}/lida — marca uma como lida
# ------------------------------------------------------------------
@estudante_router.patch("/notificacoes/{notificacao_id}/lida", response_model=NotificacaoResponse)
def marcar_notificacao_lida(
    notificacao_id: int,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    notificacao = crud.buscar_notificacao(db, notificacao_id)
    if notificacao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificação não encontrada")
    if notificacao.estudante_id != usuario_logado.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Essa notificação não é sua")

    notificacao = crud.marcar_notificacao_lida(db, notificacao)
    return _montar_notificacao_response(notificacao)


# ------------------------------------------------------------------
# Helper — monta o NotificacaoResponse navegando arquivo -> edital -> programa
# ------------------------------------------------------------------
def _montar_notificacao_response(notificacao) -> NotificacaoResponse:
    edital = notificacao.edital
    programa = edital.programa if edital else None

    return NotificacaoResponse(
        id=notificacao.id,
        titulo=notificacao.titulo,
        lida=notificacao.lida,
        criado_em=notificacao.criado_em,
        edital_id=edital.id if edital else None,
        edital_titulo=edital.titulo if edital else None,
        programa_id=programa.id if programa else None,
        programa_nome=programa.nome if programa else None,
    )

# ------------------------------------------------------------------
# GET /estudante/perfil — dados do estudante logado (usado pra
# filtrar a home pela grande área dele)
# ------------------------------------------------------------------
@estudante_router.get("/perfil", response_model=EstudantePerfilResponse)
def get_perfil(
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_estudante),
):
    estudante = crud.buscar_estudante(db, usuario_logado.id)
    if estudante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estudante não encontrado")

    return EstudantePerfilResponse(
        id=usuario_logado.id,
        nome_completo=usuario_logado.nome_completo,
        email=usuario_logado.email,
        titulacao_atual=estudante.titulacao_atual,
        area_titulacao_id=estudante.area_titulacao_id,
        area_titulacao_nome=estudante.grande_area.nome if estudante.grande_area else None,
    )