import base64
import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger("push")

_ARQUIVO_LOCAL = "firebase-service-account.json"
_iniciado = False
CANAL_ANDROID = "high_importance_channel"


def _carregar_credencial():
    bruto = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if bruto:
        # strict=False: aceita quebras de linha "de verdade" dentro da private_key,
        # caso o painel converta os \n em linhas reais ao colar a variável
        return credentials.Certificate(json.loads(bruto, strict=False))

    b64 = os.getenv("FIREBASE_CREDENTIALS_B64")
    if b64:
        return credentials.Certificate(json.loads(base64.b64decode(b64), strict=False))

    if os.path.exists(_ARQUIVO_LOCAL):
        return credentials.Certificate(_ARQUIVO_LOCAL)

    return None


def _iniciar() -> bool:
    """Inicializa o Firebase uma única vez. Devolve False se não houver credencial."""
    global _iniciado
    if _iniciado or firebase_admin._apps:
        _iniciado = True
        return True

    try:
        cred = _carregar_credencial()
        if cred is None:
            logger.warning(
                "Firebase sem credenciais (FIREBASE_CREDENTIALS_JSON / _B64 / arquivo "
                "local): push DESLIGADO."
            )
            return False
        firebase_admin.initialize_app(cred)
        _iniciado = True
        return True
    except Exception:
        logger.exception("Falha ao inicializar o Firebase: push DESLIGADO.")
        return False


def enviar_notificacao(token: str, titulo: str, corpo: str, dados: dict | None = None):
    """Envia 1 push direto (levanta exceção se falhar).

    `dados` vai junto como payload (programa_id, edital_id...) — é o que o app
    usa pra abrir a tela certa quando a pessoa toca na notificação.
    FCM só aceita strings nos valores, por isso o str() abaixo."""
    if not _iniciar():
        raise RuntimeError("Firebase não configurado")

    mensagem = messaging.Message(
        notification=messaging.Notification(
            title=titulo,
            body=corpo,
        ),
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id=CANAL_ANDROID,
                default_sound=True,
                priority="max",
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default"),
            ),
        ),
        data={str(k): str(v) for k, v in dados.items()} if dados else None,
        token=token,
    )
    return messaging.send(mensagem)


def enviar_push(fcm_token: str, titulo: str, corpo: str, dados: dict | None = None) -> bool:
    """
    Versão "segura" usada pelo crud/arquivo_edital.py e services/notificador.py —
    nunca levanta exceção (não pode travar a criação do edital/favorito
    só porque o push falhou), e ignora se o usuário não tiver token salvo.
    """
    if not fcm_token:
        return False

    try:
        enviar_notificacao(fcm_token, titulo, corpo, dados)
        logger.info("Push FCM enviado")
        return True
    except Exception:
        logger.exception("Falha ao enviar push FCM")
        return False