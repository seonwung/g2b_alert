SMTP_CREDENTIAL_SERVICE = "G2BAlert.SMTP"

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


def delete_smtp_password(username):
    _require_keyring()
    username = (username or "").strip()
    if not username:
        return
    try:
        keyring.delete_password(SMTP_CREDENTIAL_SERVICE, username)
    except Exception as error:
        if error.__class__.__name__ != "PasswordDeleteError":
            raise CredentialStoreError(f"SMTP 앱 비밀번호를 삭제하지 못했습니다: {error}") from error
