"""
services/lembretes.py — avisos automáticos de prazo (rodam todo dia).

Pra quem favoritou o programa, dos editais de programas ABERTOS (programa_aberto):
  - no dia em que as inscrições começam ("Inscrições abertas hoje")
  - 7, 3 e 1 dia antes do fim das inscrições
  - no último dia

Não repete aviso (a mesma notificação nunca é criada duas vezes), então pode rodar
quantas vezes quiser. A data do aviso vai no texto: se o coordenador mudar o prazo,
os avisos novos valem de novo.

No main.py:
    from services.lembretes import iniciar_agendador

    @app.on_event("startup")
    def _iniciar_lembretes():
        iniciar_agendador()
"""
import logging
import threading
import time
from datetime import date, datetime

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Edital, Programa
from services.notificador import formatar_data, notificar_favoritos

logger = logging.getLogger("lembretes")

DIAS_DE_AVISO = (7, 3, 1)


def _mensagens(edital: Edital, hoje: date) -> list[str]:
    msgs = []
    titulo = edital.titulo

    if edital.data_inicio_inscricao == hoje:
        msgs.append(f"Inscrições abertas hoje (a partir de {formatar_data(hoje)}): {titulo}")

    if edital.data_fim_inscricao:
        fim = formatar_data(edital.data_fim_inscricao)
        dias = (edital.data_fim_inscricao - hoje).days
        if dias == 0:
            msgs.append(f"Último dia de inscrição ({fim}): {titulo}")
        elif dias in DIAS_DE_AVISO:
            palavra = "dia" if dias == 1 else "dias"
            msgs.append(f"Faltam {dias} {palavra} para o fim das inscrições ({fim}): {titulo}")
    return msgs


def enviar_lembretes(db: Session, hoje: date | None = None) -> dict:
    """Roda os avisos de prazo para 'hoje' (ou uma data simulada, pra testar)."""
    hoje = hoje or date.today()
    # Quem abre/fecha é o programa: programa fechado não recebe lembrete de prazo.
    editais = (
        db.query(Edital)
        .join(Programa, Programa.id == Edital.programa_id)
        .filter(Programa.programa_aberto.is_(True), Edital.status != "rascunho")
        .all()
    )

    avisos = 0
    estudantes = 0
    for edital in editais:
        for msg in _mensagens(edital, hoje):
            n = notificar_favoritos(
                db, edital.programa_id, edital.id, msg, push=True, evitar_duplicada=True
            )
            if n:
                avisos += 1
                estudantes += n
    db.commit()

    logger.info("Lembretes de %s: %s avisos para %s estudantes", hoje, avisos, estudantes)
    return {"data": hoje.isoformat(), "avisos": avisos, "notificacoes_criadas": estudantes}


def iniciar_agendador(intervalo_segundos: int = 3600, hora_inicio: int = 8, hora_fim: int = 21):
    """Thread em segundo plano: confere de hora em hora e só envia entre 8h e 21h
    (ninguém quer push de madrugada). Não repete aviso, então é seguro."""

    def _loop():
        time.sleep(15)  # deixa o servidor terminar de subir
        while True:
            if hora_inicio <= datetime.now().hour < hora_fim:
                try:
                    with SessionLocal() as db:
                        enviar_lembretes(db)
                except Exception:
                    logger.exception("Falha ao enviar lembretes")
            time.sleep(intervalo_segundos)

    threading.Thread(target=_loop, daemon=True, name="lembretes").start()