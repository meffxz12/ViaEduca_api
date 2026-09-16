"""
routes/coordenador.py — perfil do coordenador (ver/atualizar)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud import coordenador as crud
from crud import programas as crud_programas
from dependencies import pegar_sessao, exigir_coordenador
from models import Usuario
from schemas.coordenador import CoordenadorPerfilResponse, CoordenadorUpdate

coordenador_router = APIRouter(prefix="/coordenador", tags=["Coordenador"])


def _montar_perfil(db: Session, usuario: Usuario, coordenador) -> CoordenadorPerfilResponse:
    tem_programa = crud_programas.coordenador_ja_tem_programa(db, usuario.id)
    return CoordenadorPerfilResponse(
        id=usuario.id,
        nome_completo=usuario.nome_completo,
        email=usuario.email,
        celular=usuario.celular,
        foto_url=usuario.foto_url,
        email_institucional=coordenador.email_institucional,
        instituicao_id=coordenador.instituicao_id,
        area_avaliacao_id=coordenador.area_avaliacao_id,       # <-- confirma que está aqui
        area_conhecimento_id=coordenador.area_conhecimento_id, # <-- confirma que está aqui
        criado_em=usuario.criado_em,
        tem_programa=tem_programa,
    )


# ------------------------------------------------------------------
# GET /coordenador/perfil
# ------------------------------------------------------------------
@coordenador_router.get("/perfil", response_model=CoordenadorPerfilResponse)
def get_perfil(
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    coordenador = crud.buscar_coordenador(db, usuario_logado.id)
    if coordenador is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Coordenador não encontrado")
    return _montar_perfil(db, usuario_logado, coordenador)


# ------------------------------------------------------------------
# PATCH /coordenador/perfil
# ------------------------------------------------------------------
@coordenador_router.patch("/perfil", response_model=CoordenadorPerfilResponse)
def atualizar_perfil(
    dados: CoordenadorUpdate,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_coordenador),
):
    coordenador = crud.buscar_coordenador(db, usuario_logado.id)
    if coordenador is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Coordenador não encontrado")

    coordenador = crud.atualizar_coordenador(db, usuario_logado, coordenador, dados)
    return _montar_perfil(db, usuario_logado, coordenador)