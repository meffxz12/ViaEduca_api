from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class ArquivoEditalCreate(BaseModel):
    edital_id: UUID
    nome_arquivo: str
    url_arquivo: str
    tipo: Optional[str] = None


class ArquivoEditalResponse(BaseModel):
    id: UUID
    edital_id: UUID
    nome_arquivo: str
    url_arquivo: str
    tipo: Optional[str]

    class Config:
        from_attributes = True