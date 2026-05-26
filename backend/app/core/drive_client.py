from functools import lru_cache
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.core.config import PROJECT_ROOT, settings


SCOPES = ["https://www.googleapis.com/auth/drive"]


def _resolve_project_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@lru_cache
def get_drive_service():
    if settings.GOOGLE_DRIVE_AUTH_MODE == "oauth":
        credentials = _load_oauth_credentials()
    else:
        credentials = _load_service_account_credentials()

    return build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def _load_oauth_credentials():
    client_file = _resolve_project_path(settings.GOOGLE_DRIVE_OAUTH_CLIENT_FILE)
    token_file = _resolve_project_path(settings.GOOGLE_DRIVE_OAUTH_TOKEN_FILE)

    credentials = None

    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    else:
        if not client_file.exists():
            raise RuntimeError(
                f"Missing OAuth client file: {client_file}. "
                "Create OAuth Desktop client JSON, rename it to "
                "google-drive-oauth-client.json, and put it in ./credentials."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_file),
            SCOPES,
        )
        credentials = flow.run_local_server(port=0, prompt="consent")

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")

    return credentials


def _load_service_account_credentials():
    credentials_file = _resolve_project_path(settings.GOOGLE_APPLICATION_CREDENTIALS)

    if not credentials_file.exists():
        raise RuntimeError(f"Missing Service Account JSON file: {credentials_file}")

    return service_account.Credentials.from_service_account_file(
        str(credentials_file),
        scopes=SCOPES,
    )
