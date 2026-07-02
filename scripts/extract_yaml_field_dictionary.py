from pathlib import Path
import yaml
import json
import csv
import re
from collections import defaultdict

ROOT = Path("/root")
OUT_DIR = Path("/root/wb_yaml_field_dictionary")
PUBLIC_DIR = Path("/var/www/html/metadata")

OUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

def snake_case(name: str) -> str:
    if not name:
        return ""
    name = name.replace("-", "_").replace(".", "_")
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"[^a-zA-Z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_").lower()

def clean_text(value):
    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("\r", " ").strip()

def field_name_from_path(stack):
    """
    Берём имя поля из OpenAPI-пути.
    Обычно оно стоит после properties:
    components.schemas.Order.properties.nmId
    """
    for i in range(len(stack) - 1, -1, -1):
        if stack[i] == "properties" and i + 1 < len(stack):
            return stack[i + 1]

    # Для parameters
    if "parameters" in stack:
        return stack[-1] if stack else ""

    # Для items.properties
    if stack:
        return stack[-1]

    return ""

def is_probably_field(stack, obj):
    if not isinstance(obj, dict):
        return False

    if "description" not in obj and "title" not in obj:
        return False

    path = ".".join(stack)

    good_markers = [
        ".properties.",
        ".parameters.",
        ".schema.",
        ".items.properties.",
        ".responses.",
        ".requestBody.",
    ]

    return any(marker in path for marker in good_markers)

def walk(obj, stack, yaml_file, rows):
    if isinstance(obj, dict):
        if is_probably_field(stack, obj):
            field_name = field_name_from_path(stack)
            description = clean_text(obj.get("description"))
            title = clean_text(obj.get("title"))
            field_type = clean_text(obj.get("type"))
            field_format = clean_text(obj.get("format"))

            enum_value = obj.get("enum")
            if enum_value is None:
                enum_value = []

            example = obj.get("example", obj.get("examples", ""))

            row = {
                "source_yaml_file": yaml_file.name,
                "yaml_path": ".".join(stack),
                "field_name": field_name,
                "normalized_field_name": snake_case(field_name),
                "title": title,
                "description": description,
                "type": field_type,
                "format": field_format,
                "enum": enum_value,
                "example": example,
            }

            if field_name or description:
                rows.append(row)

        for k, v in obj.items():
            walk(v, stack + [str(k)], yaml_file, rows)

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, stack + [f"[{i}]"], yaml_file, rows)

yaml_files = sorted(ROOT.glob("*.yaml")) + sorted(ROOT.glob("*.yml"))

rows = []

for path in yaml_files:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print(f"SKIP {path.name}: {e}")
        continue

    walk(data, [], path, rows)

rows = [r for r in rows if r["field_name"] or r["description"]]

raw_json_path = OUT_DIR / "raw_yaml_fields.json"
raw_csv_path = OUT_DIR / "raw_yaml_fields.csv"

raw_json_path.write_text(
    json.dumps(rows, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

with raw_csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "source_yaml_file",
            "yaml_path",
            "field_name",
            "normalized_field_name",
            "title",
            "description",
            "type",
            "format",
            "enum",
            "example",
        ]
    )
    writer.writeheader()
    for r in rows:
        rr = dict(r)
        rr["enum"] = json.dumps(rr["enum"], ensure_ascii=False)
        rr["example"] = json.dumps(rr["example"], ensure_ascii=False) if rr["example"] else ""
        writer.writerow(rr)

grouped = defaultdict(list)

for r in rows:
    key = r["normalized_field_name"] or snake_case(r["field_name"])
    if not key:
        continue
    grouped[key].append(r)

summary_rows = []

for normalized_name, items in sorted(grouped.items()):
    source_names = sorted(set(i["field_name"] for i in items if i["field_name"]))
    descriptions = []
    for i in items:
        d = i["description"]
        if d and d not in descriptions:
            descriptions.append(d)

    types = sorted(set(i["type"] for i in items if i["type"]))
    formats = sorted(set(i["format"] for i in items if i["format"]))
    yaml_files_for_field = sorted(set(i["source_yaml_file"] for i in items))

    enums = []
    for i in items:
        if i["enum"] and i["enum"] not in enums:
            enums.append(i["enum"])

    summary_rows.append({
        "normalized_field_name": normalized_name,
        "source_field_names": source_names,
        "main_description": descriptions[0] if descriptions else "",
        "all_descriptions": descriptions,
        "types": types,
        "formats": formats,
        "enums": enums,
        "source_yaml_files": yaml_files_for_field,
        "occurrences": len(items),
    })

summary_json_path = OUT_DIR / "field_dictionary_by_name.json"
summary_csv_path = OUT_DIR / "field_dictionary_by_name.csv"

summary_json_path.write_text(
    json.dumps(summary_rows, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

with summary_csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "normalized_field_name",
            "source_field_names",
            "main_description",
            "all_descriptions",
            "types",
            "formats",
            "enums",
            "source_yaml_files",
            "occurrences",
        ]
    )
    writer.writeheader()
    for r in summary_rows:
        writer.writerow({
            "normalized_field_name": r["normalized_field_name"],
            "source_field_names": json.dumps(r["source_field_names"], ensure_ascii=False),
            "main_description": r["main_description"],
            "all_descriptions": json.dumps(r["all_descriptions"], ensure_ascii=False),
            "types": json.dumps(r["types"], ensure_ascii=False),
            "formats": json.dumps(r["formats"], ensure_ascii=False),
            "enums": json.dumps(r["enums"], ensure_ascii=False),
            "source_yaml_files": json.dumps(r["source_yaml_files"], ensure_ascii=False),
            "occurrences": r["occurrences"],
        })

# Копируем в публичную папку nginx, чтобы можно было скачать со второго сервера
for p in [raw_json_path, raw_csv_path, summary_json_path, summary_csv_path]:
    target = PUBLIC_DIR / p.name
    target.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

print()
print("OK: YAML field dictionary extracted")
print(f"YAML files scanned: {len(yaml_files)}")
print(f"Raw field rows: {len(rows)}")
print(f"Grouped fields: {len(summary_rows)}")
print()
print("Local files:")
print(raw_json_path)
print(raw_csv_path)
print(summary_json_path)
print(summary_csv_path)
print()
print("Public URLs:")
print("http://217.60.10.21/metadata/raw_yaml_fields.json")
print("http://217.60.10.21/metadata/raw_yaml_fields.csv")
print("http://217.60.10.21/metadata/field_dictionary_by_name.json")
print("http://217.60.10.21/metadata/field_dictionary_by_name.csv")
print()
print("Key fields preview:")

keywords = [
    "nm_id", "nmid", "nm",
    "chrt_id", "chrtid",
    "rid", "srid",
    "order_uid", "orderuid",
    "warehouse_id", "warehouseid",
    "price",
    "delivery_type", "delivery_method",
    "article",
    "barcode",
    "sku",
]

for r in summary_rows:
    name = r["normalized_field_name"]
    source_joined = " ".join(r["source_field_names"]).lower()
    if any(k in name.lower() or k in source_joined for k in keywords):
        print()
        print("FIELD:", r["normalized_field_name"])
        print("SOURCE NAMES:", ", ".join(r["source_field_names"][:10]))
        print("DESCRIPTION:", r["main_description"][:500])
        print("TYPES:", ", ".join(r["types"]))
        print("FILES:", ", ".join(r["source_yaml_files"][:5]))
