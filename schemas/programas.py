"""
schemas/programa.py — contratos de entrada e saída da API para o programa

Fluxo: coordenador cadastra o programa UMA VEZ, logo após o cadastro de
perfil (tela 5 do Flutter). O cadastro é feito num único request que já
inclui as listas dinâmicas de linhas de pesquisa e etapas do processo
seletivo.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# LinhasPesquisa — lista dinâmica (sem ordem)
# ---------------------------------------------------------------------------
class LinhaPesquisaCreate(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=200)


class LinhaPesquisaResponse(BaseModel):
    id:        int
    descricao: str

    class Config:
        from_attributes = True

class LinhaPesquisaUpdate(BaseModel):
    descricao: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

# ---------------------------------------------------------------------------
# EtapasProcesso — lista dinâmica ordenada
# Ex: 1ª Análise curricular, 2ª Prova discursiva, 3ª Entrevista
# ---------------------------------------------------------------------------
class EtapaProcessoCreate(BaseModel):
    ordem:     int = Field(..., ge=1)
    descricao: str = Field(..., min_length=1, max_length=200)


class EtapaProcessoResponse(BaseModel):
    id:        int
    ordem:     int
    descricao: str

    class Config:
        from_attributes = True

class EtapaProcessoUpdate(BaseModel):
    ordem: Optional[int] = Field(
        default=None,
        ge=1,
    )

    descricao: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
# ---------------------------------------------------------------------------
# Programa — cadastro (entrada)
# ---------------------------------------------------------------------------
class ProgramaCreate(BaseModel):
    # Dados vindos da CAPES
    id_programa_capes: int
    codigo: str

    nome: str

    nivel: str                   # MP | MA | D
    instituicao_id: int

    area_avaliacao_id: int
    area_conhecimento_id: Optional[int] = None

    nota_capes: Optional[int] = Field(
        default=None,
        ge=1,
        le=7
    )

    linhas_pesquisa: list[LinhaPesquisaCreate] = Field(default_factory=list)
    etapas_processo: list[EtapaProcessoCreate] = Field(default_factory=list)

    @field_validator("nivel")
    @classmethod
    def validar_nivel(cls, v):
        if v not in {"MP", "MA", "D"}:
            raise ValueError("Nível inválido.")
        return v

    @field_validator("etapas_processo")
    @classmethod
    def validar_ordens_unicas(cls, v):
        ordens = [e.ordem for e in v]
        if len(ordens) != len(set(ordens)):
            raise ValueError("As etapas não podem ter ordens repetidas.")
        return v

# ---------------------------------------------------------------------------
# Programa — atualização (parcial, todos os campos opcionais)
# Obs: linhas de pesquisa e etapas não são atualizadas por aqui — dá pra
# criar endpoints próprios (POST/DELETE) pra cada uma se precisar editar
# item a item, em vez de substituir a lista inteira.
# ---------------------------------------------------------------------------
class ProgramaUpdate(BaseModel):
    nome:                 Optional[str] = None
    id_capes:             Optional[str] = None
    area_avaliacao_id:    Optional[int] = None
    area_conhecimento_id: Optional[int] = None
    nota_capes:           Optional[int] = Field(default=None, ge=1, le=7)
    programa_aberto:      Optional[bool] = None

# ---------------------------------------------------------------------------
# Programa — resposta completa (perfil do programa)
# ---------------------------------------------------------------------------
class ProgramaResponse(BaseModel):
    id:                   int
    coordenador_id:       UUID
    instituicao_id:       int
    nome:                 str
    id_capes:             Optional[str]
    nivel:                str
    area_avaliacao_id:    Optional[int]
    area_conhecimento_id: Optional[int]
    nota_capes:           Optional[int]
    criado_em:            datetime
    programa_aberto: bool

    linhas_pesquisa: list[LinhaPesquisaResponse] = []
    etapas_processo: list[EtapaProcessoResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Programa — item de listagem (busca do estudante), mais enxuto
# ---------------------------------------------------------------------------
class ProgramaListItem(BaseModel):
    id:                     int
    nome:                   str
    nivel:                  str
    nota_capes:             Optional[int]
    instituicao_id:         int
    programa_aberto:        bool

    linhas_pesquisa: list[LinhaPesquisaResponse] = []
    etapas_processo: list[EtapaProcessoResponse] = []

    class Config:
        from_attributes = True

class ProgramaCapesResponse(BaseModel):
    id:                     int
    id_programa_capes:      int
    nome:                   str
    codigo:                 Optional[str]
    grau:                   Optional[str]
    conceito:               Optional[int]
    situacao:               Optional[str]
    instituicao_id:         Optional[int]
    area_avaliacao_id:      Optional[int]
    area_conhecimento_id:   Optional[int]

    class Config:
        from_attributes = True