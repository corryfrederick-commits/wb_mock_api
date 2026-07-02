from pathlib import Path
import yaml
import json
import csv
import re
from collections import defaultdict, Counter

ROOT = Path("/root")
WEB_ROOT = Path("/var/www/html")
OUT_DIR = Path("/root/wb_yaml_field_dictionary")
PUBLIC_DIR = Path("/var/www/html/metadata")

OUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

MOCK_JSON_FILES = [
    "orders_fbs_new.json",
    "orders_fbs_current.json",
    "orders_fbs_archive.json",
    "orders_fbs_statuses.json",
    "orders_dbs_new.json",
    "orders_dbs_completed.json",
    "orders_dbs_statuses.json",
    "orders_dbw_new.json",
    "orders_dbw_completed.json",
    "orders_dbw_statuses.json",
    "orders_pickup_new.json",
    "orders_pickup_statuses.json",
    "items_cards.json",
    "items_stocks.json",
    "items_warehouses.json",
    "finance_balance.json",
    "finance_sales_reports.json",
    "finance_sales_reports_detailed.json",
    "report_orders.json",
    "report_sales.json",
    "tariffs_commission.json",
    "tariffs_box.json",
    "tariffs_acceptance.json",
    "analytics_sales_funnel.json",
    "analytics_stocks.json",
    "promotion_campaigns.json",
    "promotion_fullstats.json",
    "communications_feedbacks.json",
    "communications_chats.json",
    "fbw_supplies.json",
    "general_seller_info.json",
]

DATASET_YAML_HINTS = {
    "orders_fbs": ["03-orders-fbs.yaml"],
    "orders_dbs": ["05-orders-dbs.yaml"],
    "orders_dbw": ["04-orders-dbw.yaml"],
    "orders_pickup": ["06-in-store-pickup.yaml"],
    "items": ["02-items.yaml"],
    "finance": ["13-finances.yaml"],
    "report": ["12-reports.yaml"],
    "tariffs": ["10-tariffs.yaml"],
    "analytics": ["11-analytics.yaml"],
    "promotion": ["08-promotion.yaml"],
    "communications": ["09-communications.yaml"],
    "fbw": ["07-orders-fbw.yaml"],
    "general": ["01-general.yaml"],
}

def clean_text(value):
    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("\r", " ").strip()

def snake_case(name: str) -> str:
    if not name:
        return ""

    s = str(name).strip()
    s = s.replace("-", "_").replace(".", "_").replace(" ", "_")

    # Чиним WB/OpenAPI-аббревиатуры до camelCase-вида
    replacements = {
        "SKUs": "Skus",
        "SKU": "Sku",
        "NMs": "Nms",
        "NMIDs": "NmIds",
        "NMIds": "NmIds",
        "nmIDs": "nmIds",
        "IDs": "Ids",
        "ID": "Id",
        "WB": "Wb",
        "URL": "Url",
        "UUID": "Uuid",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)

    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s)

    return s.strip("_").lower()

def value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__

def last_json_field(json_path: str) -> str:
    if not json_path:
        return ""
    part = json_path.split(".")[-1]
    return part.replace("[]", "")

def field_name_from_yaml_path(stack):
    for i in range(len(stack) - 1, -1, -1):
        if stack[i] == "properties" and i + 1 < len(stack):
            return stack[i + 1]
    if "parameters" in stack:
        return stack[-1] if stack else ""
    return stack[-1] if stack else ""

def is_probably_openapi_field(stack, obj):
    if not isinstance(obj, dict):
        return False
    if "description" not in obj and "title" not in obj:
        return False

    path = ".".join(stack)
    markers = [
        ".properties.",
        ".parameters.",
        ".responses.",
        ".requestBody.",
        ".schema.",
        ".items.properties.",
    ]
    return any(m in path for m in markers)

def walk_yaml(obj, stack, yaml_file, rows):
    if isinstance(obj, dict):
        if is_probably_openapi_field(stack, obj):
            field_name = field_name_from_yaml_path(stack)
            description = clean_text(obj.get("description"))
            title = clean_text(obj.get("title"))
            field_type = clean_text(obj.get("type"))
            field_format = clean_text(obj.get("format"))
            enum_value = obj.get("enum") or []
            example = obj.get("example", obj.get("examples", ""))

            if field_name or description:
                rows.append({
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
                })

        for k, v in obj.items():
            walk_yaml(v, stack + [str(k)], yaml_file, rows)

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_yaml(v, stack + [f"[{i}]"], yaml_file, rows)

def walk_json(obj, path, rows, dataset_name):
    current_path = ".".join(path)

    if path:
        field_name = last_json_field(current_path)
        rows.append({
            "dataset_name": dataset_name,
            "json_path": current_path,
            "source_field_name": field_name,
            "normalized_field_name": snake_case(field_name),
            "json_value_type": value_type(obj),
        })

    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_json(v, path + [str(k)], rows, dataset_name)

    elif isinstance(obj, list):
        for item in obj:
            if path:
                array_path = path[:-1] + [path[-1] + "[]"]
            else:
                array_path = ["[]"]
            walk_json(item, array_path, rows, dataset_name)

def dataset_yaml_hints(dataset_name):
    for prefix, files in DATASET_YAML_HINTS.items():
        if dataset_name.startswith(prefix):
            return files
    return []

def choose_yaml_match(normalized_name, candidates, preferred_files):
    if not candidates:
        return None

    preferred = [c for c in candidates if c["source_yaml_file"] in preferred_files]
    pool = preferred if preferred else candidates

    with_desc = [c for c in pool if c.get("description")]
    pool = with_desc if with_desc else pool

    return pool[0] if pool else None

# 1. Читаем YAML
yaml_rows = []
yaml_files = sorted(ROOT.glob("*.yaml")) + sorted(ROOT.glob("*.yml"))

for yf in yaml_files:
    try:
        data = yaml.safe_load(yf.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        data = yaml.safe_load(yf.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print(f"SKIP YAML {yf.name}: {e}")
        continue

    walk_yaml(data, [], yf, yaml_rows)

yaml_by_name = defaultdict(list)
for r in yaml_rows:
    if r["normalized_field_name"]:
        yaml_by_name[r["normalized_field_name"]].append(r)

# 2. Читаем фактические mock JSON
actual_rows_raw = []

for filename in MOCK_JSON_FILES:
    path = WEB_ROOT / filename
    if not path.exists():
        print(f"WARN: JSON not found: {path}")
        continue

    dataset_name = path.stem

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"SKIP JSON {filename}: {e}")
        continue

    walk_json(data, [], actual_rows_raw, dataset_name)

# 3. Агрегируем фактические поля: dataset + json_path
actual_group = {}

for r in actual_rows_raw:
    key = (r["dataset_name"], r["json_path"])
    if key not in actual_group:
        actual_group[key] = {
            "dataset_name": r["dataset_name"],
            "json_path": r["json_path"],
            "source_field_name": r["source_field_name"],
            "normalized_field_name": r["normalized_field_name"],
            "json_value_types": Counter(),
            "occurrences": 0,
        }
    actual_group[key]["json_value_types"][r["json_value_type"]] += 1
    actual_group[key]["occurrences"] += 1

actual_fields = []
for item in actual_group.values():
    item["json_value_types"] = dict(item["json_value_types"])
    actual_fields.append(item)

actual_fields.sort(key=lambda x: (x["dataset_name"], x["json_path"]))

# 4. Склеиваем actual fields + YAML descriptions
dataset_dictionary = []

for f in actual_fields:
    dataset_name = f["dataset_name"]
    normalized = f["normalized_field_name"]
    preferred_files = dataset_yaml_hints(dataset_name)
    candidates = yaml_by_name.get(normalized, [])
    match = choose_yaml_match(normalized, candidates, preferred_files)

    all_candidate_descriptions = []
    all_candidate_files = []
    all_source_names = []

    for c in candidates:
        if c.get("description") and c["description"] not in all_candidate_descriptions:
            all_candidate_descriptions.append(c["description"])
        if c["source_yaml_file"] not in all_candidate_files:
            all_candidate_files.append(c["source_yaml_file"])
        if c["field_name"] and c["field_name"] not in all_source_names:
            all_source_names.append(c["field_name"])

    dataset_dictionary.append({
        "dataset_name": dataset_name,
        "json_path": f["json_path"],
        "source_field_name": f["source_field_name"],
        "normalized_field_name": normalized,
        "json_value_types": f["json_value_types"],
        "occurrences": f["occurrences"],
        "preferred_yaml_files": preferred_files,
        "matched_yaml_file": match["source_yaml_file"] if match else "",
        "matched_yaml_path": match["yaml_path"] if match else "",
        "description": match["description"] if match else "",
        "title": match["title"] if match else "",
        "openapi_type": match["type"] if match else "",
        "openapi_format": match["format"] if match else "",
        "enum": match["enum"] if match else [],
        "all_source_field_names": all_source_names,
        "all_candidate_yaml_files": all_candidate_files,
        "all_candidate_descriptions": all_candidate_descriptions,
    })

# 5. Пишем файлы
def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            out = {}
            for k in fieldnames:
                v = r.get(k, "")
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                out[k] = v
            writer.writerow(out)

raw_yaml_json = OUT_DIR / "raw_yaml_fields_v2.json"
raw_yaml_csv = OUT_DIR / "raw_yaml_fields_v2.csv"
actual_json = OUT_DIR / "actual_dataset_fields.json"
actual_csv = OUT_DIR / "actual_dataset_fields.csv"
dataset_dict_json = OUT_DIR / "dataset_field_dictionary.json"
dataset_dict_csv = OUT_DIR / "dataset_field_dictionary.csv"

write_json(raw_yaml_json, yaml_rows)
write_csv(raw_yaml_csv, yaml_rows, [
    "source_yaml_file", "yaml_path", "field_name", "normalized_field_name",
    "title", "description", "type", "format", "enum", "example"
])

write_json(actual_json, actual_fields)
write_csv(actual_csv, actual_fields, [
    "dataset_name", "json_path", "source_field_name",
    "normalized_field_name", "json_value_types", "occurrences"
])

write_json(dataset_dict_json, dataset_dictionary)
write_csv(dataset_dict_csv, dataset_dictionary, [
    "dataset_name",
    "json_path",
    "source_field_name",
    "normalized_field_name",
    "json_value_types",
    "occurrences",
    "preferred_yaml_files",
    "matched_yaml_file",
    "matched_yaml_path",
    "description",
    "title",
    "openapi_type",
    "openapi_format",
    "enum",
    "all_source_field_names",
    "all_candidate_yaml_files",
    "all_candidate_descriptions",
])

for p in [
    raw_yaml_json, raw_yaml_csv,
    actual_json, actual_csv,
    dataset_dict_json, dataset_dict_csv,
]:
    target = PUBLIC_DIR / p.name
    target.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

# 6. Отчёт
matched = sum(1 for r in dataset_dictionary if r["description"])
unmatched = len(dataset_dictionary) - matched

print()
print("OK: dataset field dictionary built")
print(f"YAML files scanned: {len(yaml_files)}")
print(f"YAML field rows: {len(yaml_rows)}")
print(f"Mock JSON files expected: {len(MOCK_JSON_FILES)}")
print(f"Actual dataset fields: {len(actual_fields)}")
print(f"Dataset dictionary rows: {len(dataset_dictionary)}")
print(f"Rows with YAML description: {matched}")
print(f"Rows without YAML description: {unmatched}")
print()
print("Files:")
print(dataset_dict_json)
print(dataset_dict_csv)
print(actual_json)
print(actual_csv)
print()
print("Public URLs:")
print("http://217.60.10.21/metadata/dataset_field_dictionary.json")
print("http://217.60.10.21/metadata/dataset_field_dictionary.csv")
print("http://217.60.10.21/metadata/actual_dataset_fields.json")
print("http://217.60.10.21/metadata/actual_dataset_fields.csv")
print()
print("Snake case sanity check:")
for name in ["nmID", "nmIDs", "nmIds", "chrtID", "chrtIds", "includeSubstitutedSKUs", "isNotIncludeNMsWithoutSales", "warehouseID", "orderUid"]:
    print(f"{name} -> {snake_case(name)}")

print()
print("Orders/core-important preview:")
important = {
    "order_id", "rid", "srid", "order_uid", "nm_id", "chrt_id",
    "article", "supplier_article", "barcode", "skus",
    "warehouse_id", "delivery_type", "delivery_method",
    "price", "sale_price", "final_price", "converted_price",
    "converted_final_price"
}

for r in dataset_dictionary:
    if r["normalized_field_name"] in important and r["description"]:
        print()
        print("DATASET:", r["dataset_name"])
        print("JSON PATH:", r["json_path"])
        print("FIELD:", r["normalized_field_name"])
        print("YAML:", r["matched_yaml_file"])
        print("DESC:", r["description"][:500])
