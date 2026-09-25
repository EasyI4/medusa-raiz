import json
import os


class FirebaseNotConfigured(Exception):
    """O Firebase Admin ainda não tem credencial no ambiente."""


def public_config():
    """Configuração pública do Firebase Web. A chave de API do cliente não é segredo."""
    values = {
        "apiKey": os.getenv("FIREBASE_API_KEY", "").strip(),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", "").strip(),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", "").strip(),
        "appId": os.getenv("FIREBASE_APP_ID", "").strip(),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", "").strip(),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", "").strip(),
    }
    required = (
        ("apiKey", "FIREBASE_API_KEY"),
        ("authDomain", "FIREBASE_AUTH_DOMAIN"),
        ("projectId", "FIREBASE_PROJECT_ID"),
        ("appId", "FIREBASE_APP_ID"),
    )
    missing = [env_name for key, env_name in required if not values[key]]
    config = {key: value for key, value in values.items() if value}
    return config, missing


def _init_firebase():
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        return

    raw = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
    path = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()

    if raw:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
        return

    if path and os.path.exists(path):
        firebase_admin.initialize_app(credentials.Certificate(path))
        return

    raise FirebaseNotConfigured(
        "Firebase Admin não configurado. Defina FIREBASE_CREDENTIALS_JSON ou FIREBASE_CREDENTIALS_PATH."
    )


def verify_bearer(header):
    """Confere o ID token do Firebase enviado em Authorization: Bearer."""
    if not header or not header.startswith("Bearer "):
        raise PermissionError("Entre na conta para enviar perguntas.")

    token = header.split(" ", 1)[1].strip()
    if not token:
        raise PermissionError("Entre na conta para enviar perguntas.")

    _init_firebase()
    from firebase_admin import auth

    try:
        return auth.verify_id_token(token)
    except Exception as error:
        raise PermissionError("Sessão inválida ou expirada. Entre novamente.") from error
