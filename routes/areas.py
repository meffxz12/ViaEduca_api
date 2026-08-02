"""
routes/areas.py — dropdowns de área de avaliação/conhecimento e grandes áreas

Endpoints:
    GET /areas/grandes-areas               -> lista estática (cadastro do estudante)
    GET /areas/avaliacao                   -> lista sincronizada da Sucupira
    GET /areas/conhecimento                -> lista sincronizada da Sucupira
    GET /areas/conhecimento?area_avaliacao_id=  -> filtrada (2º dropdown do Flutter)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud import areas as crud
from dependencies import pegar_sessao
from schemas.areas import (
    GrandeAreaResponse,
    AreaAvaliacaoResponse,
    AreaConhecimentoResponse,
)

areas_router = APIRouter(prefix="/areas", tags=["Áreas"])

# ------------------------------------------------------------------
# GET /areas/grandes-areas
# ------------------------------------------------------------------
@areas_router.get("/grandes-areas", response_model=list[GrandeAreaResponse])
def get_grandes_areas(db: Session = Depends(pegar_sessao)):
    return crud.listar_grandes_areas(db)


# ------------------------------------------------------------------
# GET /areas/avaliacao
# ------------------------------------------------------------------
@areas_router.get("/avaliacao", response_model=list[AreaAvaliacaoResponse])
def get_areas_avaliacao(db: Session = Depends(pegar_sessao)):
    return crud.listar_areas_avaliacao(db)


# ------------------------------------------------------------------
# GET /areas/conhecimento
# ------------------------------------------------------------------
@areas_router.get("/conhecimento", response_model=list[AreaConhecimentoResponse])
def get_areas_conhecimento(
    area_avaliacao_id: Optional[int] = None,
    db: Session = Depends(pegar_sessao),
):
    if area_avaliacao_id is not None:
        area = crud.buscar_area_avaliacao(db, area_avaliacao_id)
        if area is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Área de avaliação não encontrada",
            )
    return crud.listar_areas_conhecimento(db, area_avaliacao_id)