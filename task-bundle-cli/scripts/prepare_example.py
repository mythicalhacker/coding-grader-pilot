"""Recreate the qutebrowser example from the archived public SWE-bench Pro split."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pyarrow.parquet as parquet
from huggingface_hub import hf_hub_download

from task_bundle.bundle import init_from_row, load
from task_bundle.errors import BundleError


DATASET = "ScaleAI/SWE-bench_Pro"
REVISION = "7ab5114912baf22bb098818e604c02fe7ad2c11f"
FILENAME = "data/test-00000-of-00001.parquet"
PARQUET_SHA256 = "c8cd7115496ad4e9a8b21d088cef576a65bf821bb542b24336f13f714cef13f8"
INSTANCE_ID = (
    "instance_qutebrowser__qutebrowser-f91ace96223cac8161c16dd061907e138fe85111"
    "-v059c6fdc75567943479b23ebca7c07b5e9a7f34c"
)
BUNDLE_SHA256 = "f114f14f7937e598b60342a35efb3284d4c1511acf27e6e4c1fc7821372c1e56"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "bundles" / "qutebrowser-instance-1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, help="Use a local copy of the pinned Parquet file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Example bundle directory.")
    args = parser.parse_args()

    if args.output.exists():
        try:
            existing = load(args.output)
        except (BundleError, OSError):
            existing = None
        if existing and existing.bundle_hash == BUNDLE_SHA256:
            print(f"Example already prepared at {args.output}")
            return
        parser.error(f"{args.output} already exists with different contents. Choose a new --output directory.")

    source = args.parquet
    if source is None:
        source = Path(hf_hub_download(
            repo_id=DATASET, repo_type="dataset", revision=REVISION, filename=FILENAME, token=False,
        ))
    try:
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        parser.error(f"Cannot read the dataset: {exc}")
    if digest != PARQUET_SHA256:
        parser.error(f"Unexpected dataset SHA-256 {digest}. Expected {PARQUET_SHA256}.")

    rows = parquet.read_table(source, filters=[("instance_id", "=", INSTANCE_ID)]).to_pylist()
    if len(rows) != 1:
        parser.error(f"Expected one matching qutebrowser row, found {len(rows)}.")
    init_from_row(rows[0], args.output)
    print(f"Prepared {args.output}")


if __name__ == "__main__":
    main()
