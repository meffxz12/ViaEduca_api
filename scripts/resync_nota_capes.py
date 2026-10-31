"""
scripts/resync_nota_capes.py — atualiza Programa.nota_capes a partir do
ProgramaCapes.conceito já sincronizado, só pra programas SEM coordenador.
"""
from database import SessionLocal
from models import Programa, ProgramaCapes

def resync():
    db = SessionLocal()
    try:
        programas = db.query(Programa).filter(Programa.coordenador_id.is_(None)).all()

        atualizados = 0

        for programa in programas:
            id_capes_puro = programa.id_capes.split("-")[0]

            catalogo = (
                db.query(ProgramaCapes)
                .filter(ProgramaCapes.id_programa_capes == int(id_capes_puro))
                .first()
            )
            if catalogo is None or not catalogo.conceito:
                continue

            if programa.nota_capes != catalogo.conceito:
                programa.nota_capes = catalogo.conceito
                atualizados += 1

        db.commit()
        print(f"\nConcluído: {atualizados} programas atualizados.")
    finally:
        db.close()

if __name__ == "__main__":
    resync()