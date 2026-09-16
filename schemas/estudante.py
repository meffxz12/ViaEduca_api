"""
schemas/estudante.py — contratos de entrada e saída da API pro estudante

Cobre: busca de programa, favoritar/desfavoritar e notificações (que são
geradas automaticamente por um trigger no banco quando o coordenador posta
um novo arquivo no edital de um programa favoritado).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr

from schemas.programas import ProgramaListItem


# ---------------------------------------------------------------------------
# Busca de programa — mesmo item de listagem do programa, com a flag de
# favorito calculada pro estudante logado
# ---------------------------------------------------------------------------
class ProgramaBuscaItem(ProgramaListItem):
    favoritado: bool = False


# ---------------------------------------------------------------------------
# Favoritos
# ---------------------------------------------------------------------------
class ProgramaFavoritoResponse(BaseModel):
    favoritado_em: datetime
    programa:      ProgramaListItem

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Notificações
# ---------------------------------------------------------------------------
class NotificacaoResponse(BaseModel):
    id:             int
    titulo:         str
    lida:           bool
    criado_em:      datetime

    arquivo_id:     Optional[int] = None
    arquivo_titulo: Optional[str] = None
    arquivo_url:    Optional[str] = None
    edital_id:      Optional[int] = None
    edital_titulo:  Optional[str] = None
    programa_id:    Optional[int] = None
    programa_nome:  Optional[str] = None

    class Config:
        from_attributes = True


class ContadorNotificacoesResponse(BaseModel):
    nao_lidas: int

class EstudantePerfilResponse(BaseModel):
    id: UUID
    nome_completo: str
    email: EmailStr
    titulacao_atual: Optional[str]
    area_titulacao_id: Optional[int]
    area_titulacao_nome: Optional[str]

    class Config:
        from_attributes = True