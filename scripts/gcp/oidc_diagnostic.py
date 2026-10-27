"""Temporary DEV-only OIDC inspection. Never logs/stores/exports a token.

Payload decoding is diagnostic, NOT signature verification or authorization.
Google STS remains the authoritative verifier. No Google API is called here.
"""
import base64
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scripts.gcp.ci_config import identities

POLICY = Path(__file__).resolve().parents[2] / "infra/gcp/github-actions/dev-oidc-policy.json"
CLAIMS = ("repository", "repository_id", "repository_owner_id", "event_name", "environment", "sub", "ref", "workflow_ref")
LEGACY_SUB = "repo:piotrbarabasz/tripse-ai-demo:environment:development"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def checks(claims, policy):
    results = {key: isinstance(claims.get(key), str) and claims[key] == policy[key]
               for key in ("repository", "repository_id", "repository_owner_id", "environment", "sub")}
    event, ref = claims.get("event_name"), claims.get("ref")
    results["event_name"] = event in policy["events"] if isinstance(event, str) else False
    results["ref"] = isinstance(ref, str) and (
        (event == "push" and ref in policy["push_refs"]) or
        (event == "workflow_dispatch" and ref.startswith(policy["dispatch_ref_prefix"])))
    results["workflow_ref"] = isinstance(ref, str) and claims.get("workflow_ref") == policy["workflow_ref_prefix"] + ref
    return results


def request_claims():
    # Same audience as the pinned google-github-actions/auth v3 source.
    provider = identities("dev")["WIF_PROVIDER"]
    if os.getenv("WIF_PROVIDER") != provider or os.getenv("CI_TARGET_ENV") != "dev":
        raise ValueError("OIDC diagnostic requires the reviewed DEV provider/target")
    endpoint = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
    bearer = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
    url = urlsplit(endpoint)
    if (not bearer or url.scheme != "https" or not (url.hostname or "").endswith(".actions.githubusercontent.com")
            or url.username or url.password or url.fragment):
        raise ValueError("GitHub runner OIDC endpoint unavailable or invalid; check id-token permission")
    query = [(k, v) for k, v in parse_qsl(url.query) if k != "audience"]
    query.append(("audience", "https://iam.googleapis.com/" + provider))
    endpoint = urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), ""))
    try:
        req = Request(endpoint, headers={"Authorization": "Bearer " + bearer})
        with build_opener(NoRedirect()).open(req, timeout=30) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError("Oversize OIDC response")
        token = json.loads(raw)["value"]
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT envelope")
        claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        if not isinstance(claims, dict):
            raise ValueError("Invalid payload")
        # The token/response/bearer are never returned, logged or exported.
        return {key: claims.get(key) for key in CLAIMS}
    except Exception:
        # In particular, never stringify HTTP errors, request URLs, response bodies,
        # JSON fragments, headers, or base64/JWT decode exceptions.
        raise ValueError("GitHub OIDC request/decode failed; no credential details logged") from None


def report(claims, policy):
    results = checks(claims, policy)
    print("DEV OIDC diagnostic: decoded payload only; Google STS verifies signature/issuer/audience.")
    for key in CLAIMS:
        value = claims.get(key)
        # Only simple bounded strings are eligible for diagnostic output. Reject
        # nested data and mask anything resembling a JWT, even in allowed fields.
        if (not isinstance(value, str) or len(value) > 512
                or re.search(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", value)):
            shown = "<missing or invalid>"
        else:
            shown = json.dumps(value, ensure_ascii=True)
        print(f"{key}={shown} source Terraform check={'PASS' if results[key] else 'FAIL'}")
    print("Audited pre-fix provider legacy sub comparison=" + ("PASS" if claims.get("sub") == LEGACY_SUB else "FAIL"))
    print("Source DEV condition=" + ("PASS" if all(results.values()) else "FAIL"))
    return all(results.values())


def main():
    try:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        if not report(request_claims(), policy):
            raise ValueError("DEV claims do not match the source Terraform condition; authentication remains blocked")
    except Exception:
        print("DEV OIDC diagnostic blocked: inspect selected claim PASS/FAIL results; no token or credential output.", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
