import json
import random
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

WEB_DIR = Path("/var/www/html")
random.seed(20260629)

ORDER_DATASETS = {
    "orders_fbs_new.json": ("fbs", "new", 1000001),
    "orders_fbs_current.json": ("fbs", "current", 1100001),
    "orders_fbs_archive.json": ("fbs", "archive", 1900001),

    "orders_dbs_new.json": ("dbs", "new", 2000001),
    "orders_dbs_completed.json": ("dbs", "completed", 2100001),

    "orders_dbw_new.json": ("dbw", "new", 3000001),
    "orders_dbw_completed.json": ("dbw", "completed", 3100001),

    "orders_pickup_new.json": ("pickup", "new", 4000001),
}

STATUS_DATASETS = {
    "orders_fbs_statuses.json": [
        "orders_fbs_new.json",
        "orders_fbs_current.json",
        "orders_fbs_archive.json",
    ],
    "orders_dbs_statuses.json": [
        "orders_dbs_new.json",
        "orders_dbs_completed.json",
    ],
    "orders_dbw_statuses.json": [
        "orders_dbw_new.json",
        "orders_dbw_completed.json",
    ],
    "orders_pickup_statuses.json": [
        "orders_pickup_new.json",
    ],
}

DELIVERY_TYPES_BY_FLOW = {
    "fbs": ["fbs"],
    "dbs": ["dbs", "edbs", "dbsPickupPoint"],
    "dbw": ["dbw"],
    "pickup": ["pickupPoint", "selfPickup"],
}

DELIVERY_SERVICE_BY_FLOW = {
    "fbs": ["WB_FBS", "SELLER_TO_WB"],
    "dbs": ["SELLER_COURIER", "SELLER_PICKUP_POINT"],
    "dbw": ["WB_WAREHOUSE"],
    "pickup": ["PICKUP_POINT", "SELF_PICKUP"],
}

PAY_MODES = ["prepaid", "card", "cashless"]

ORDERS = []
ORDERS_BY_FILE = {}


def load_json(filename):
    path = WEB_DIR / filename
    if not path.exists():
        print(f"SKIP missing file: {filename}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(filename, data):
    path = WEB_DIR / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def first_array(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        preferred_keys = [
            "orders",
            "cards",
            "stocks",
            "warehouses",
            "data",
            "result",
            "reports",
            "sales",
            "campaigns",
            "feedbacks",
            "chats",
            "supplies",
        ]

        for key in preferred_keys:
            if isinstance(data.get(key), list):
                return data[key]

        for value in data.values():
            if isinstance(value, list):
                return value

    return []


def walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for item in value:
            yield from walk_dicts(item)


def recent_iso(offset_days=60):
    dt = datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, offset_days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return dt.isoformat()


def make_barcode(i):
    return str(4600000000000 + i * 137 + random.randint(10, 99))


def make_products(count=60):
    products = []

    for i in range(1, count + 1):
        nm_id = 70000000 + i
        chrt_id = 170000000 + i
        article = f"art-{1000 + i}"
        barcodes = [
            make_barcode(i * 10 + j)
            for j in range(1, random.randint(2, 4))
        ]

        products.append({
            "nm_id": nm_id,
            "chrt_id": chrt_id,
            "article": article,
            "vendor_code": article,
            "barcode": barcodes[0],
            "barcodes": barcodes,
            "brand": f"Brand {i % 7 + 1}",
            "subject_id": 500 + i % 12,
            "subject_name": f"Категория {i % 12 + 1}",
        })

    return products


def make_warehouses(count=20):
    warehouses = []

    for i in range(1, count + 1):
        warehouses.append({
            "warehouse_id": 1000 + i,
            "office_id": 2000 + i,
            "warehouse_name": f"Склад WB {i}",
            "warehouse_address": f"г. Москва, складская зона {i}",
        })

    return warehouses


PRODUCTS = make_products()
WAREHOUSES = make_warehouses()


def delivery_type_for_flow(flow):
    return random.choice(DELIVERY_TYPES_BY_FLOW.get(flow, [flow]))


def delivery_service_for_flow(flow):
    return random.choice(DELIVERY_SERVICE_BY_FLOW.get(flow, ["UNKNOWN"]))


def set_any_key(obj, keys, value, add_key=None):
    found = False

    for key in keys:
        if key in obj:
            obj[key] = value
            found = True

    if not found and add_key:
        obj[add_key] = value


def patch_product_fields(obj, product, force=False):
    product_keys = {
        "nmId", "nmID", "nm_id",
        "chrtId", "chrtID", "chrt_id",
        "article", "vendorCode", "vendor_code", "supplierArticle",
        "barcode", "barCode", "skus",
    }

    if not force and not any(key in obj for key in product_keys):
        return

    # Всегда пишем канонические поля.
    obj["nmId"] = product["nm_id"]
    obj["chrtId"] = product["chrt_id"]
    obj["article"] = product["article"]
    obj["vendorCode"] = product["vendor_code"]
    obj["barcode"] = product["barcode"]
    obj["skus"] = product["barcodes"]

    # И обновляем возможные альтернативные ключи, если они уже есть.
    for key in ("nmID", "nm_id"):
        if key in obj:
            obj[key] = product["nm_id"]

    for key in ("chrtID", "chrt_id"):
        if key in obj:
            obj[key] = product["chrt_id"]

    for key in ("supplierArticle",):
        if key in obj:
            obj[key] = product["article"]

    for key in ("vendor_code",):
        if key in obj:
            obj[key] = product["vendor_code"]

    for key in ("barCode",):
        if key in obj:
            obj[key] = product["barcode"]

def patch_warehouse_fields(obj, warehouse, force=False):
    warehouse_keys = {
        "warehouseId", "warehouseID", "warehouse_id",
        "officeId", "officeID", "office_id",
        "warehouseName", "warehouse_name",
        "warehouseAddress", "warehouse_address",
    }

    if not force and not any(key in obj for key in warehouse_keys):
        return

    # Всегда пишем канонические поля.
    obj["warehouseId"] = warehouse["warehouse_id"]
    obj["officeId"] = warehouse["office_id"]
    obj["warehouseName"] = warehouse["warehouse_name"]
    obj["warehouseAddress"] = warehouse["warehouse_address"]

    # И обновляем возможные альтернативные ключи.
    for key in ("warehouseID", "warehouse_id"):
        if key in obj:
            obj[key] = warehouse["warehouse_id"]

    for key in ("officeID", "office_id"):
        if key in obj:
            obj[key] = warehouse["office_id"]

    for key in ("warehouse_name",):
        if key in obj:
            obj[key] = warehouse["warehouse_name"]

    for key in ("warehouse_address",):
        if key in obj:
            obj[key] = warehouse["warehouse_address"]

def patch_order_fields(obj, order, force=False):
    order_keys = {
        "id", "orderId", "orderID", "order_id",
        "rid", "srid",
        "orderUid", "order_uid",
        "createdAt", "date", "orderDt", "saleDt",
    }

    if not force and not any(key in obj for key in order_keys):
        return

    # Всегда пишем канонические поля.
    obj["id"] = order["order_id"]
    obj["orderId"] = order["order_id"]
    obj["rid"] = order["rid"]
    obj["srid"] = order["rid"]
    obj["orderUid"] = order["order_uid"]
    obj["createdAt"] = order["created_at"]

    # И обновляем возможные альтернативные ключи.
    for key in ("orderID", "order_id"):
        if key in obj:
            obj[key] = order["order_id"]

    for key in ("order_uid",):
        if key in obj:
            obj[key] = order["order_uid"]

    for key in ("date", "orderDt", "saleDt"):
        if key in obj:
            obj[key] = order["created_at"]

def patch_price_fields(obj, order, force=False):
    if force or "price" in obj:
        obj["price"] = order["price"]

    if force or "salePrice" in obj:
        obj["salePrice"] = order["sale_price"]

    if force or "finalPrice" in obj:
        obj["finalPrice"] = order["final_price"]

    if force or "convertedPrice" in obj:
        obj["convertedPrice"] = order["price"]

    if force or "convertedFinalPrice" in obj:
        obj["convertedFinalPrice"] = order["final_price"]

    if force or "currencyCode" in obj:
        obj["currencyCode"] = 643

    if force or "convertedCurrencyCode" in obj:
        obj["convertedCurrencyCode"] = 643


def make_order(order_id, flow, kind, product, warehouse):
    price = random.randint(900, 12000)
    discount = random.randint(0, min(2500, price // 2))
    final_price = price - discount

    return {
        "order_id": order_id,
        "rid": f"rid_{order_id}",
        "order_uid": f"{order_id}_{uuid.uuid4().hex[:24]}",
        "order_code": f"ORD-{order_id}",
        "flow": flow,
        "kind": kind,
        "created_at": recent_iso(),
        "product": deepcopy(product),
        "warehouse": deepcopy(warehouse),
        "price": price,
        "sale_price": final_price,
        "final_price": final_price,
        "delivery_type": delivery_type_for_flow(flow),
        "delivery_service": delivery_service_for_flow(flow),
        "pay_mode": random.choice(PAY_MODES),
    }


def patch_order_record(record, order):
    product = order["product"]
    warehouse = order["warehouse"]

    patch_order_fields(record, order, force=True)
    patch_product_fields(record, product, force=True)
    patch_warehouse_fields(record, warehouse, force=True)
    patch_price_fields(record, order, force=True)

    record["orderCode"] = order["order_code"]
    record["deliveryType"] = order["delivery_type"]
    record["deliveryMethod"] = order["delivery_type"]
    record["deliveryService"] = order["delivery_service"]
    record["payMode"] = order["pay_mode"]

    if order["kind"] == "archive":
        record["isArchive"] = True


def patch_order_files():
    for filename, (flow, kind, id_start) in ORDER_DATASETS.items():
        data = load_json(filename)
        if data is None:
            continue

        rows = first_array(data)
        file_orders = []

        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue

            product = PRODUCTS[index % len(PRODUCTS)]
            warehouse = WAREHOUSES[index % len(WAREHOUSES)]
            order = make_order(id_start + index, flow, kind, product, warehouse)

            patch_order_record(row, order)

            file_orders.append(order)
            ORDERS.append(order)

        ORDERS_BY_FILE[filename] = file_orders
        save_json(filename, data)
        print(f"OK orders linked: {filename} rows={len(file_orders)}")


def patch_status_files():
    status_values = [
        "new",
        "confirmed",
        "assembly",
        "in_delivery",
        "completed",
        "cancelled",
    ]

    for filename, source_files in STATUS_DATASETS.items():
        data = load_json(filename)
        if data is None:
            continue

        source_orders = []
        for source_file in source_files:
            source_orders.extend(ORDERS_BY_FILE.get(source_file, []))

        if not source_orders:
            continue

        rows = first_array(data)

        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue

            order = source_orders[index % len(source_orders)]
            patch_order_fields(row, order, force=True)

            row["orderId"] = order["order_id"]
            row["rid"] = order["rid"]
            row["orderUid"] = order["order_uid"]
            row["status"] = random.choice(status_values)
            row["updatedAt"] = recent_iso(20)

        save_json(filename, data)
        print(f"OK statuses linked: {filename} rows={len(rows)}")


def patch_items_cards():
    filename = "items_cards.json"
    data = load_json(filename)
    if data is None:
        return

    rows = first_array(data)

    if rows:
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue

            product = PRODUCTS[index % len(PRODUCTS)]
            patch_product_fields(row, product, force=True)

            row["brand"] = product["brand"]
            row["subjectID"] = product["subject_id"]
            row["subjectName"] = product["subject_name"]

            for child in walk_dicts(row):
                patch_product_fields(child, product, force=False)

    save_json(filename, data)
    print(f"OK products linked: {filename} rows={len(rows)}")


def patch_items_stocks():
    filename = "items_stocks.json"
    data = load_json(filename)
    if data is None:
        return

    rows = first_array(data)

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue

        product = PRODUCTS[index % len(PRODUCTS)]
        warehouse = WAREHOUSES[index % len(WAREHOUSES)]

        patch_product_fields(row, product, force=True)
        patch_warehouse_fields(row, warehouse, force=True)

        row["quantity"] = random.randint(1, 300)
        row["inWayToClient"] = random.randint(0, 20)
        row["inWayFromClient"] = random.randint(0, 10)

    save_json(filename, data)
    print(f"OK stocks linked: {filename} rows={len(rows)}")


def patch_items_warehouses():
    filename = "items_warehouses.json"
    data = load_json(filename)
    if data is None:
        return

    rows = first_array(data)

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue

        warehouse = WAREHOUSES[index % len(WAREHOUSES)]
        patch_warehouse_fields(row, warehouse, force=True)

    save_json(filename, data)
    print(f"OK warehouses linked: {filename} rows={len(rows)}")


def patch_report_or_finance_file(filename):
    data = load_json(filename)
    if data is None or not ORDERS:
        return

    rows = first_array(data)

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue

        order = ORDERS[index % len(ORDERS)]
        product = order["product"]
        warehouse = order["warehouse"]

        patch_order_fields(row, order, force=True)
        patch_product_fields(row, product, force=True)
        patch_warehouse_fields(row, warehouse, force=True)
        patch_price_fields(row, order, force=True)

        row["orderId"] = order["order_id"]
        row["srid"] = order["rid"]
        row["rid"] = order["rid"]
        row["saleDt"] = order["created_at"]
        row["operationDate"] = recent_iso(30)

    save_json(filename, data)
    print(f"OK reports/finance linked: {filename} rows={len(rows)}")


def patch_promotion_files():
    for filename in ["promotion_campaigns.json", "promotion_fullstats.json"]:
        data = load_json(filename)
        if data is None:
            continue

        rows = first_array(data)

        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue

            product = PRODUCTS[index % len(PRODUCTS)]
            patch_product_fields(row, product, force=True)

            advert_id = 900000 + index
            row["advertId"] = advert_id
            row["campaignId"] = advert_id

        save_json(filename, data)
        print(f"OK promotion linked: {filename} rows={len(rows)}")


def patch_communications_files():
    for filename in ["communications_feedbacks.json", "communications_chats.json"]:
        data = load_json(filename)
        if data is None or not ORDERS:
            continue

        rows = first_array(data)

        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue

            order = ORDERS[index % len(ORDERS)]
            product = order["product"]

            patch_order_fields(row, order, force=True)
            patch_product_fields(row, product, force=True)

            row["orderId"] = order["order_id"]
            row["rid"] = order["rid"]

        save_json(filename, data)
        print(f"OK communications linked: {filename} rows={len(rows)}")


def main():
    if not WEB_DIR.exists():
        raise SystemExit(f"Нет папки {WEB_DIR}")

    patch_order_files()
    patch_status_files()

    patch_items_cards()
    patch_items_stocks()
    patch_items_warehouses()

    for filename in [
        "report_orders.json",
        "report_sales.json",
        "finance_sales_reports.json",
        "finance_sales_reports_detailed.json",
    ]:
        patch_report_or_finance_file(filename)

    patch_promotion_files()
    patch_communications_files()

    print()
    print("OK: mock JSON связаны общими products / warehouses / orders")
    print("OK: deliveryType теперь из контролируемого словаря")


if __name__ == "__main__":
    main()
