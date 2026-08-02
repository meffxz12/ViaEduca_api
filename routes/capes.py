from fastapi import APIRouter

from crud import capes
from fastapi import Depends
from sqlalchemy.orm import Session

from dependencies import pegar_sessao

from schemas.capes import (
    FacetaCAPES,
    ProgramasCAPESResponse,
)

capes_router = APIRouter(
    prefix="/capes",
    tags=["CAPES"]
)


# ============================
# FACETAS
# ============================
@capes_router.get(
    "/instituicoes-programas",
    response_model=list[FacetaCAPES]
)
def instituicoes_programas(
    area_avaliacao: str | None = None,
    area_conhecimento: str | None = None,
):
    return capes.listar_instituicoes_dos_programas(
        area_avaliacao,
        area_conhecimento,
    )

@capes_router.get(
    "/grandes-areas",
    response_model=list[FacetaCAPES]
)
def grandes_areas():
    return capes.listar_grandes_areas()


@capes_router.get(
    "/areas-avaliacao",
    response_model=list[FacetaCAPES]
)
def areas_avaliacao():
    return capes.listar_areas_avaliacao()


@capes_router.get(
    "/areas-conhecimento",
    response_model=list[FacetaCAPES]
)
def areas_conhecimento():
    return capes.listar_areas_conhecimento()


@capes_router.get(
    "/graus",
    response_model=list[FacetaCAPES]
)
def graus():
    return capes.listar_graus()


@capes_router.get(
    "/modalidades",
    response_model=list[FacetaCAPES]
)
def modalidades():
    return capes.listar_modalidades()


@capes_router.get(
    "/notas",
    response_model=list[FacetaCAPES]
)
def notas():
    return capes.listar_notas()

@capes_router.post("/sincronizar/instituicoes")
def sincronizar_instituicoes(
    db: Session = Depends(pegar_sessao),
):
    capes.sincronizar_instituicoes(db)

    return {"mensagem": "Instituições sincronizadas com sucesso"}


# ============================
# PROGRAMAS
# ============================

@capes_router.get(
    "/programas",
    response_model=ProgramasCAPESResponse
)
def programas(
    area_avaliacao: str | None = None,
    area_conhecimento: str | None = None,
    instituicao: str | None = None,
    page: int = 0,
    size: int = 20,
):

    return capes.listar_programas(
        area_avaliacao,
        area_conhecimento,
        instituicao,
        page,
        size,
    )