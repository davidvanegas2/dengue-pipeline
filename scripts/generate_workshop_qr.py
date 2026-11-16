# /// script
# requires-python = ">=3.11"
# dependencies = ["segno==1.6.6"]
# ///
"""Generate workshop QR assets locally without sending URLs to a QR service."""

from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parents[1]
LINKS = {
    "repository": "https://github.com/davidvanegas2/dengue-pipeline",
    "molab": (
        "https://molab.marimo.io/github/davidvanegas2/dengue-pipeline"
        "/blob/main/notebooks/workshop.py"
    ),
}


def main() -> None:
    """Write print-friendly SVG and PNG files for each workshop entry point."""
    output = ROOT / "docs" / "assets"
    output.mkdir(parents=True, exist_ok=True)
    for name, url in LINKS.items():
        qr = segno.make_qr(url, error="m")
        for extension in ("svg", "png"):
            path = output / f"qr_{name}.{extension}"
            qr.save(path, scale=10, border=4, light="white", dark="black")
            # ASCII only: Windows consoles and redirected output may not encode arrows.
            print(f"QR creado: {path.relative_to(ROOT)} -> {url}")


if __name__ == "__main__":
    main()
