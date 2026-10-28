"""Verified IAP identities and explicit demo permissions. No proxy-header trust."""
from dataclasses import dataclass

from fastapi import HTTPException, Request


class IAPVerifier:
    def __init__(self, audience):
        import jwt
        self.audience = audience
        self.keys = jwt.PyJWKClient(
            "https://www.gstatic.com/iap/verify/public_key-jwk", timeout=5,
            cache_jwk_set=True, lifespan=300,
        )

    def __call__(self, assertion):
        import jwt
        key = self.keys.get_signing_key_from_jwt(assertion).key
        return jwt.decode(assertion, key, algorithms=["ES256"],
                          audience=self.audience, issuer="https://cloud.google.com/iap",
                          leeway=30, options={"strict_aud": True, "require": ["exp", "iat", "sub", "email", "aud", "iss"]})


@dataclass(frozen=True)
class CloudAccess:
    origin: str
    readers: frozenset[str]
    editors: frozenset[str]
    verifier: object
    task_account: str = ""

    def authenticate(self, request: Request):
        assertion = request.headers.get("x-goog-iap-jwt-assertion", "")
        if not assertion or len(assertion) > 16384:
            raise HTTPException(401, "Verified IAP identity required")
        try:
            claims = self.verifier(assertion)
            email, subject = claims["email"].lower(), claims["sub"]
            if not subject or not isinstance(subject, str):
                raise ValueError("Missing subject")
        except Exception:
            raise HTTPException(401, "Invalid IAP assertion") from None
        internal = request.url.path.startswith("/internal/")
        if internal:
            if not self.task_account or email != self.task_account:
                raise HTTPException(403, "Task identity required")
        else:
            if email not in self.readers | self.editors or email == self.task_account:
                raise HTTPException(403, "Demo membership required")
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                if email not in self.editors:
                    raise HTTPException(403, "Editor permission required")
                # Browsers send Origin on same-origin POST/PUT and binary upload.
                # Missing/null origin is rejected too; CLI writes must set it explicitly.
                if request.headers.get("origin") != self.origin:
                    raise HTTPException(403, "Same-origin write required")
            if request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}:
                raise HTTPException(403, "Cross-origin access denied")
        request.state.can_edit = email in self.editors
        request.state.principal = subject
        return subject


def authenticated_demo(request: Request):
    if not getattr(request.state, "principal", None):
        raise HTTPException(401, "Verified IAP identity required")
