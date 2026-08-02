from pydantic import BaseModel
from uuid import UUID


class LinhaPesquisaCreate(BaseModel):
    programa_id: UUID
    nome: str
    descricao: str | None = None


class LinhaPesquisaResponse(BaseModel):
    id: UUID
    programa_id: UUID
    nome: str
    descricao: str | None = None

    class Config:
        from_attributes = True