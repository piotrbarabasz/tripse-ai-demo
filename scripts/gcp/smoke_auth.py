"""Short-lived, keyless probe credentials using the runner's WIF credentials."""
import json
import os
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def probe_token(g, origin, *, iap):
    account = os.getenv("GCP_SMOKE_ACCOUNT", "")
    expected = f'tripse-ai-{g.config["APP_ENV"]}-ci-probe@{g.config["GCP_PROJECT_ID"]}.iam.gserviceaccount.com'
    if account != expected:
        raise ValueError("CI probe must use the dedicated environment account")
    if not re.fullmatch(r"https://[a-z0-9.-]+\.run\.app", origin):
        raise ValueError("Invalid probe origin")
    access = g("auth", "print-access-token")
    if not access:
        raise ValueError("Runner cannot obtain an access token")
    method = "signJwt" if iap else "generateIdToken"
    if iap:
        timestamp = int(time.time())
        # IAP service-account JWTs scope an exact URL, not an OIDC service origin.
        # The smoke/API/browser suite visits multiple paths on this one origin.
        payload = {"payload": json.dumps({"iss": account, "sub": account, "aud": origin + "/*",
                                          "iat": timestamp, "exp": timestamp + 600})}
        field = "signedJwt"
    else:
        payload, field = {"audience": origin, "includeEmail": True}, "token"
    request = Request(f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{account}:{method}",
        data=json.dumps(payload).encode(), headers={"Authorization": "Bearer " + access,
                                                  "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            token = json.load(response)[field]
    except (HTTPError, OSError, KeyError, ValueError):
        raise ValueError("Keyless CI probe credential unavailable; check probe IAM/IAP setup") from None
    if not isinstance(token, str) or not token:
        raise ValueError("Empty CI probe credential")
    # Keep the token in memory only; do not print it, write it to an artifact,
    # or pass it as a command-line argument.
    return token


def safe_auth_metadata(headers):
    """Static classifications only: never return raw challenges/redirects/headers."""
    headers = headers or {}
    challenge = headers.get("WWW-Authenticate", "")
    scheme = challenge.split(" ", 1)[0].lower()
    scheme = scheme if scheme in {"bearer", "basic", "negotiate"} else "absent_or_other"
    match = re.search(r'\berror\s*=\s*"([a-z_]+)"', challenge, flags=re.IGNORECASE)
    error = match.group(1).lower() if match else "absent_or_other"
    if error not in {"invalid_token", "invalid_request", "insufficient_scope"}:
        error = "absent_or_other"
    generated = headers.get("X-Goog-IAP-Generated-Response", "").lower() in {"true", "1"}
    return (f"iap_generated={str(generated).lower()}, www_auth_scheme={scheme}, "
            f"www_auth_error={error}, redirect={str(bool(headers.get('Location'))).lower()}")
