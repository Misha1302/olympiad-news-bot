#!/usr/bin/env python3
"""Build a GigaChat-only CA bundle inside the repository runtime directory."""

from __future__ import annotations

import hashlib
import ssl
from pathlib import Path
from urllib.request import urlopen

import certifi

CERTIFICATES = (
    (
        "russian_trusted_root_ca_pem.crt",
        "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt",
    ),
    (
        "russian_trusted_sub_ca_pem.crt",
        "https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt",
    ),
)


def download(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def validate_pem_certificate(content: bytes) -> str:
    text = content.decode("ascii")
    der = ssl.PEM_cert_to_DER_cert(text)
    return hashlib.sha256(der).hexdigest()


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    certificates_directory = repository_root / ".runtime" / "certs"
    certificates_directory.mkdir(parents=True, exist_ok=True)

    bundle_path = certificates_directory / "gigachat-ca-bundle.pem"
    bundle_parts = [Path(certifi.where()).read_bytes().rstrip() + b"\n"]

    for filename, url in CERTIFICATES:
        content = download(url)
        fingerprint = validate_pem_certificate(content)
        certificate_path = certificates_directory / filename
        certificate_path.write_bytes(content)
        bundle_parts.append(content.rstrip() + b"\n")
        print(f"Saved {certificate_path} (SHA-256 {fingerprint})")

    bundle_path.write_bytes(b"\n".join(bundle_parts))
    print(f"Saved {bundle_path}")
    print()
    print("Add this setting to SECRETS.py:")
    print(f'GIGACHAT_CA_BUNDLE = r"{bundle_path}"')
    print()
    print("The bundle is used only by the GigaChat adapter and does not alter global trust.")


if __name__ == "__main__":
    main()
