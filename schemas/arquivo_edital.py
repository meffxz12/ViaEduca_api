from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ArquivoEditalResponse(BaseModel):
    id: int
    edital_id: int
    etapa_id: Optional[int]
    titulo: str
    arquivo_url: str
    alerta_sonoro: bool
    publicado_em: datetime

    class Config:
        from_attributes = True

class ArquivoEditalResponse(BaseModel):
    id: UUID
    edital_id: UUID
    nome_arquivo: str
    url_arquivo: str
    tipo: Optional[str]

    class Config:
        from_attributes = True