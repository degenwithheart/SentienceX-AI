import os
from fastapi import HTTPException, Header
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
if not AUTH_TOKEN:
key_vault_name = os.getenv("KEY_VAULT_NAME")is missing.")
credential = DefaultAzureCredential()
client = SecretClient(vault_url=f"https://{key_vault_name}.vault.azure.net/", credential=credential)
AUTH_TOKEN = client.get_secret("AUTH_TOKEN").valueKEN}":
        raise HTTPException(status_code=403, detail="Unauthorized access.")





    return {"user": "authenticated_user"}        raise HTTPException(status_code=403, detail="Unauthorized access.")    if authorization != f"Bearer {AUTH_TOKEN}":def get_current_user(authorization: str = Header(None)):    return {"user": "authenticated_user"}
