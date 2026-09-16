"""
routes/programas.py — cadastro (coordenador), busca (estudante) e
gerenciamento de linhas de pesquisa / etapas do processo de um programa
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud import programas as crud
from crud import linha_pesquisa as crud_linha
from crud import etapa_processo as crud_etapa
from dependencies import pegar_sessao, exigir_coordenador
from models import Usuario, Programa
from schemas.programas import (
    ProgramaCreate,
    ProgramaUpdate,
    ProgramaResponse,
    ProgramaCapesResponse,
    ProgramaListItem,
    LinhaPesquisaCreate,
    LinhaPesquisaUpdate,
    LinhaPesquisaResponse,
    EtapaProcessoCreate,
    EtapaProcessoUpdate,
    EtapaProcessoResponse,
)
from crud import solicitacao_vinculo as crud_solicitacao
from schemas.solicitacao_vinculo import SolicitacaoVinculoCreate, SolicitacaoVinculoResponse

programas_router = APIRouter(prefix="/programas", tags=["Programas"])


def _exigir_dono(programa, usuario_logado: Usuario) -> None:
    if programa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programa não encontrado")
    if programa.coordenador_id != usuario_logado.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não é o coordenador deste programa")


# ------------------------------------------------------------------
# POST /programas — cadastro único, feito logo após o cadastro de perfil
# ------------------------------------------------------------------
@programas_router.post(
    "",
    response_model=ProgramaResponse,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_programa(
    dados: ProgramaCreate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    erro = crud.validar_novo_programa(db, usuario_logado.id, dados)
    if erro is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=erro)

    return crud.criar_programa(db, usuario_logado.id, dados)


# ------------------------------------------------------------------
# GET /programas/meus — programa(s) do coordenador logado (1 ou 2: MA/D)
# ------------------------------------------------------------------
@programas_router.get("/meus", response_model=list[ProgramaResponse])
def get_meus_programas(
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    return crud.programas_do_coordenador(db, usuario_logado.id)


# ------------------------------------------------------------------
# GET /programas/catalogo — programas SEM coordenador (pra solicitar vínculo)
# ------------------------------------------------------------------
@programas_router.get("/catalogo", response_model=list[ProgramaListItem])
def get_catalogo_programas(
    instituicao_id: int,
    area_avaliacao_id: int,
    area_conhecimento_id: Optional[int] = None,
    db: Session = Depends(pegar_sessao),
):
    query = db.query(Programa).filter(
        Programa.instituicao_id == instituicao_id,
        Programa.area_avaliacao_id == area_avaliacao_id,
        Programa.coordenador_id.is_(None),
    )
    if area_conhecimento_id:
        query = query.filter(Programa.area_conhecimento_id == area_conhecimento_id)
    return query.order_by(Programa.nome).all()


# ------------------------------------------------------------------
# GET /programas/contagem — precisa vir ANTES de /{programa_id},
# senão o FastAPI tenta converter "contagem" pra int e quebra.
# ------------------------------------------------------------------
@programas_router.get("/contagem")
def contar_programas(
    nivel: Optional[str] = None,
    instituicao_id: Optional[int] = None,
    area_avaliacao_id: Optional[int] = None,
    area_conhecimento_id: Optional[int] = None,
    nota_capes_min: Optional[int] = None,
    nome: Optional[str] = None,
    grande_area_id: Optional[int] = None,
    db: Session = Depends(pegar_sessao),
):
    total = crud.contar_programas(
        db,
        nivel=nivel,
        instituicao_id=instituicao_id,
        area_avaliacao_id=area_avaliacao_id,
        area_conhecimento_id=area_conhecimento_id,
        nota_capes_min=nota_capes_min,
        nome=nome,
        grande_area_id=grande_area_id,
    )
    return {"total": total}


# ------------------------------------------------------------------
# GET /programas — busca/listagem (usada pelo estudante)
# ÚNICA definição agora — a antiga duplicada foi removida.
# ------------------------------------------------------------------
@programas_router.get("", response_model=list[ProgramaListItem])
def listar_programas(
    nivel: Optional[str] = None,
    instituicao_id: Optional[int] = None,
    area_avaliacao_id: Optional[int] = None,
    area_conhecimento_id: Optional[int] = None,
    nota_capes_min: Optional[int] = None,
    nome: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    db: Session = Depends(pegar_sessao),
):
    return crud.listar_programas(
        db,
        nivel=nivel,
        instituicao_id=instituicao_id,
        area_avaliacao_id=area_avaliacao_id,
        area_conhecimento_id=area_conhecimento_id,
        nota_capes_min=nota_capes_min,
        nome=nome,
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------
# POST /programas/{programa_id}/solicitar-vinculo
# ------------------------------------------------------------------
@programas_router.post(
    "/{programa_id}/solicitar-vinculo",
    response_model=SolicitacaoVinculoResponse,
    status_code=status.HTTP_201_CREATED,
)
def solicitar_vinculo(
    programa_id: int,
    dados: SolicitacaoVinculoCreate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    programa = crud.buscar_programa(db, programa_id)
    if programa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programa não encontrado")
    if programa.coordenador_id is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Este programa já tem um coordenador vinculado")
    if crud_solicitacao.ja_tem_pendente(db, usuario_logado.id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Você já tem uma solicitação pendente")

    return crud_solicitacao.criar(db, programa_id, usuario_logado.id)


# ------------------------------------------------------------------
# GET /programas/{programa_id} — detalhe (usado pelo estudante)
# ------------------------------------------------------------------
@programas_router.get("/{programa_id}", response_model=ProgramaResponse)
def get_programa(
    programa_id: int,
    db: Session = Depends(pegar_sessao),
):
    programa = crud.buscar_programa(db, programa_id)
    if programa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Programa não encontrado",
        )
    return programa


# ------------------------------------------------------------------
# PATCH /programas/{programa_id} — edição parcial (só o coordenador dono)
# ------------------------------------------------------------------
@programas_router.patch("/{programa_id}", response_model=ProgramaResponse)
def atualizar_programa(
    programa_id: int,
    dados: ProgramaUpdate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    programa = crud.buscar_programa(db, programa_id)
    _exigir_dono(programa, usuario_logado)
    return crud.atualizar_programa(db, programa, dados)


# ==================================================================
# Linhas de pesquisa — gerenciamento individual (fora do cadastro em lote)
# ==================================================================
@programas_router.post(
    "/{programa_id}/linhas-pesquisa",
    response_model=LinhaPesquisaResponse,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_linha_pesquisa(
    programa_id: int,
    dados: LinhaPesquisaCreate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    programa = crud.buscar_programa(db, programa_id)
    _exigir_dono(programa, usuario_logado)
    return crud_linha.adicionar(db, programa_id, dados)


@programas_router.patch(
    "/{programa_id}/linhas-pesquisa/{linha_id}",
    response_model=LinhaPesquisaResponse,
)
def editar_linha_pesquisa(
    programa_id: int,
    linha_id: int,
    dados: LinhaPesquisaUpdate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    programa = crud.buscar_programa(db, programa_id)
    _exigir_dono(programa, usuario_logado)

    linha = crud_linha.buscar(db, linha_id)
    if linha is None or linha.programa_id != programa_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linha de pesquisa não encontrada")

    return crud_linha.atualizar(db, linha, dados)


@programas_router.delete(
    "/{programa_id}/linhas-pesquisa/{linha_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remover_linha_pesquisa(
    programa_id: int,
    linha_id: int,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    programa = crud.buscar_programa(db, programa_id)
    _exigir_dono(programa, usuario_logado)

    linha = crud_linha.buscar(db, linha_id)
    if linha is None or linha.programa_id != programa_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linha de pesquisa não encontrada")

    crud_linha.remover(db, linha)


# ==================================================================
# Etapas do processo — gerenciamento individual (fora do cadastro em lote)
# ==================================================================
@programas_router.post(
    "/{programa_id}/etapas_processo",
    response_model=EtapaProcessoResponse,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_etapa_processo(
    programa_id: int,
    dados: EtapaProcessoCreate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    programa = crud.buscar_programa(db, programa_id)
    _exigir_dono(programa, usuario_logado)

    if crud_etapa.ordem_em_uso(db, programa_id, dados.ordem):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Já existe uma etapa com ordem {dados.ordem} neste programa",
        )

    return crud_etapa.adicionar(db, programa_id, dados)


@programas_router.patch(
    "/{programa_id}/etapas-processo/{etapa_id}",
    response_model=EtapaProcessoResponse,
)
def editar_etapa_processo(
    programa_id: int,
    etapa_id: int,
    dados: EtapaProcessoUpdate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    programa = crud.buscar_programa(db, programa_id)
    _exigir_dono(programa, usuario_logado)

    etapa = crud_etapa.buscar(db, etapa_id)
    if etapa is None or etapa.programa_id != programa_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Etapa do processo não encontrada")

    if dados.ordem is not None and crud_etapa.ordem_em_uso(
        db, programa_id, dados.ordem, ignorar_etapa_id=etapa_id
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Já existe uma etapa com ordem {dados.ordem} neste programa",
        )

    return crud_etapa.atualizar(db, etapa, dados)


@programas_router.delete(
    "/{programa_id}/etapas-processo/{etapa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remover_etapa_processo(
    programa_id: int,
    etapa_id: int,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    programa = crud.buscar_programa(db, programa_id)
    _exigir_dono(programa, usuario_logado)

    etapa = crud_etapa.buscar(db, etapa_id)
    if etapa is None or etapa.programa_id != programa_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Etapa do processo não encontrada")

    crud_etapa.remover(db, etapa)