from pydantic import BaseModel
from typing import Optional
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