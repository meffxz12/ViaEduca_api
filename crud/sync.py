"""
crud/sync.py — sincroniza programas (PPGs) e áreas com o banco local,
usando a tabela GrandeAreas já seedada (dificilmente muda).
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database import SessionLocal
from services import capes
from models import GrandeAreas, AreaAvaliacao, AreaConhecimento, ProgramaCapes, Instituicao
import unicodedata

logger = logging.getLogger("sync_capes")
def sincronizar_areas(db: Session, programas: list[dict]) -> None:
    grandes_cache = {
        (g.nome or "").strip().upper(): g
        for g in db.query(GrandeAreas).all()
    }
    avaliacao_cache = {a.id_capes: a for a in db.query(AreaAvaliacao).all()}
    conhecimento_cache = {c.id_capes: c for c in db.query(AreaConhecimento).all()}

    agora = datetime.now(timezone.utc)

    for p in programas:
        id_avaliacao = p.get("idAreaAvaliacao")
        id_conhecimento = p.get("idAreaConhecimento")
        nome_grande = (p.get("nomeGrandeAreaConhecimento") or "").strip().upper()

        grande = grandes_cache.get(nome_grande)
        if grande is None:
           logger.warning(
    "Grande área '%s' não encontrada no seed local — programa idPrograma=%s seguirá sem essa validação",
    p.get("nomeGrandeAreaConhecimento"), p.get("idPrograma"),
)

        # área avaliação: cria/atualiza
        avaliacao = avaliacao_cache.get(id_avaliacao)
        if avaliacao is None:
            avaliacao = AreaAvaliacao(id_capes=id_avaliacao)
            db.add(avaliacao)
            avaliacao_cache[id_avaliacao] = avaliacao

        avaliacao.nome = p.get("nomeAreaAvaliacao")
        avaliacao.sincronizado_em = agora
        db.flush()  # garante avaliacao.id preenchido antes de usar abaixo

        # área conhecimento: cria/atualiza (se veio no payload)
        if id_conhecimento is not None:
            conhecimento = conhecimento_cache.get(id_conhecimento)
            if conhecimento is None:
                conhecimento = AreaConhecimento(id_capes=id_conhecimento)
                db.add(conhecimento)
                conhecimento_cache[id_conhecimento] = conhecimento

            conhecimento.nome = p.get("nomeAreaConhecimento")
            conhecimento.sincronizado_em = agora
            conhecimento.area_avaliacao_id = avaliacao.id

    db.commit()


def sincronizar_catalogo_programas(db: Session, programas: list[dict]) -> None:
    instituicoes_cache = {
        (i.sigla or "").strip().upper(): i
        for i in db.query(Instituicao).all()
    }
    avaliacao_cache = {a.id_capes: a for a in db.query(AreaAvaliacao).all()}
    conhecimento_cache = {c.id_capes: c for c in db.query(AreaConhecimento).all()}
    catalogo_cache = {p.id_programa_capes: p for p in db.query(ProgramaCapes).all()}

    agora = datetime.now(timezone.utc)

    for p in programas:
        id_prog = p.get("idPrograma")
        if id_prog is None:
            continue

        sigla = (p.get("siglaIes") or "").strip().upper()
        instituicao = instituicoes_cache.get(sigla)
        if instituicao is None:
            logger.warning(
                "Instituição sigla='%s' não encontrada — programa idPrograma=%s ficará sem instituicao_id",
                p.get("siglaIes"), id_prog,
            )

        avaliacao = avaliacao_cache.get(p.get("idAreaAvaliacao"))
        conhecimento = conhecimento_cache.get(p.get("idAreaConhecimento"))

        catalogo = catalogo_cache.get(id_prog)
        if catalogo is None:
            catalogo = ProgramaCapes(id_programa_capes=id_prog)
            db.add(catalogo)
            catalogo_cache[id_prog] = catalogo

        catalogo.nome = p.get("nome")
        catalogo.codigo = p.get("codigo")
        catalogo.grau = p.get("grau")
        catalogo.conceito = p.get("conceito")
        catalogo.situacao = p.get("situacao")
        catalogo.sigla_ies = p.get("siglaIes")
        catalogo.instituicao_id = instituicao.id if instituicao else None
        catalogo.area_avaliacao_id = avaliacao.id if avaliacao else None
        catalogo.area_conhecimento_id = conhecimento.id if conhecimento else None
        catalogo.sincronizado_em = agora

    db.commit()

def sincronizar_instituicoes(db: Session, dados: list[dict]) -> None:
    existentes = {i.id_capes: i for i in db.query(Instituicao).all()}

    for item in dados:
        id_capes = item.get("idIes")
        if id_capes is None:
            continue

        instituicao = existentes.get(id_capes)
        if instituicao is None:
            instituicao = Instituicao(id_capes=id_capes)
            db.add(instituicao)
            existentes[id_capes] = instituicao

        instituicao.nome = item.get("nome")
        instituicao.sigla = item.get("sigla")

    db.commit()

def sincronizar() -> None:
    db = SessionLocal()
    try:
        sincronizar_instituicoes(db, capes.listar_instituicoes()["content"])

        programas = capes.listar_programas(size=50)
        sincronizar_areas(db, programas["content"])
        sincronizar_catalogo_programas(db, programas["content"])

        logger.info("Sincronização concluída: %d programas processados.", len(programas["content"]))
    except Exception:
        db.rollback()
        logger.exception("Falha na sincronização, nada foi salvo nesta run.")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sincronizar()


def normalizar(texto: str) -> str:
    texto = texto.strip().upper()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto