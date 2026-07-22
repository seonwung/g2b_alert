"""Windows credential storage for API and SMTP secrets."""

SMTP_CREDENTIAL_SERVICE = "G2BAlert.SMTP"
API_CREDENTIAL_SERVICE = "G2BAlert.API"
API_CREDENTIAL_USERNAME = "g2b-service-key"

try:
    import keyring
except ImportError:
    keyring = None


class CredentialStoreError(RuntimeError):
    pass


def _require_keyring():
    if keyring is None:
        raise CredentialStoreError("Windows 자격 증명 저장 기능을 사용하려면 keyring 패키지가 필요합니다.")


def save_smtp_password(username, password):
    _require_keyring()
    username = (username or "").strip()
    password = "".join((password or "").split())
    if not username or not password:
        raise CredentialStoreError("SMTP 계정과 앱 비밀번호를 모두 입력해 주세요.")
    try:
        keyring.set_password(SMTP_CREDENTIAL_SERVICE, username, password)
    except Exception as error:
        raise CredentialStoreError(f"Windows 자격 증명 관리자에 저장하지 못했습니다: {error}") from error


def get_smtp_password(username):
    _require_keyring()
    username = (username or "").strip()
    if not username:
        return None
    try:
        return keyring.get_password(SMTP_CREDENTIAL_SERVICE, username)
    except Exception as error:
        raise CredentialStoreError(f"Windows 자격 증명 관리자에서 비밀번호를 읽지 못했습니다: {error}") from error


def save_api_key(api_key):
    _require_keyring()
    api_key = "".join((api_key or "").split())
    if not api_key:
        raise CredentialStoreError("나라장터 API 키를 입력해 주세요.")
    try:
        keyring.set_password(API_CREDENTIAL_SERVICE, API_CREDENTIAL_USERNAME, api_key)
    except Exception as error:
        raise CredentialStoreError(f"Windows 자격 증명 관리자에 API 키를 저장하지 못했습니다: {error}") from error


def get_api_key():
    _require_keyring()
    try:
        return keyring.get_password(API_CREDENTIAL_SERVICE, API_CREDENTIAL_USERNAME)
    except Exception as error:
        raise CredentialStoreError(f"Windows 자격 증명 관리자에서 API 키를 읽지 못했습니다: {error}") from error

