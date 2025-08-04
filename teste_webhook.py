# post_webhook.py
import requests

BASE_URL = "http://localhost:5678"  # troque pelo seu domínio do n8n
# Enquanto o workflow estiver inativo (active=false):
url = f"https://nutec.app.n8n.cloud/webhook-test/7c62511d-0854-4d02-9b6f-ea195e09cb80"

# Se ATIVAR o workflow, use a linha abaixo:
# url = f"{BASE_URL}/webhook/7c62511d-0854-4d02-9b6f-ea195e09cb80"

payload = {"ping": "hello n8n"}  # qualquer JSON simples

resp = requests.post(url, json=payload)
print(resp.status_code)
print(resp.text)
