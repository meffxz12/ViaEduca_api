
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class CoordenadorPerfilResponse(BaseModel):
    id:                  UUID
    nome_completo:       str
    email:               EmailStr
    celular:             Optional[str]
    foto_url:            Optional[str]
    email_institucional: Optional[str]
    instituicao_id:      Optional[int]
    area_avaliacao_id:      Optional[int]     # <-- confirma que está aqui
    area_conhecimento_id:   Optional[int]     # <-- confirma que está aqui
    criado_em:           datetime

    tem_programa: bool = False

    class Config:
        from_attributes = True
        
class CoordenadorUpdate(BaseModel):
    celular:             Optional[str] = None
    foto_url:            Optional[str] = None
    email_institucional: Optional[str] = None
    instituicao_id:      Optional[int] = None
    area_avaliacao_id:      Optional[int] = None
    area_conhecimento_id:   Optional[int] = None