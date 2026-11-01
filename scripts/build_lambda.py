"""Empaqueta la Lambda: handler.py + duckdb para Linux x86_64 -> dist/ingest_lambda.zip."""

import argparse
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "lambda"
ZIP = ROOT / "dist" / "ingest_lambda"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duckdb-version", help="por defecto, la instalada en local")
    args = ap.parse_args()

    shutil.rmtree(BUILD, ignore_errors=True)
    BUILD.mkdir(parents=True)
    # La misma versión de duckdb que en local, compilada para el runtime de Lambda.
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--quiet",
            f"duckdb=={args.duckdb_version or version('duckdb')}",
            "--platform", "manylinux_2_28_x86_64", "--python-version", "3.12",
            "--implementation", "cp", "--only-binary=:all:", "--target", str(BUILD),
        ],
        check=True,
    )  # fmt: skip
    shutil.copy(ROOT / "src" / "ingest" / "handler.py", BUILD / "handler.py")
    ZIP.parent.mkdir(exist_ok=True)
    out = shutil.make_archive(str(ZIP), "zip", BUILD)
    print(f"{out}  ({Path(out).stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
