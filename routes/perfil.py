import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from dependencies import get_usuario_atual, pegar_sessao
from models import Estudante, Usuario
from security import criar_hash_senha, verificar_senha

perfil_router = APIRouter(prefix="/perfil", tags=["Perfil"])

TITULACOES_VALIDAS = {"Graduação incompleta", "Graduação", "Especialização", "Mestrado", "Doutorado"}


class PerfilUpdate(BaseModel):
    nome_completo: Optional[str] = Field(default=None, max_length=150)
    celular: Optional[str] = None
    titulacao_atual: Optional[str] = None
    area_titulacao_id: Optional[int] = None

    @field_validator("nome_completo")
    @classmethod
    def _nome(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Informe seu nome completo.")
        return v

    @field_validator("celular")
    @classmethod
    def _celular(cls, v):
        if v is None:
            return v
        digitos = re.sub(r"\D", "", v)
        if len(digitos) not in (10, 11):
            raise ValueError("Celular inválido. Use DDD + número.")
        return digitos


class AlterarSenha(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8, max_length=128)


def _resposta(usuario: Usuario) -> dict:
    # mesmas chaves do GET /auth/me, pro Flutter reaproveitar o parse
    return {
        "id": str(usuario.id),
        "tipo": usuario.tipo,
        "nome_completo": usuario.nome_completo,
        "email": usuario.email,
        "celular": usuario.celular,
        "foto_url": usuario.foto_url,
        "criado_em": usuario.criado_em.isoformat(),
    }


@perfil_router.patch("")
def atualizar_perfil(
    dados: PerfilUpdate,
    db: Session = Depends(pegar_sessao),
    usuario: Usuario = Depends(get_usuario_atual),
):
    campos = dados.model_dump(exclude_unset=True)

    if campos.get("nome_completo"):
        usuario.nome_completo = campos["nome_completo"]

    if "celular" in campos and campos["celular"]:
        em_uso = (
            db.query(Usuario)
            .filter(Usuario.celular == campos["celular"], Usuario.id != usuario.id)
            .first()
        )
        if em_uso:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Este celular já está cadastrado em outra conta.",
            )
        usuario.celular = campos["celular"]

    dados_estudante = {"titulacao_atual", "area_titulacao_id"} & campos.keys()
    if dados_estudante:
        if usuario.tipo != "estudante":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Titulação e área da titulação só se aplicam a estudantes.",
            )

        estudante = (
            db.query(Estudante).filter(Estudante.usuario_id == usuario.id).first()
        )
        if estudante is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil de estudante não encontrado.")

        if "titulacao_atual" in campos:
            if campos["titulacao_atual"] not in TITULACOES_VALIDAS:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Titulação inválida.")
            estudante.titulacao_atual = campos["titulacao_atual"]

        if "area_titulacao_id" in campos and campos["area_titulacao_id"] is not None:
            estudante.area_titulacao_id = campos["area_titulacao_id"]

    db.commit()
    db.refresh(usuario)
    return _resposta(usuario)


@perfil_router.post("/alterar-senha", status_code=status.HTTP_204_NO_CONTENT)
def alterar_senha(
    dados: AlterarSenha,
    db: Session = Depends(pegar_sessao),
    usuario: Usuario = Depends(get_usuario_atual),
):
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Senha atual incorreta.")

    if verificar_senha(dados.nova_senha, usuario.senha_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A nova senha deve ser diferente da atual.",
        )

    usuario.senha_hash = criar_hash_senha(dados.nova_senha)
    db.commit()