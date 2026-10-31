
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
    id: int
    id_capes: int
    nome: str
    grande_area_id: Optional[int] = None  # <-- adiciona

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