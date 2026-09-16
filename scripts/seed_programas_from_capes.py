# scripts/seed_programas_from_capes.py
from database import SessionLocal
from models import ProgramaCapes, Programa
from sqlalchemy.exc import IntegrityError

MAPA_NIVEL = {
    "Mestrado": ["MA"],
    "Doutorado": ["D"],
    "Mestrado Profissional": ["MP"],
    "Mestrado/Doutorado": ["MA", "D"],
    "Mestrado Profissional/Doutorado Profissional": ["MP"],
    "Doutorado Profissional": [],
}


def popular_programas():
    db = SessionLocal()
    try:
        capes_list = db.query(ProgramaCapes).all()
        criados, pulados, duplicados = 0, 0, 0

        for c in capes_list:
            grau = (c.grau or "").strip()
            niveis = MAPA_NIVEL.get(grau)

            if niveis is None:
                print(f"[PULADO] grau desconhecido: {grau!r} (id_capes={c.id_programa_capes})")
                pulados += 1
                continue
            if not niveis:
                print(f"[PULADO] grau sem suporte ainda: {grau!r} (id_capes={c.id_programa_capes})")
                pulados += 1
                continue

            nota = None
            try:
                nota_int = int(c.conceito)
                if 1 <= nota_int <= 7:
                    nota = nota_int
            except (TypeError, ValueError):
                pass

            for nivel in niveis:
                id_capes_final = (
                    str(c.id_programa_capes)
                    if len(niveis) == 1
                    else f"{c.id_programa_capes}-{nivel}"
                )

                # já existe esse id_capes exato?
                if db.query(Programa).filter(Programa.id_capes == id_capes_final).first():
                    continue

                # já existe um programa com a mesma inst+nome+nível (duplicata na origem)?
                if db.query(Programa).filter(
                    Programa.instituicao_id == c.instituicao_id,
                    Programa.nome == c.nome,
                    Programa.nivel == nivel,
                ).first():
                    print(f"[DUPLICADO] {c.nome!r} nivel={nivel} instituicao_id={c.instituicao_id} "
                          f"(id_capes={c.id_programa_capes}, já existe outro registro igual)")
                    duplicados += 1
                    continue

                novo = Programa(
                    coordenador_id=None,
                    instituicao_id=c.instituicao_id,
                    nome=c.nome,
                    id_capes=id_capes_final,
                    nivel=nivel,
                    area_avaliacao_id=c.area_avaliacao_id,
                    area_conhecimento_id=c.area_conhecimento_id,
                    nota_capes=nota,
                    programa_aberto=False,
                )

                # savepoint por registro: se ESSE der erro, só ele é descartado
                try:
                    with db.begin_nested():
                        db.add(novo)
                    criados += 1
                except IntegrityError as e:
                    print(f"[ERRO] falha ao inserir {c.nome!r} nivel={nivel}: {e.orig}")
                    duplicados += 1

        db.commit()
        print(f"\nConcluído: {criados} criados, {pulados} pulados (grau), "
              f"{duplicados} duplicados/erros.")
    finally:
        db.close()


if __name__ == "__main__":
    popular_programas()