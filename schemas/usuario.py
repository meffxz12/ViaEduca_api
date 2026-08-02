"""
schemas/usuario.py — contratos de entrada e saída da API para usuários
"""
import re
from datetime import datetime
from typing import Optional
from uuid import UUID


from pydantic import BaseModel, EmailStr, Field, field_validator
from schemas.programas import ProgramaCreate


# ------------------------------------------a---------------------------------
# Validadores reutilizados por EstudanteCreate e CoordenadorCreate
# ---------------------------------------------------------------------------
def _validar_cpf(cpf: str) -> str:
    digitos = re.sub(r"\D", "", cpf)

    if len(digitos) != 11:
        raise ValueError("CPF deve ter 11 dígitos")

    if digitos == digitos[0] * 11:  # 000.000.000-00, 111.111.111-11 etc.
        raise ValueError("CPF inválido")

    def _digito_verificador(parcial: str) -> int:
        soma = sum(
            int(d) * peso for d, peso in zip(parcial, range(len(parcial) + 1, 1, -1))
        )
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    d1 = _digito_verificador(digitos[:9])
    d2 = _digito_verificador(digitos[:9] + str(d1))

    if digitos[-2:] != f"{d1}{d2}":
        raise ValueError("CPF inválido")

    return digitos  # normalizado: só os 11 dígitos, sem pontuação


def _validar_celular(celular: Optional[str]) -> Optional[str]:
    if celular is None:
        return celular

    digitos = re.sub(r"\D", "", celular)

    if len(digitos) not in (10, 11):  # DDD + número (fixo=10, celular=11)
        raise ValueError("Celular deve ter DDD + número (10 ou 11 dígitos)")

    return digitos  # normalizado: só dígitos


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str
    
class LoginResponse(BaseModel):
    token: str
    id: UUID
    nome_completo: str
    email: str
    tipo: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tipo_usuario: str   # "estudante" ou "coordenador" — Flutter usa pra redirecionar


# ---------------------------------------------------------------------------
# Cadastro Estudante
# ---------------------------------------------------------------------------
class EstudanteCreate(BaseModel):
    nome_completo:  str
    cpf:            str
    email:          EmailStr
    senha:          str = Field(..., min_length=6)
    celular:        Optional[str] = None
    titulacao_atual: Optional[str] = None   # "Graduação" | "Especialização" | "Mestrado" | "Doutorado"
    area_titulacao_id: Optional[int] = None    # FK pra areas_titulacao (lista estática)

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        return _validar_cpf(v)

    @field_validator("celular")
    @classmethod
    def validar_celular(cls, v: Optional[str]) -> Optional[str]:
        return _validar_celular(v)


# ---------------------------------------------------------------------------
# Cadastro Coordenador
# ---------------------------------------------------------------------------
class CoordenadorCreate(BaseModel):
    nome_completo:       str
    cpf:                 str
    email:               EmailStr
    senha:               str = Field(..., min_length=8)
    celular:             Optional[str] = None
    email_institucional: Optional[str] = None
    instituicao_id:      Optional[int] = None
    area_avaliacao_id: Optional[int] = None
    area_conhecimento_id: Optional[int] = None

    # Programa vem junto no mesmo cadastro — 1 requisição só,
    # já que ainda não existe coordenador autenticado antes deste ponto
    programa: ProgramaCreate

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        return _validar_cpf(v)

    @field_validator("celular")
    @classmethod
    def validar_celular(cls, v: Optional[str]) -> Optional[str]:
        return _validar_celular(v)
# ---------------------------------------------------------------------------
# Resposta genérica de usuário (perfil)
# ---------------------------------------------------------------------------
class UsuarioResponse(BaseModel):
    id:           UUID
    tipo:         str
    nome_completo: str
    email:        EmailStr
    celular:      Optional[str]
    foto_url:     Optional[str]
    criado_em:    datetime

    class Config:
        from_attributes = True