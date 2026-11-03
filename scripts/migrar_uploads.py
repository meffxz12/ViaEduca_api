"""
Envia os PDFs que já estão em uploads/editais pro Supabase Storage,
mantendo o MESMO nome (os caminhos salvos no banco continuam valendo).

Uso (na pasta da API, com SUPABASE_URL e SUPABASE_SERVICE_KEY no .env):
    python scripts/migrar_uploads.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import storage  # noqa: E402

if not storage.supabase_ativo():
    sys.exit("Defina SUPABASE_URL e SUPABASE_SERVICE_KEY no .env primeiro.")

pasta = storage.PASTA_LOCAL
ok = pulados = erros = 0

for nome in sorted(os.listdir(pasta)):
    caminho = os.path.join(pasta, nome)
    if not os.path.isfile(caminho):
        continue
    with open(caminho, "rb") as f:
        resp = storage.enviar_supabase(nome, f.read(), upsert=False)
    if resp.status_code in (200, 201):
        ok += 1
        print("enviado :", nome)
    elif resp.status_code in (400, 409) and "xist" in resp.text:
        pulados += 1
        print("já existe:", nome)
    else:
        erros += 1
        print("ERRO    :", nome, resp.status_code, resp.text[:200])

print(f"\n{ok} enviados, {pulados} já existiam, {erros} com erro.")
