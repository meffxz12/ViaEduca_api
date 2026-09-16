from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class LinhaPesquisaRascunho(BaseModel):
    descricao: str


class EtapaProcessoRascunho(BaseModel):
    ordem: int
    descricao: str


class SolicitacaoVinculoCreate(BaseModel):
    linhas_pesquisa: list[LinhaPesquisaRascunho] = []
    etapas_processo: list[EtapaProcessoRascunho] = []


class SolicitacaoVinculoResponse(BaseModel):
    id: int
    programa_id: int
    coordenador_id: UUID
    status: str
    criado_em: datetime
    decidido_em: Optional[datetime]
    motivo_rejeicao: Optional[str]

    class Config:
        from_attributes = True


class SolicitacaoVinculoRejeitar(BaseModel):
    motivo: Optional[str] = None