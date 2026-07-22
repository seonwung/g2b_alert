import requests


class ApiRequestError(RuntimeError):
    """API failure whose message never contains the request URL or service key."""

    def __init__(self, service_name, kind, status_code=None):
        self.service_name = service_name
        self.kind = kind
        self.status_code = status_code
        super().__init__(self.user_message)

    @property
    def signature(self):
        return f"{self.kind}:{self.status_code or ''}"

    @property
    def user_message(self):
        if self.kind == "timeout":
            return f"{self.service_name} 응답 시간이 초과되었습니다."
        if self.kind == "connection":
            return f"{self.service_name} 네트워크 연결에 실패했습니다."
        if self.kind == "invalid_json":
            return f"{self.service_name} 응답을 JSON으로 해석하지 못했습니다."
        if self.status_code:
            return f"{self.service_name} HTTP {self.status_code} 오류입니다."
        return f"{self.service_name} 요청에 실패했습니다."


def request_json(url, params, timeout, service_name):
    """Return JSON while replacing requests errors with URL-safe exceptions."""
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise ApiRequestError(service_name, "timeout") from None
    except requests.exceptions.ConnectionError:
        raise ApiRequestError(service_name, "connection") from None
    except requests.exceptions.HTTPError as error:
        response = error.response
        status_code = response.status_code if response is not None else None
        raise ApiRequestError(service_name, "http", status_code=status_code) from None
    except requests.exceptions.JSONDecodeError:
        raise ApiRequestError(service_name, "invalid_json") from None
    except requests.exceptions.RequestException:
        raise ApiRequestError(service_name, "request") from None
    except ValueError:
        raise ApiRequestError(service_name, "invalid_json") from None
