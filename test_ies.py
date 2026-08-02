from services.firebase_service import enviar_notificacao

token = "dfdVIWDjQqCKqJgtl1qe8a:APA91bHo_XocXidHGGCiysLXMbWXGK2vBxOjf2gKca6D7uDhpq056tqD7VngyxPrBj6WTPzF65CB2gwR71ai6ccOZ_-gXXg-Sg3nWyCQnYDBqcFR7239ns8"

resposta = enviar_notificacao(
    token=token,
    titulo="ViaEduca",
    corpo="so testando amigo 😎",
)

print("Mensagem enviada!")
print("ID:", resposta)