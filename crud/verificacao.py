"""
crud/verificacao.py — códigos de 6 dígitos (verificação de e-mail e reset de senha)

Segurança:
- o código é guardado só como HASH (SHA-256 + SECRET_KEY), nunca em texto puro
- expira (15 min), é de uso único e tem no máx. 5 tentativas erradas
- pedir um novo código invalida os anteriores
- intervalo mínimo de 60s entre pedidos (anti-spam de e-mail)
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import CodigoVerificacao, Usuario
from security import SECRET_KEY

VALIDADE_MIN = 15
MAX_TENTATIVAS = 5
INTERVALO_REENVIO_S = 60


def verificacao_exigida() -> bool:
    """
    Chave geral da verificação de e-mail (variável EXIGIR_VERIFICACAO_EMAIL no .env).

    false (padrão): cadastro e login funcionam como antes, ninguém é barrado e
                    nenhum código é enviado no cadastro.
    true:           e-mail precisa ser confirmado por código pra conseguir entrar.
                    Só ligue depois de verificar um domínio no Resend
                    (senão ninguém além de você recebe o código).
    """
    return os.getenv("EXIGIR_VERIFICACAO_EMAIL", "false").strip().lower() in ("1", "true", "sim", "yes")


def _hash(codigo: str) -> str:
    return hmac.new(SECRET_KEY.encode(), codigo.encode(), hashlib.sha256).hexdigest()


def pode_reenviar(db: Session, usuario_id, finalidade: str) -> bool:
    ultimo = (
        db.query(CodigoVerificacao)
        .filter(CodigoVerificacao.usuario_id == usuario_id,
                CodigoVerificacao.finalidade == finalidade)
        .order_by(CodigoVerificacao.criado_em.desc())
        .first()
    )
    if not ultimo:
        return True
    return (datetime.now() - ultimo.criado_em).total_seconds() >= INTERVALO_REENVIO_S


def gerar_codigo(db: Session, usuario_id, finalidade: str) -> str:
    """Invalida códigos antigos dessa finalidade e cria um novo. Devolve o código em texto puro (pra enviar)."""
    db.query(CodigoVerificacao).filter(
        CodigoVerificacao.usuario_id == usuario_id,
        CodigoVerificacao.finalidade == finalidade,
        CodigoVerificacao.usado.is_(False),
    ).update({CodigoVerificacao.usado: True}, synchronize_session=False)

    codigo = f"{secrets.randbelow(1_000_000):06d}"
    db.add(CodigoVerificacao(
        usuario_id=usuario_id,
        finalidade=finalidade,
        codigo_hash=_hash(codigo),
        expira_em=datetime.now() + timedelta(minutes=VALIDADE_MIN),
    ))
    db.commit()
    return codigo


def validar_codigo(db: Session, usuario_id, finalidade: str, codigo: str) -> bool:
    """True se o código confere (e consome ele). Conta tentativas erradas."""
    registro = (
        db.query(CodigoVerificacao)
        .filter(CodigoVerificacao.usuario_id == usuario_id,
                CodigoVerificacao.finalidade == finalidade,
                CodigoVerificacao.usado.is_(False))
        .order_by(CodigoVerificacao.criado_em.desc())
        .first()
    )
    if not registro or registro.expira_em < datetime.now() or registro.tentativas >= MAX_TENTATIVAS:
        return False

    if not hmac.compare_digest(registro.codigo_hash, _hash(codigo.strip())):
        registro.tentativas += 1
        db.commit()
        return False

    registro.usado = True
    db.commit()
    return True


def marcar_email_verificado(db: Session, usuario: Usuario) -> None:
    usuario.email_verificado = True
    db.commit()