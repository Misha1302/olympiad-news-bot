#!/usr/bin/env python3
"""Install a local CA bundle for GigaChat HTTPS requests.

The script mirrors the working Fedora approach from the ResumeAkbars project,
but keeps certificates inside the Python bot repository instead of modifying
system trust storage.

It downloads Russian trusted root and subordinate CA certificates, creates a
single PEM bundle in .runtime/certs, and prints the environment variable that
must be used when running the bot.
"""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

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
    downloaded_certificates: list[bytes] = []

    for filename, url in CERTIFICATES:
        content = download(url)
        certificate_path = certificates_directory / filename
        certificate_path.write_bytes(content)
        downloaded_certificates.append(content.rstrip() + b"\n")
        print(f"Saved {certificate_path}")

    bundle_path.write_bytes(b"\n".join(downloaded_certificates))
    print(f"Saved {bundle_path}")
    print()
    print("Use this command before starting the bot:")
    print(f'export REQUESTS_CA_BUNDLE="{bundle_path}"')


if __name__ == "__main__":
    main()
