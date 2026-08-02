from database import SessionLocal
from services.capes import (
    listar_instituicoes,
    listar_areas_avaliacao,
    listar_areas_conhecimento,
)
from crud.sync import (
    sincronizar_instituicoes,
    sincronizar_areas_avaliacao,
    sincronizar_areas_conhecimento,
)

db = SessionLocal()

sincronizar_instituicoes(db, listar_instituicoes())
sincronizar_areas_avaliacao(db, listar_areas_avaliacao())
sincronizar_areas_conhecimento(db, listar_areas_conhecimento())

db.close()