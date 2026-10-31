"""
scripts/debug_capes.py — busca um programa específico na API da Sucupira
e mostra TODOS os campos do JSON bruto, sem filtrar nada.
"""
import json
from services.capes import listar_programas

ID_PROCURADO = 210451  # o programa que você conferiu manualmente

resultado = listar_programas(size=50)

encontrado = None
for p in resultado["content"]:
    if p.get("idPrograma") == ID_PROCURADO:
        encontrado = p
        break

if encontrado is None:
    print(f"Programa idPrograma={ID_PROCURADO} não apareceu nessa sincronização.")
else:
    print(json.dumps(encontrado, indent=2, ensure_ascii=False))