"""
email_service.py — envio de e-mail pela API do Resend (https://resend.com).

Variáveis no .env:
    RESEND_API_KEY=re_xxxxxxxx
    RESEND_FROM=ViaEduca <onboarding@resend.dev>     (opcional)

IMPORTANTE: enquanto você não verificar um domínio seu no Resend, o remetente
"onboarding@resend.dev" só consegue enviar para o e-mail da PRÓPRIA conta Resend.
Pra mandar pra qualquer usuário, verifique um domínio em resend.com/domains e
use um remetente dele (ex.: ViaEduca <nao-responda@seudominio.com.br>).

Sem RESEND_API_KEY o e-mail NÃO é enviado: o código aparece no log do servidor.
"""
import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger("viaeduca.email")

RESEND_URL = "https://api.resend.com/emails"


def _enviar(destino: str, assunto: str, texto: str, html: str) -> None:
    chave = os.getenv("RESEND_API_KEY")
    remetente = os.getenv("RESEND_FROM") or "ViaEduca <onboarding@resend.dev>"

    if not chave:
        log.warning("RESEND_API_KEY não configurada — e-mail para %s NÃO enviado.", destino)
        print(f"[EMAIL DESLIGADO] para {destino} | {assunto}\n{texto}")
        return

    corpo = json.dumps({
        "from": remetente,
        "to": [destino],
        "subject": assunto,
        "text": texto,
        "html": html,
    }).encode()

    req = urllib.request.Request(
        RESEND_URL,
        data=corpo,
        method="POST",
        headers={
            "Authorization": f"Bearer {chave}",
            "Content-Type": "application/json",
            # sem User-Agent o Resend (Cloudflare) pode recusar com 403
            "User-Agent": "viaeduca-api/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            log.info("E-mail enviado para %s (HTTP %s)", destino, resp.status)
    except urllib.error.HTTPError as e:
        # 403/422 aqui quase sempre = remetente/domínio não verificado
        log.error("Resend recusou o e-mail para %s: HTTP %s %s",
                  destino, e.code, e.read().decode(errors="replace"))
    except Exception:
        # nunca derruba a requisição por falha de e-mail
        log.exception("Falha ao enviar e-mail para %s", destino)


def _html(titulo: str, intro: str, codigo: str, minutos: int) -> str:
    return f"""
<div style="font-family:Arial,sans-serif;max-width:420px;margin:auto;padding:24px;
            border:1px solid #e3e6f0;border-radius:12px">
  <h2 style="color:#0A1946;margin:0 0 12px">{titulo}</h2>
  <p style="color:#444;font-size:14px">{intro}</p>
  <div style="font-size:32px;letter-spacing:8px;font-weight:700;color:#0A1946;
              background:#f2f4fa;border-radius:8px;text-align:center;padding:16px;margin:20px 0">
    {codigo}
  </div>
  <p style="color:#777;font-size:12px">O código vale por {minutos} minutos.
  Se não foi você, ignore este e-mail.</p>
</div>"""


def enviar_codigo_verificacao_email(destino: str, nome: str, codigo: str, minutos: int) -> None:
    primeiro = (nome or "").split(" ")[0] or "tudo bem"
    texto = (f"Olá, {primeiro}!\n\nSeu código para confirmar o e-mail no ViaEduca é: {codigo}\n"
             f"Ele vale por {minutos} minutos.\n\nSe não foi você, ignore este e-mail.")
    _enviar(destino, "Confirme seu e-mail — ViaEduca", texto,
            _html("Confirme seu e-mail", f"Olá, {primeiro}! Use o código abaixo no app:", codigo, minutos))


def enviar_codigo_redefinicao_senha(destino: str, nome: str, codigo: str, minutos: int) -> None:
    primeiro = (nome or "").split(" ")[0] or "tudo bem"
    texto = (f"Olá, {primeiro}!\n\nSeu código para redefinir a senha no ViaEduca é: {codigo}\n"
             f"Ele vale por {minutos} minutos.\n\nSe você não pediu, ignore este e-mail.")
    _enviar(destino, "Redefinir senha — ViaEduca", texto,
            _html("Redefinir senha", f"Olá, {primeiro}! Use o código abaixo no app para criar uma nova senha:", codigo, minutos))