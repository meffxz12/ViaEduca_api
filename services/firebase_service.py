"""
services/firebase_service.py — envio de push via Firebase Cloud Messaging (FCM)

Credenciais, em ordem de prioridade:
  1. FIREBASE_CREDENTIALS_JSON -> conteúdo do JSON da service account (produção / Railway)
  2. FIREBASE_CREDENTIALS_B64  -> o mesmo JSON em base64 (se o painel estragar aspas/quebras de linha)
  3. arquivo firebase-service-account.json (desenvolvimento local; fica no .gitignore)

Se nenhuma existir, o push fica DESLIGADO e o resto da API continua funcionando
(antes o servidor nem subia sem o arquivo, porque a leitura era no import).
"""
import base64
import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger("push")

_ARQUIVO_LOCAL = "firebase-service-account.json"
_iniciado = False

# --- Configuração visual da notificação no Android ---------------------------
# Esses valores precisam existir no app:
#   - CANAL_ANDROID: canal criado no app com importância ALTA
#   - ICONE_ANDROID: PNG branco com fundo transparente em res/drawable (ic_notification)
CANAL_ANDROID = "high_importance_channel"
ICONE_ANDROID = "ic_notification"
COR_ANDROID = "#1E88E5"


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
                icon=ICONE_ANDROID,
                color=COR_ANDROID,
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
    Versão "segura" usada pelo crud/arquivo_edital.py e crud/estudante.py —
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