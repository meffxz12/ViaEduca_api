
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from crud import usuario as crud_usuario
from crud import verificacao as crud
from dependencies import pegar_sessao
from services.email import enviar_codigo_redefinicao_senha, enviar_codigo_verificacao_email
from security import criar_hash_senha

verificacao_router = APIRouter(prefix="/auth", tags=["Verificação de e-mail / Senha"])

MSG_GENERICA = {"ok": True, "mensagem": "Se o e-mail estiver cadastrado, enviamos um código."}


class EmailRequest(BaseModel):
    email: EmailStr


class ConfirmarEmailRequest(BaseModel):
    email: EmailStr
    codigo: str = Field(..., min_length=6, max_length=6)


class RedefinirSenhaRequest(BaseModel):
    email: EmailStr
    codigo: str = Field(..., min_length=6, max_length=6)
    nova_senha: str = Field(..., min_length=8, max_length=128)


def disparar_verificacao_email(db: Session, usuario, tasks: BackgroundTasks) -> None:
    """Usada também pelo cadastro: gera o código e agenda o envio do e-mail.
    Com a verificação desligada (EXIGIR_VERIFICACAO_EMAIL=false) não faz nada."""
    if not crud.verificacao_exigida():
        return
    codigo = crud.gerar_codigo(db, usuario.id, "email")
    tasks.add_task(enviar_codigo_verificacao_email, usuario.email, usuario.nome_completo,
                   codigo, crud.VALIDADE_MIN)


@verificacao_router.get("/config")
def config_verificacao():
    """O app consulta isso pra saber se deve abrir a tela de confirmar e-mail."""
    return {"verificacao_email": crud.verificacao_exigida()}


@verificacao_router.post("/verificar-email/enviar")
def reenviar_verificacao(dados: EmailRequest, tasks: BackgroundTasks,
                         db: Session = Depends(pegar_sessao)):
    usuario = crud_usuario.buscar_por_email(db, dados.email)
    # Sempre a mesma resposta (conta existindo ou não, já verificada ou não,
    # dentro ou fora do intervalo de 60s) — assim ninguém descobre quais
    # e-mails estão cadastrados. O app já impede reenvio antes de 60s.
    if usuario and not usuario.email_verificado \
            and crud.pode_reenviar(db, usuario.id, "email"):
        disparar_verificacao_email(db, usuario, tasks)
    return MSG_GENERICA


@verificacao_router.post("/verificar-email/confirmar")
def confirmar_email(dados: ConfirmarEmailRequest, db: Session = Depends(pegar_sessao)):
    usuario = crud_usuario.buscar_por_email(db, dados.email)
    if not usuario or not crud.validar_codigo(db, usuario.id, "email", dados.codigo):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código inválido ou expirado.")
    crud.marcar_email_verificado(db, usuario)
    return {"ok": True}


@verificacao_router.post("/esqueci-senha")
def esqueci_senha(dados: EmailRequest, tasks: BackgroundTasks,
                  db: Session = Depends(pegar_sessao)):
    usuario = crud_usuario.buscar_por_email(db, dados.email)
    if usuario and crud.pode_reenviar(db, usuario.id, "senha"):
        codigo = crud.gerar_codigo(db, usuario.id, "senha")
        tasks.add_task(enviar_codigo_redefinicao_senha, usuario.email, usuario.nome_completo,
                       codigo, crud.VALIDADE_MIN)
    return MSG_GENERICA


@verificacao_router.post("/redefinir-senha")
def redefinir_senha(dados: RedefinirSenhaRequest, db: Session = Depends(pegar_sessao)):
    usuario = crud_usuario.buscar_por_email(db, dados.email)
    if not usuario or not crud.validar_codigo(db, usuario.id, "senha", dados.codigo):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código inválido ou expirado.")
    usuario.senha_hash = criar_hash_senha(dados.nova_senha)
    # invalida qualquer outro código de senha ainda em aberto
    from models import CodigoVerificacao
    db.query(CodigoVerificacao).filter(
        CodigoVerificacao.usuario_id == usuario.id,
        CodigoVerificacao.usado.is_(False),
    ).update({CodigoVerificacao.usado: True}, synchronize_session=False)
    # quem recebeu o código no e-mail provou que é dono dele
    usuario.email_verificado = True
    db.commit()
    return {"ok": True}