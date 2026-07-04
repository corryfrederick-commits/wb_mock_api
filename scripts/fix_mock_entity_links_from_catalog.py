import json
import random
import shutil
from datetime import datetime
from pathlib import Path


random.seed(20260702)

BASE_DIRS = [
    Path("/var/www/html"),
]

TARGET_FILES = [
    "communications_feedbacks.json",
    "promotion_fullstats.json",
    "analytics_sales_funnel.json",
    "analytics_stocks.json",
    "tariffs_acceptance.json",
]

BACKUP_ROOT = Path("/root/mock_json_backup_entity_links_" + datetime.now().strftime("%Y%m%d_%H%M%S"))


PRODUCT_ID_KEYS = {
    "nmID",
    "nmId",
    "nm_id",
    "nm",
    "productId",
    "productID",
    "product_id",
}

VARIANT_ID_KEYS = {
    "chrtID",
    "chrtId",
    "chrt_id",
    "productVariantId",
    "product_variant_id",
}

PRODUCT_TEXT_KEYS = {
    "article",
    "vendorCode",
    "vendor_code",
    "supplierArticle",
    "supplier_article",
    "barcode",
    "barCode",
    "barcodeValue",
    "barcode_value",
    "skus",
    "brand",
    "brandName",
    "brand_name",
    "title",
    "productName",
    "product_name",
    "nmName",
    "nm_name",
    "subjectID",
    "subjectId",
    "subject_id",
    "subjectName",
    "subject_name",
    "techSize",
    "tech_size",
}

WAREHOUSE_KEYS = {
    "warehouseID",
    "warehouseId",
    "warehouse_id",
    "warehouseName",
    "warehouse_name",
    "warehouseAddress",
    "warehouse_address",
    "officeID",
    "officeId",
    "office_id",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def first_array(data, preferred_keys=None):
    if preferred_keys is None:
        preferred_keys = []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in preferred_keys:
            if isinstance(data.get(key), list):
                return data[key]

        for value in data.values():
            if isinstance(value, list):
                return value

    return []


def pick(obj, keys):
    for key in keys:
        if isinstance(obj, dict) and key in obj and obj[key] not in (None, ""):
            return obj[key]
    return None


def scalar(value):
    return isinstance(value, (str, int, float, bool)) or value is None


def walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for item in value:
            yield from walk_dicts(item)


def extract_products(base):
    path = base / "items_cards.json"
    data = load_json(path)
    cards = first_array(data, preferred_keys=["cards", "data", "result"])

    products = []

    for card in cards:
        if not isinstance(card, dict):
            continue

        nm_id = pick(card, ["nmID", "nmId", "nm_id", "nm"])
        if nm_id is None:
            continue

        article = pick(card, ["vendorCode", "vendor_code", "article", "supplierArticle"]) or f"art-{nm_id}"
        brand = pick(card, ["brand", "brandName", "brand_name"]) or "Unknown brand"
        title = pick(card, ["title", "productName", "product_name", "nmName"]) or f"Product {nm_id}"
        subject_id = pick(card, ["subjectID", "subjectId", "subject_id"])
        subject_name = pick(card, ["subjectName", "subject_name", "subject"])

        sizes = card.get("sizes")
        if not isinstance(sizes, list) or not sizes:
            products.append({
                "nm_id": nm_id,
                "chrt_id": None,
                "article": article,
                "vendor_code": article,
                "barcode": None,
                "barcodes": [],
                "brand": brand,
                "title": title,
                "subject_id": subject_id,
                "subject_name": subject_name,
                "tech_size": None,
            })
            continue

        for size in sizes:
            if not isinstance(size, dict):
                continue

            chrt_id = pick(size, ["chrtID", "chrtId", "chrt_id"])
            tech_size = pick(size, ["techSize", "tech_size", "size"])

            skus = pick(size, ["skus", "barcodes", "barCodes"])
            if isinstance(skus, str):
                barcodes = [skus]
            elif isinstance(skus, list):
                barcodes = [str(x) for x in skus if x not in (None, "")]
            else:
                barcodes = []

            barcode = barcodes[0] if barcodes else pick(size, ["barcode", "barCode", "barcodeValue"])

            products.append({
                "nm_id": nm_id,
                "chrt_id": chrt_id,
                "article": article,
                "vendor_code": article,
                "barcode": barcode,
                "barcodes": barcodes,
                "brand": brand,
                "title": title,
                "subject_id": subject_id,
                "subject_name": subject_name,
                "tech_size": tech_size,
            })

    if not products:
        raise RuntimeError(f"No products extracted from {path}")

    return products


def extract_warehouses(base):
    path = base / "items_warehouses.json"
    data = load_json(path)
    rows = first_array(data, preferred_keys=["warehouses", "data", "result"])

    warehouses = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        warehouse_id = pick(row, ["id", "warehouseID", "warehouseId", "warehouse_id"])
        if warehouse_id is None:
            continue

        warehouse_name = pick(row, ["name", "warehouseName", "warehouse_name"]) or f"Warehouse {warehouse_id}"
        warehouse_address = pick(row, ["address", "warehouseAddress", "warehouse_address"]) or None
        office_id = pick(row, ["officeID", "officeId", "office_id"])

        warehouses.append({
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse_name,
            "warehouse_address": warehouse_address,
            "office_id": office_id,
        })

    if not warehouses:
        raise RuntimeError(f"No warehouses extracted from {path}")

    return warehouses


def has_product_context(obj):
    keys = set(obj.keys())
    return bool((keys & PRODUCT_ID_KEYS) or (keys & VARIANT_ID_KEYS) or (keys & PRODUCT_TEXT_KEYS))


def has_warehouse_context(obj):
    keys = set(obj.keys())
    return bool(keys & WAREHOUSE_KEYS)


def patch_existing_product_fields(obj, product):
    changed = 0

    for key in PRODUCT_ID_KEYS:
        if key in obj and scalar(obj[key]):
            obj[key] = product["nm_id"]
            changed += 1

    for key in VARIANT_ID_KEYS:
        if key in obj and scalar(obj[key]) and product["chrt_id"] is not None:
            obj[key] = product["chrt_id"]
            changed += 1

    replacements = {
        "article": product["article"],
        "vendorCode": product["vendor_code"],
        "vendor_code": product["vendor_code"],
        "supplierArticle": product["article"],
        "supplier_article": product["article"],
        "barcode": product["barcode"],
        "barCode": product["barcode"],
        "barcodeValue": product["barcode"],
        "barcode_value": product["barcode"],
        "brand": product["brand"],
        "brandName": product["brand"],
        "brand_name": product["brand"],
        "title": product["title"],
        "productName": product["title"],
        "product_name": product["title"],
        "nmName": product["title"],
        "nm_name": product["title"],
        "subjectID": product["subject_id"],
        "subjectId": product["subject_id"],
        "subject_id": product["subject_id"],
        "subjectName": product["subject_name"],
        "subject_name": product["subject_name"],
        "techSize": product["tech_size"],
        "tech_size": product["tech_size"],
    }

    for key, value in replacements.items():
        if key in obj and value is not None:
            obj[key] = value
            changed += 1

    if "skus" in obj and product["barcodes"]:
        obj["skus"] = product["barcodes"]
        changed += 1

    return changed


def patch_existing_warehouse_fields(obj, warehouse):
    changed = 0

    replacements = {
        "warehouseID": warehouse["warehouse_id"],
        "warehouseId": warehouse["warehouse_id"],
        "warehouse_id": warehouse["warehouse_id"],
        "warehouseName": warehouse["warehouse_name"],
        "warehouse_name": warehouse["warehouse_name"],
        "warehouseAddress": warehouse["warehouse_address"],
        "warehouse_address": warehouse["warehouse_address"],
        "officeID": warehouse["office_id"],
        "officeId": warehouse["office_id"],
        "office_id": warehouse["office_id"],
    }

    for key, value in replacements.items():
        if key in obj and value is not None:
            obj[key] = value
            changed += 1

    return changed


def backup_file(path, base):
    rel_base = "web" if str(base) == "/var/www/html" else "root"
    dst = BACKUP_ROOT / rel_base / path.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)


def patch_file(path, products, warehouses, base):
    data = load_json(path)

    product_patches = 0
    warehouse_patches = 0

    product_index = 0
    warehouse_index = 0

    for obj in walk_dicts(data):
        if not isinstance(obj, dict):
            continue

        if has_product_context(obj):
            product = products[product_index % len(products)]
            product_index += 1
            product_patches += patch_existing_product_fields(obj, product)

        if has_warehouse_context(obj):
            warehouse = warehouses[warehouse_index % len(warehouses)]
            warehouse_index += 1
            warehouse_patches += patch_existing_warehouse_fields(obj, warehouse)

    backup_file(path, base)
    save_json(path, data)

    return product_patches, warehouse_patches


def main():
    print("backup root:", BACKUP_ROOT)

    for base in BASE_DIRS:
        if not base.exists():
            print("skip missing base:", base)
            continue

        print()
        print("========== base:", base, "==========")

        products = extract_products(base)
        warehouses = extract_warehouses(base)

        print("catalog products/variants:", len(products))
        print("catalog warehouses:", len(warehouses))

        for filename in TARGET_FILES:
            path = base / filename
            if not path.exists():
                print("skip missing:", path)
                continue

            product_patches, warehouse_patches = patch_file(path, products, warehouses, base)

            print(
                filename,
                "product_fields_patched=" + str(product_patches),
                "warehouse_fields_patched=" + str(warehouse_patches),
            )

    print()
    print("done")


if __name__ == "__main__":
    main()
