from __future__ import annotations


def supabase_admin_headers(
    server_key: str,
    *,
    include_json: bool = True,
) -> dict[str, str]:
    """Build Data API headers for new secret and legacy service-role keys."""

    key = server_key.strip()
    if not key:
        raise ValueError("Supabase server key is required")
    if key.startswith("sb_publishable_"):
        raise ValueError(
            "A Supabase publishable key cannot authorize the control plane"
        )

    headers = {"apikey": key}
    # Opaque sb_secret keys are API keys, not JWTs. Legacy service-role JWTs
    # keep the bearer header for backward compatibility.
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    if include_json:
        headers["Content-Type"] = "application/json"
    return headers
