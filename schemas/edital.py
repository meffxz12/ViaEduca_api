"""
schemas/edital.py — contratos de entrada/saída para Edital
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class EditalCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    data_inicio_inscricao: Optional[date] = None
    data_fim_inscricao: Optional[date] = None


class EditalUpdateStatus(BaseModel):
    status: str


class EditalResponse(BaseModel):
    id: int
    programa_id: int
    titulo: str
    descricao: Optional[str]
    data_inicio_inscricao: Optional[date]
    data_fim_inscricao: Optional[date]
    status: str
    criado_em: datetime

    class Config:
        from_attributes = True