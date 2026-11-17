
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from crud import solicitacao_vinculo as crud
from dependencies import exigir_admin, pegar_sessao
from models import Programa, SolicitacaoVinculo, Usuario

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


# ------------------------------------------------------------------
# Schemas (só do painel admin)
# ------------------------------------------------------------------
class ProgramaAdmin(BaseModel):
    id: int
    nome: str
    nivel: str
    id_capes: str
    instituicao: Optional[str] = None


class CoordenadorAdmin(BaseModel):
    id: UUID
    nome_completo: str
    email: str
    email_institucional: str
    celular: Optional[str] = None
    instituicao: Optional[str] = None


class SolicitacaoAdminResponse(BaseModel):
    # campos antigos (o painel e qualquer outro cliente continuam funcionando)
    id: int
    programa_id: int
    coordenador_id: UUID
    status: str
    criado_em: datetime
    decidido_em: Optional[datetime] = None
    motivo_rejeicao: Optional[str] = None
    # novos
    programa: ProgramaAdmin
    coordenador: CoordenadorAdmin
    instituicao_confere: bool   # a instituição do coordenador é a mesma do programa?
    linhas_pesquisa: list[str] = []
    etapas_processo: list[str] = []


class RejeitarIn(BaseModel):
    motivo: Optional[str] = Field(default=None, max_length=200)

    @field_validator("motivo")
    @classmethod
    def _limpa(cls, v):
        v = (v or "").strip()
        return v or None


def _nome_inst(inst) -> Optional[str]:
    if inst is None:
        return None
    return inst.sigla or inst.nome


def _montar(s: SolicitacaoVinculo) -> SolicitacaoAdminResponse:
    prog = s.programa
    coord = s.coordenador
    user = coord.usuario
    etapas = sorted(s.etapas_processo_rascunho or [], key=lambda e: e.get("ordem", 0))
    return SolicitacaoAdminResponse(
        id=s.id,
        programa_id=s.programa_id,
        coordenador_id=s.coordenador_id,
        status=s.status,
        criado_em=s.criado_em,
        decidido_em=s.decidido_em,
        motivo_rejeicao=s.motivo_rejeicao,
        programa=ProgramaAdmin(
            id=prog.id,
            nome=prog.nome,
            nivel=prog.nivel,
            id_capes=prog.id_capes,
            instituicao=_nome_inst(prog.instituicao),
        ),
        coordenador=CoordenadorAdmin(
            id=coord.usuario_id,
            nome_completo=user.nome_completo,
            email=user.email,
            email_institucional=coord.email_institucional,
            celular=user.celular,
            instituicao=_nome_inst(coord.instituicao),
        ),
        instituicao_confere=prog.instituicao_id == coord.instituicao_id,
        linhas_pesquisa=[l.get("descricao", "") for l in (s.linhas_pesquisa_rascunho or [])],
        etapas_processo=[e.get("descricao", "") for e in etapas],
    )


def _buscar_pendente(db: Session, solicitacao_id: int) -> SolicitacaoVinculo:
    s = crud.buscar(db, solicitacao_id)
    if s is None or s.status != "pendente":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada ou já decidida")
    return s


# ------------------------------------------------------------------
@admin_router.get("/solicitacoes", response_model=list[SolicitacaoAdminResponse])
def listar_solicitacoes(
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_admin),
):
    return [_montar(s) for s in crud.listar_pendentes(db)]


@admin_router.post("/solicitacoes/{solicitacao_id}/aprovar", response_model=SolicitacaoAdminResponse)
def aprovar_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_admin),
):
    solicitacao = _buscar_pendente(db, solicitacao_id)

    # Dois coordenadores podem ter pedido o mesmo programa. Se outro já foi
    # aprovado, aprovar este aqui trocaria o coordenador sem ninguém perceber
    # (e duplicaria linhas de pesquisa e etapas).
    programa = db.query(Programa).filter(Programa.id == solicitacao.programa_id).first()
    if programa is not None and programa.coordenador_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este programa já tem um coordenador vinculado. Rejeite esta solicitação.",
        )

    return _montar(crud.aprovar(db, solicitacao, usuario_logado.id))


@admin_router.post("/solicitacoes/{solicitacao_id}/rejeitar", response_model=SolicitacaoAdminResponse)
def rejeitar_solicitacao(
    solicitacao_id: int,
    dados: RejeitarIn,
    db: Session = Depends(pegar_sessao),
    usuario_logado: Usuario = Depends(exigir_admin),
):
    solicitacao = _buscar_pendente(db, solicitacao_id)
    return _montar(crud.rejeitar(db, solicitacao, usuario_logado.id, dados.motivo))