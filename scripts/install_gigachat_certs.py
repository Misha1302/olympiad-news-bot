#!/usr/bin/env python3
"""Install a local CA bundle for GigaChat HTTPS requests.

The script mirrors the working Fedora approach from the ResumeAkbars project,
but keeps certificates inside the Python bot repository instead of modifying
system trust storage.

Important: the generated bundle starts with the default certifi CA bundle and
then appends Russian trusted root and subordinate CA certificates. This keeps
Telegram API HTTPS working while also allowing GigaChat HTTPS verification.
"""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

import certifi

CERTIFICATES = [
    (
        "russian_trusted_root_ca_pem.crt",
        "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt",
    ),
    (
        "russian_trusted_sub_ca_pem.crt",
        "https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt",
    ),
]


def download(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    certificates_directory = repository_root / ".runtime" / "certs"
    certificates_directory.mkdir(parents=True, exist_ok=True)

    bundle_path = certificates_directory / "gigachat-ca-bundle.pem"
    default_bundle = Path(certifi.where()).read_bytes().rstrip() + b"\n"
    bundle_parts = [default_bundle]

    for filename, url in CERTIFICATES:
        content = download(url)
        certificate_path = certificates_directory / filename
        certificate_path.write_bytes(content)
        bundle_parts.append(content.rstrip() + b"\n")
        print(f"Saved {certificate_path}")

    bundle_path.write_bytes(b"\n".join(bundle_parts))
    print(f"Saved {bundle_path}")
    print()
    print("Use this command before starting the bot:")
    print(f'export REQUESTS_CA_BUNDLE="{bundle_path}"')
    print()
    print("The generated bundle includes default certifi certificates, so Telegram API HTTPS remains trusted.")


if __name__ == "__main__":
    main()
