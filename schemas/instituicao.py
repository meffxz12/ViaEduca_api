"""
schemas/instituicao.py — contrato de saída pro dropdown de instituição
(usado no cadastro do coordenador e no cadastro/busca de programa)
"""
from typing import Optional

from pydantic import BaseModel


class InstituicaoResponse(BaseModel):
    id:     int
    nome:   str
    sigla:  Optional[str]


    class Config:
        from_attributes = True