import json
import os
import urllib.request

_JEV_URL = "https://jevtypesafeai.com/api/v1/decide"
_TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
_TYPESAFE_MODEL = "jev-latest"


def decide(body: dict) -> dict | None:
    jev_key = os.environ.get("JEV_API_KEY", "").strip()
    typesafe_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not jev_key and not typesafe_key:
        return None
    if not isinstance(body, dict):
        raise TypeError("body must be a dict")
    if jev_key:
        return _post(_JEV_URL, jev_key, body)
    payload = body if "model" in body else {"model": _TYPESAFE_MODEL, **body}
    return _post(_TYPESAFE_URL, typesafe_key, payload)


def _post(url: str, key: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError("Jev response was not a JSON object")
    return parsed
