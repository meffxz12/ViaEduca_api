"""
services/firebase_service.py — envio de push via Firebase Cloud Messaging (FCM)
"""
import logging

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger("push")

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)


def enviar_notificacao(token: str, titulo: str, corpo: str):
    """Envia 1 push direto — usada no seu teste manual (test_ies.py)."""
    mensagem = messaging.Message(
        notification=messaging.Notification(
            title=titulo,
            body=corpo,
        ),
        token=token,
    )
    resposta = messaging.send(mensagem)
    return resposta


def enviar_push(fcm_token: str, titulo: str, corpo: str) -> bool:
    """
    Versão "segura" usada pelo crud/edital.py e crud/estudante.py —
    nunca levanta exceção (não pode travar a criação do edital/favorito
    só porque o push falhou), e ignora se o usuário não tiver token salvo.
    """
    if not fcm_token:
        return False
    try:
        enviar_notificacao(fcm_token, titulo, corpo)
        return True
    except Exception:
        logger.exception("Falha ao enviar push FCM")
        return False