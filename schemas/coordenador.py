"""
schemas/coordenador.py — contratos de entrada e saída da API para o perfil do coordenador

Dados básicos (nome, email, cpf) já foram fixados no cadastro
(schemas/usuario.py -> CoordenadorCreate) e não são editáveis por aqui.
Este módulo cobre só o que faz sentido editar depois: celular, foto,
email institucional e a instituição vinculada.
"""
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