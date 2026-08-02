from pydantic import BaseModel
from uuid import UUID


class EtapaProcessoCreate(BaseModel):
    edital_id: UUID
    nome: str
    descricao: str | None = None
    ordem: int


class EtapaProcessoResponse(BaseModel):
    id: UUID
    edital_id: UUID
    nome: str
    descricao: str | None
    ordem: int

    class Config:
        from_attributes = True