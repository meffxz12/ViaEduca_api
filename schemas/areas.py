"""
schemas/area.py — contratos de saída da API para as áreas usadas nos dropdowns

- GrandeArea: lista estática (seed no banco), usada no cadastro do estudante
- AreaAvaliacao / AreaConhecimento: sincronizadas 1x/dia da API Sucupira,
  usadas no cadastro do programa (coordenador)
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# GrandesAreas — estudante escolhe no cadastro
# ---------------------------------------------------------------------------
class GrandeAreaResponse(BaseModel):
    id:   int
    nome: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AreasAvaliacao — coordenador escolhe no cadastro do programa
# ---------------------------------------------------------------------------
class AreaAvaliacaoResponse(BaseModel):
    id:              int
    id_capes:        int
    nome:            str
    sincronizado_em: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AreasConhecimento — sub-área, depende da área de avaliação escolhida
# ---------------------------------------------------------------------------
class AreaConhecimentoResponse(BaseModel):
    id:                int
    id_capes:          int
    area_avaliacao_id: int
    nome:              str
    sincronizado_em:   datetime

    class Config:
        from_attributes = True