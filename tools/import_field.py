# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click"]
# ///
"""Merge field-sheet entries exported from the worksheet's database into site/field-data.json.

The export is a folder of one JSON file per shot (`<id>.json`), as the artifact database
export writes them. Existing entries for other shots are kept.

Run: uv run tools/import_field.py EXPORT_DIR
"""

import json
from pathlib import Path

import rich_click as click

DATA = Path(__file__).resolve().parent.parent / "site" / "field-data.json"


@click.command()
@click.argument("export_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def main(export_dir: Path) -> None:
    """Merge EXPORT_DIR/*.json shot documents into site/field-data.json."""
    merged = json.loads(DATA.read_text()) if DATA.exists() else {}
    for f in sorted(export_dir.glob("*.json")):
        doc = json.loads(f.read_text())
        body = doc.get("data", doc)
        merged[f.stem] = {k: body.get(k, d) for k, d in (("fields", {}), ("note", ""), ("updatedAt", ""))}
    DATA.write_text(json.dumps(dict(sorted(merged.items())), indent=2, ensure_ascii=False) + "\n")
    click.echo(f"{len(merged)} shots in {DATA.name}")


if __name__ == "__main__":
    main()
