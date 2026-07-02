import json
import os
import random
import shutil
from datetime import datetime, timezone, timedelta
from copy import deepcopy
from pathlib import Path

import yaml
from faker import Faker

fake = Faker("ru_RU")

NGINX_DIR = Path(os.getenv("NGINX_DIR", "/var/www/html"))
BASE_DIR = Path(os.getenv("YAML_DIR", "."))

CLEAN_OLD_TEST_DATA = True

COUNT_MIN = 5
COUNT_MAX = 20

# Один элемент = один JSON-файл = один имитируемый ответ реального API endpoint-а
DATASETS = [
    # ORDERS FBS
    {"dataset_name": "orders_fbs_new", "yaml_file": "03-orders-fbs.yaml", "method": "get", "path": "/api/v3/orders/new", "output_file": "orders_fbs_new.json", "id_start": 1000000, "flow": "fbs", "kind": "orders"},
    {"dataset_name": "orders_fbs_current", "yaml_file": "03-orders-fbs.yaml", "method": "get", "path": "/api/v3/orders", "output_file": "orders_fbs_current.json", "id_start": 1100000, "flow": "fbs", "kind": "orders"},
    {"dataset_name": "orders_fbs_archive", "yaml_file": "03-orders-fbs.yaml", "method": "get", "path": "/api/marketplace/v3/fbs/orders/archive", "output_file": "orders_fbs_archive.json", "id_start": 1900000, "flow": "fbs", "kind": "archive"},
    {"dataset_name": "orders_fbs_statuses", "yaml_file": "03-orders-fbs.yaml", "method": "post", "path": "/api/v3/orders/status", "output_file": "orders_fbs_statuses.json", "id_start": 1000000, "flow": "fbs", "kind": "statuses"},

    # ORDERS DBS
    {"dataset_name": "orders_dbs_new", "yaml_file": "05-orders-dbs.yaml", "method": "get", "path": "/api/v3/dbs/orders/new", "output_file": "orders_dbs_new.json", "id_start": 2000000, "flow": "dbs", "kind": "orders"},
    {"dataset_name": "orders_dbs_completed", "yaml_file": "05-orders-dbs.yaml", "method": "get", "path": "/api/v3/dbs/orders", "output_file": "orders_dbs_completed.json", "id_start": 2100000, "flow": "dbs", "kind": "orders"},
    {"dataset_name": "orders_dbs_statuses", "yaml_file": "05-orders-dbs.yaml", "method": "post", "path": "/api/marketplace/v3/dbs/orders/status/info", "output_file": "orders_dbs_statuses.json", "id_start": 2000000, "flow": "dbs", "kind": "statuses"},

    # ORDERS DBW
    {"dataset_name": "orders_dbw_new", "yaml_file": "04-orders-dbw.yaml", "method": "get", "path": "/api/v3/dbw/orders/new", "output_file": "orders_dbw_new.json", "id_start": 3000000, "flow": "dbw", "kind": "orders"},
    {"dataset_name": "orders_dbw_completed", "yaml_file": "04-orders-dbw.yaml", "method": "get", "path": "/api/v3/dbw/orders", "output_file": "orders_dbw_completed.json", "id_start": 3100000, "flow": "dbw", "kind": "orders"},
    {"dataset_name": "orders_dbw_statuses", "yaml_file": "04-orders-dbw.yaml", "method": "post", "path": "/api/v3/dbw/orders/status", "output_file": "orders_dbw_statuses.json", "id_start": 3000000, "flow": "dbw", "kind": "statuses"},

    # PICKUP
    {"dataset_name": "orders_pickup_new", "yaml_file": "06-in-store-pickup.yaml", "method": "get", "path": "/api/v3/click-collect/orders/new", "output_file": "orders_pickup_new.json", "id_start": 4000000, "flow": "pickup", "kind": "orders"},
    {"dataset_name": "orders_pickup_statuses", "yaml_file": "06-in-store-pickup.yaml", "method": "post", "path": "/api/marketplace/v3/click-collect/orders/status/info", "output_file": "orders_pickup_statuses.json", "id_start": 4000000, "flow": "pickup", "kind": "statuses"},

    # ITEMS / STOCKS
    {"dataset_name": "items_cards", "yaml_file": "02-items.yaml", "method": "post", "path": "/content/v2/get/cards/list", "output_file": "items_cards.json", "id_start": 5000000, "flow": "items", "kind": "items"},
    {"dataset_name": "items_stocks", "yaml_file": "02-items.yaml", "method": "post", "path": "/api/v3/stocks/{warehouseId}", "output_file": "items_stocks.json", "id_start": 5100000, "flow": "items", "kind": "stocks"},
    {"dataset_name": "items_warehouses", "yaml_file": "02-items.yaml", "method": "get", "path": "/api/v3/warehouses", "output_file": "items_warehouses.json", "id_start": 5200000, "flow": "items", "kind": "warehouses"},

    # FINANCES / REPORTS
    {"dataset_name": "finance_balance", "yaml_file": "13-finances.yaml", "method": "get", "path": "/api/v1/account/balance", "output_file": "finance_balance.json", "id_start": 6000000, "flow": "finance", "kind": "balance"},
    {"dataset_name": "finance_sales_reports", "yaml_file": "13-finances.yaml", "method": "post", "path": "/api/finance/v1/sales-reports/list", "output_file": "finance_sales_reports.json", "id_start": 6100000, "flow": "finance", "kind": "reports"},
    {"dataset_name": "finance_sales_reports_detailed", "yaml_file": "13-finances.yaml", "method": "post", "path": "/api/finance/v1/sales-reports/detailed", "output_file": "finance_sales_reports_detailed.json", "id_start": 6200000, "flow": "finance", "kind": "reports"},

    {"dataset_name": "report_orders", "yaml_file": "12-reports.yaml", "method": "get", "path": "/api/v1/supplier/orders", "output_file": "report_orders.json", "id_start": 6300000, "flow": "reports", "kind": "orders_report"},
    {"dataset_name": "report_sales", "yaml_file": "12-reports.yaml", "method": "get", "path": "/api/v1/supplier/sales", "output_file": "report_sales.json", "id_start": 6400000, "flow": "reports", "kind": "sales_report"},

    # TARIFFS
    {"dataset_name": "tariffs_commission", "yaml_file": "10-tariffs.yaml", "method": "get", "path": "/api/v1/tariffs/commission", "output_file": "tariffs_commission.json", "id_start": 7000000, "flow": "tariffs", "kind": "tariffs"},
    {"dataset_name": "tariffs_box", "yaml_file": "10-tariffs.yaml", "method": "get", "path": "/api/v1/tariffs/box", "output_file": "tariffs_box.json", "id_start": 7100000, "flow": "tariffs", "kind": "tariffs"},
    {"dataset_name": "tariffs_acceptance", "yaml_file": "10-tariffs.yaml", "method": "get", "path": "/api/tariffs/v1/acceptance/coefficients", "output_file": "tariffs_acceptance.json", "id_start": 7200000, "flow": "tariffs", "kind": "tariffs"},

    # ANALYTICS / ADS / COMMUNICATIONS
    {"dataset_name": "analytics_sales_funnel", "yaml_file": "11-analytics.yaml", "method": "post", "path": "/api/analytics/v3/sales-funnel/products", "output_file": "analytics_sales_funnel.json", "id_start": 8000000, "flow": "analytics", "kind": "analytics"},
    {"dataset_name": "analytics_stocks", "yaml_file": "11-analytics.yaml", "method": "post", "path": "/api/analytics/v1/stocks-report/wb-warehouses", "output_file": "analytics_stocks.json", "id_start": 8100000, "flow": "analytics", "kind": "analytics"},

    {"dataset_name": "promotion_campaigns", "yaml_file": "08-promotion.yaml", "method": "get", "path": "/api/advert/v2/adverts", "output_file": "promotion_campaigns.json", "id_start": 9000000, "flow": "promotion", "kind": "promotion"},
    {"dataset_name": "promotion_fullstats", "yaml_file": "08-promotion.yaml", "method": "get", "path": "/adv/v3/fullstats", "output_file": "promotion_fullstats.json", "id_start": 9100000, "flow": "promotion", "kind": "promotion"},

    {"dataset_name": "communications_feedbacks", "yaml_file": "09-communications.yaml", "method": "get", "path": "/api/v1/feedbacks", "output_file": "communications_feedbacks.json", "id_start": 9200000, "flow": "communications", "kind": "feedbacks"},
    {"dataset_name": "communications_chats", "yaml_file": "09-communications.yaml", "method": "get", "path": "/api/v1/seller/chats", "output_file": "communications_chats.json", "id_start": 9300000, "flow": "communications", "kind": "chats"},

    # FBW / GENERAL
    {"dataset_name": "fbw_supplies", "yaml_file": "07-orders-fbw.yaml", "method": "post", "path": "/api/v1/supplies", "output_file": "fbw_supplies.json", "id_start": 9400000, "flow": "fbw", "kind": "supplies"},
    {"dataset_name": "general_seller_info", "yaml_file": "01-general.yaml", "method": "get", "path": "/api/v1/seller-info", "output_file": "general_seller_info.json", "id_start": 9500000, "flow": "general", "kind": "general"},
]

ROOT_LARGE_ARRAY_NAMES = {
    "orders", "cards", "stocks", "data", "items", "goods", "adverts",
    "bids", "supplies", "feedbacks", "questions", "chats", "events",
    "warehouses", "contacts", "report", "nms"
}

ORDER_ID_POOLS = {}


def realistic_datetime_iso(days_back: int = 60) -> str:
    dt = datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return dt.isoformat()



def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def schema_from_response(resp):
    if not isinstance(resp, dict):
        return None

    content = resp.get("content", {})
    if not isinstance(content, dict):
        return None

    for content_type in ("application/json", "application/problem+json", "*/*"):
        schema = content.get(content_type, {}).get("schema")
        if schema:
            return schema

    for content_obj in content.values():
        if isinstance(content_obj, dict) and content_obj.get("schema"):
            return content_obj["schema"]

    return None


def get_response_schema(spec: dict, api_path: str, method: str):
    path_obj = spec.get("paths", {}).get(api_path)
    if not path_obj:
        raise KeyError(f"В YAML нет path: {api_path}")

    op = path_obj.get(method.lower())
    if not op:
        raise KeyError(f"В YAML нет method {method.upper()} для path: {api_path}")

    responses = op.get("responses", {})

    for code in ("200", "201"):
        schema = schema_from_response(responses.get(code))
        if schema:
            return schema

    for code, resp in responses.items():
        if str(code).startswith("2"):
            schema = schema_from_response(resp)
            if schema:
                return schema

    raise ValueError(f"Не нашёл JSON response schema для {method.upper()} {api_path}")


def deep_merge(a: dict, b: dict) -> dict:
    result = deepcopy(a)
    for k, v in b.items():
        if k == "properties":
            result.setdefault("properties", {})
            result["properties"].update(v or {})
        elif k == "required":
            result[k] = sorted(set(result.get(k, [])) | set(v or []))
        elif isinstance(result.get(k), dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


def resolve_ref(schema: dict, spec: dict, seen=None):
    if seen is None:
        seen = set()

    if not isinstance(schema, dict):
        return schema

    if "$ref" not in schema:
        return schema

    ref = schema["$ref"]
    if ref in seen:
        return {}

    seen.add(ref)

    if not ref.startswith("#/"):
        return {}

    parts = ref.lstrip("#/").split("/")
    node = spec

    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        node = node.get(part)
        if node is None:
            return {}

    return normalize_schema(deepcopy(node), spec, seen)


def normalize_schema(schema: dict, spec: dict, seen=None):
    if seen is None:
        seen = set()

    if not isinstance(schema, dict):
        return schema

    schema = resolve_ref(schema, spec, seen)

    if "allOf" in schema:
        merged = {}
        for item in schema.get("allOf", []):
            merged = deep_merge(merged, normalize_schema(item, spec, seen))
        rest = {k: v for k, v in schema.items() if k != "allOf"}
        return deep_merge(merged, rest)

    for key in ("oneOf", "anyOf"):
        if key in schema and schema[key]:
            return normalize_schema(schema[key][0], spec, seen)

    return schema


def is_order_id_field(field_name: str, path_stack: list) -> bool:
    fn = (field_name or "").lower()

    if fn in {"orderid", "order_id"}:
        return True

    if fn == "id" and "orders" in [p.lower() for p in path_stack]:
        return True

    return False


def next_order_id(ctx: dict) -> int:
    ctx["next_id"] += 1
    value = ctx["next_id"]
    ORDER_ID_POOLS.setdefault(ctx["flow"], []).append(value)
    return value


def pick_existing_order_id(ctx: dict) -> int:
    pool = ORDER_ID_POOLS.get(ctx["flow"]) or []

    if pool:
        return random.choice(pool)

    return next_order_id(ctx)


def generate_string(field_name: str, schema: dict, ctx: dict, path_stack: list, object_cache: dict):
    fn = (field_name or "").lower()
    fmt = schema.get("format")

    if fmt == "date-time":
        return realistic_datetime_iso()

    if fmt == "date":
        return fake.date()

    if "enum" in schema and schema["enum"]:
        return random.choice(schema["enum"])

    if fn.endswith("date") or fn in {"createdat", "updatedat"}:
        return realistic_datetime_iso()

    if fn == "orderuid":
        if object_cache.get("order_id"):
            oid = object_cache["order_id"]
        elif ctx.get("kind") == "statuses":
            oid = pick_existing_order_id(ctx)
        else:
            oid = next_order_id(ctx)

        object_cache["order_id"] = oid
        return f"{oid}_{fake.uuid4().replace('-', '')[:24]}"

    if fn == "rid":
        if object_cache.get("order_id"):
            oid = object_cache["order_id"]
        elif ctx.get("kind") == "statuses":
            oid = pick_existing_order_id(ctx)
        else:
            oid = next_order_id(ctx)

        object_cache["order_id"] = oid
        return f"rid_{oid}"

    if fn in {"article", "vendorcode"}:
        return f"art-{random.randint(1000, 9999)}"

    if fn in {"barcode", "sku", "skus"} or "barcode" in fn or "sku" in fn:
        return str(random.randint(4600000000000, 4699999999999))

    if "address" in fn:
        return fake.address().replace("\n", ", ")

    if "name" in fn or "title" in fn:
        return fake.word()

    if "status" in fn:
        return random.choice(["new", "confirm", "complete", "cancel", "delivered", "sold", "waiting"])

    if "currency" in fn:
        return "RUB"

    return fake.word()


def generate_number(field_name: str, schema: dict, ctx: dict, path_stack: list, object_cache: dict):
    fn = (field_name or "").lower()
    typ = schema.get("type")

    if is_order_id_field(field_name, path_stack):
        if ctx["kind"] == "statuses":
            oid = object_cache.get("order_id") or pick_existing_order_id(ctx)
        else:
            oid = object_cache.get("order_id") or next_order_id(ctx)

        object_cache["order_id"] = oid
        return oid

    if fn in {"nmid", "nm_id"} or "nmid" in fn:
        return random.randint(10000000, 99999999)

    if fn in {"chrtid", "chrt_id"} or "chrtid" in fn:
        return random.randint(100000000, 999999999)

    if "warehouse" in fn and "id" in fn:
        return random.randint(1, 500)

    if "office" in fn and "id" in fn:
        return random.randint(1, 500)

    if "price" in fn or "sum" in fn or "amount" in fn or "total" in fn:
        base_price = object_cache.get("base_price")

        if base_price is None:
            base_price = random.randint(500, 10000)
            object_cache["base_price"] = base_price

        if "final" in fn:
            return max(1, int(base_price * random.uniform(0.5, 0.95)))

        if "sale" in fn:
            return max(1, int(base_price * random.uniform(0.7, 1.0)))

        return base_price

    if "currency" in fn and "code" in fn:
        return 643

    if "longitude" in fn:
        return round(random.uniform(30, 160), 6)

    if "latitude" in fn:
        return round(random.uniform(40, 70), 6)

    if typ == "number":
        return round(random.uniform(1, 1000), 2)

    return random.randint(1, 1000)


def array_count(field_name: str, path_stack: list) -> int:
    fn = (field_name or "").lower()

    # Главные массивы ответа: orders, cards, stocks и т.д.
    if len(path_stack) <= 1:
        return random.randint(COUNT_MIN, COUNT_MAX)

    if fn in ROOT_LARGE_ARRAY_NAMES and len(path_stack) <= 2:
        return random.randint(COUNT_MIN, COUNT_MAX)

    # Вложенные массивы: skus, sizes, photos, errors и т.д.
    return random.randint(1, 3)


def generate_mock_value(schema: dict, spec: dict, ctx: dict, field_name=None, path_stack=None, object_cache=None):
    if path_stack is None:
        path_stack = []

    if object_cache is None:
        object_cache = {}

    schema = normalize_schema(schema or {}, spec)

    if not isinstance(schema, dict):
        return None

    prop_type = schema.get("type")

    if not prop_type:
        if "properties" in schema:
            prop_type = "object"
        elif "items" in schema:
            prop_type = "array"

    if "enum" in schema and schema["enum"] and prop_type in {"string", "integer", "number", None}:
        return random.choice(schema["enum"])

    if prop_type == "object":
        props = schema.get("properties", {})
        local_cache = {}

        return {
            k: generate_mock_value(v, spec, ctx, k, path_stack + [k], local_cache)
            for k, v in props.items()
        }

    if prop_type == "array":
        cnt = array_count(field_name, path_stack)
        item_schema = schema.get("items", {})

        return [
            generate_mock_value(item_schema, spec, ctx, field_name, path_stack + ["[]"], {})
            for _ in range(cnt)
        ]

    if prop_type == "string":
        return generate_string(field_name, schema, ctx, path_stack, object_cache)

    if prop_type in {"integer", "number"}:
        return generate_number(field_name, schema, ctx, path_stack, object_cache)

    if prop_type == "boolean":
        return fake.boolean()

    if "example" in schema:
        return schema["example"]

    return None


def clean_old_files():
    if not CLEAN_OLD_TEST_DATA:
        return

    for directory in {BASE_DIR, NGINX_DIR}:
        if not directory.exists():
            continue

        for old_file in directory.glob("*_test_data.json"):
            try:
                old_file.unlink()
                print(f"[clean] Удалён старый файл: {old_file}")
            except Exception as e:
                print(f"[clean] Не смог удалить {old_file}: {e}")


def main():
    print("[+] Генерация реалистичных mock-ответов API")
    print(f"[+] YAML_DIR: {BASE_DIR.resolve()}")
    print(f"[+] NGINX_DIR: {NGINX_DIR.resolve()}")

    NGINX_DIR.mkdir(parents=True, exist_ok=True)
    clean_old_files()

    created_json_files = []

    for ds in DATASETS:
        yaml_path = BASE_DIR / ds["yaml_file"]
        output_path = BASE_DIR / ds["output_file"]
        nginx_output_path = NGINX_DIR / ds["output_file"]

        print(f"\n[+] Dataset: {ds['dataset_name']}")
        print(f"    YAML: {ds['yaml_file']}")
        print(f"    Endpoint: {ds['method'].upper()} {ds['path']}")

        try:
            if not yaml_path.exists():
                raise FileNotFoundError(f"Не найден YAML: {yaml_path}")

            spec = load_yaml(yaml_path)
            response_schema = get_response_schema(spec, ds["path"], ds["method"])

            ctx = {
                "dataset_name": ds["dataset_name"],
                "flow": ds.get("flow", ds["dataset_name"]),
                "kind": ds.get("kind", "generic"),
                "next_id": int(ds.get("id_start", 1_000_000)),
            }

            mock_data = generate_mock_value(
                response_schema,
                spec,
                ctx,
                field_name=ds["dataset_name"],
                path_stack=[],
                object_cache={}
            )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(mock_data, f, indent=4, ensure_ascii=False)

            shutil.copy2(output_path, nginx_output_path)
            nginx_output_path.chmod(0o644)

            created_json_files.append(nginx_output_path)

            print(f"    OK: {output_path.name} -> {nginx_output_path}")

        except Exception as e:
            print(f"    ERROR: {e}")

    print("\n[+] Генерация завершена.")

    if created_json_files:
        print("\n[+] Файлы доступны через Nginx:")
        for file_path in created_json_files:
            print(f"    /{file_path.name}")
    else:
        print("\n[-] JSON-файлы не были созданы.")


if __name__ == "__main__":
    main()
