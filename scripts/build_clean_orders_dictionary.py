import json
import csv
from pathlib import Path
from collections import defaultdict

IN_PATH = Path("/root/wb_yaml_field_dictionary/dataset_field_dictionary.json")
OUT_DIR = Path("/root/wb_yaml_field_dictionary")
PUBLIC_DIR = Path("/var/www/html/metadata")

OUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

rows = json.loads(IN_PATH.read_text(encoding="utf-8"))

ORDER_DATASETS_FOR_CORE = {
    "orders_fbs_new",
    "orders_fbs_current",
    "orders_fbs_archive",
    "orders_dbs_new",
    "orders_dbs_completed",
    "orders_dbw_new",
    "orders_dbw_completed",
    "orders_pickup_new",
}

OVERRIDES = {
    "order_id": {
        "business_name_ru": "ID сборочного задания WB",
        "description_ru": "Идентификатор сборочного задания или заказа в API Wildberries. В разных методах может приходить как orderId, orderID или id.",
        "description_en": "Assembly order ID / order ID in Wildberries API.",
        "semantic_type": "order_identifier",
        "is_key": True,
    },
    "rid": {
        "business_name_ru": "Уникальный ID заказа WB",
        "description_ru": "Уникальный идентификатор заказа Wildberries. Используется для связи заказов с продажами, возвратами, отчётами и финансовыми детализациями. В ряде методов WB этому же смыслу соответствует поле srid.",
        "description_en": "Unique order ID. In several WB reports and finance methods, srid corresponds to rid.",
        "semantic_type": "order_identifier",
        "is_key": True,
    },
    "srid": {
        "business_name_ru": "Уникальный ID заказа WB в отчётах",
        "description_ru": "Идентификатор заказа в отчётах и финансовых методах WB. Для Marketplace API по смыслу соответствует rid из методов сборочных заданий.",
        "description_en": "Order ID in WB reports and finance methods. In Marketplace API responses, srid corresponds to rid.",
        "semantic_type": "order_identifier",
        "is_key": True,
    },
    "order_uid": {
        "business_name_ru": "ID корзины / транзакции",
        "description_ru": "Идентификатор транзакции для группировки сборочных заданий. Заказы из одной корзины покупателя могут иметь одинаковый orderUid.",
        "description_en": "Transaction/cart ID for grouping assembly orders. Orders in the same buyer cart can have the same orderUid.",
        "semantic_type": "cart_identifier",
        "is_key": False,
    },
    "nm_id": {
        "business_name_ru": "Артикул WB / номер товара WB",
        "description_ru": "Номенклатурный номер товара Wildberries. Используется для связи заказа с карточкой товара, остатками, аналитикой, рекламой и отчётами.",
        "description_en": "WB item number / Wildberries article number.",
        "semantic_type": "product_identifier",
        "is_key": True,
    },
    "chrt_id": {
        "business_name_ru": "ID размера / характеристики товара",
        "description_ru": "Идентификатор размера или характеристики товара в системе Wildberries. Используется для различения вариантов одного товара.",
        "description_en": "Size ID / item characteristic ID in WB systems.",
        "semantic_type": "product_variant_identifier",
        "is_key": True,
    },
    "article": {
        "business_name_ru": "Артикул продавца",
        "description_ru": "Артикул товара у продавца. Используется продавцом для внутренней идентификации товара.",
        "description_en": "Seller item number / seller article.",
        "semantic_type": "seller_product_identifier",
        "is_key": False,
    },
    "supplier_article": {
        "business_name_ru": "Артикул продавца",
        "description_ru": "Артикул товара у продавца в отчётах WB.",
        "description_en": "Seller article number.",
        "semantic_type": "seller_product_identifier",
        "is_key": False,
    },
    "barcode": {
        "business_name_ru": "Баркод / штрихкод",
        "description_ru": "Баркод товара или закодированное значение стикера, в зависимости от метода WB. В core.orders используется как идентификатор товарной единицы из заказа.",
        "description_en": "Barcode or encoded sticker value depending on the WB method.",
        "semantic_type": "product_barcode",
        "is_key": False,
    },
    "skus": {
        "business_name_ru": "Список SKU / баркодов",
        "description_ru": "Массив SKU или баркодов товарной единицы в заказе.",
        "description_en": "Item SKU/barcode array.",
        "semantic_type": "product_barcode_array",
        "is_key": False,
    },
    "warehouse_id": {
        "business_name_ru": "ID склада",
        "description_ru": "Идентификатор склада, связанного с заказом. В зависимости от метода может означать склад продавца, склад приёмки или склад отгрузки.",
        "description_en": "Warehouse ID related to the order.",
        "semantic_type": "warehouse_identifier",
        "is_key": True,
    },
    "delivery_type": {
        "business_name_ru": "Тип доставки",
        "description_ru": "Тип доставки заказа. Для наших mock-данных используется словарь: fbs, dbs, edbs, dbsPickupPoint, dbw, pickupPoint, selfPickup.",
        "description_en": "Delivery type. In mock data: fbs, dbs, edbs, dbsPickupPoint, dbw, pickupPoint, selfPickup.",
        "semantic_type": "delivery_type",
        "is_key": False,
    },
    "delivery_method": {
        "business_name_ru": "Метод доставки / модель продажи",
        "description_ru": "Метод доставки или модель продажи. В финансовых отчётах WB описывает sales model and item type.",
        "description_en": "Delivery method / sales model and item type.",
        "semantic_type": "delivery_method",
        "is_key": False,
    },
    "price": {
        "business_name_ru": "Цена заказа",
        "description_ru": "Цена в валюте продажи с учётом скидок, кроме скидки WB Кошелька. В order API значения часто умножены на 100.",
        "description_en": "Price in sale currency including discounts except WB Wallet discount. In order APIs values are often multiplied by 100.",
        "semantic_type": "money_amount",
        "is_key": False,
    },
    "sale_price": {
        "business_name_ru": "Цена продавца со скидкой",
        "description_ru": "Цена продавца в валюте продажи с учётом скидки продавца, без учёта скидки WB Клуба. В order API значения часто умножены на 100.",
        "description_en": "Seller price in sale currency including seller discount, excluding WB Club discount. Often multiplied by 100.",
        "semantic_type": "money_amount",
        "is_key": False,
    },
    "final_price": {
        "business_name_ru": "Итоговая сумма к оплате покупателем",
        "description_ru": "Сумма к оплате покупателем в валюте продажи с учётом всех скидок. В order API значения часто умножены на 100.",
        "description_en": "Final amount charged to the buyer in sale currency including all discounts. Often multiplied by 100.",
        "semantic_type": "money_amount",
        "is_key": False,
    },
    "converted_price": {
        "business_name_ru": "Цена в валюте страны продавца",
        "description_ru": "Цена в валюте страны продавца с учётом скидок, кроме скидки WB Кошелька. В order API значения часто умножены на 100.",
        "description_en": "Price in seller country currency including discounts except WB Wallet discount. Often multiplied by 100.",
        "semantic_type": "money_amount",
        "is_key": False,
    },
    "converted_final_price": {
        "business_name_ru": "Итоговая сумма в валюте страны продавца",
        "description_ru": "Сумма к оплате покупателем в валюте страны продавца с учётом всех скидок. В order API значения часто умножены на 100.",
        "description_en": "Final amount charged to the buyer in seller country currency including all discounts. Often multiplied by 100.",
        "semantic_type": "money_amount",
        "is_key": False,
    },
    "currency_code": {
        "business_name_ru": "Код валюты",
        "description_ru": "Код валюты продажи.",
        "description_en": "Sale currency code.",
        "semantic_type": "currency_code",
        "is_key": False,
    },
    "created_at": {
        "business_name_ru": "Дата и время создания заказа",
        "description_ru": "Дата и время создания заказа или сборочного задания.",
        "description_en": "Order or assembly task creation date and time.",
        "semantic_type": "event_timestamp",
        "is_key": False,
    },
}

# Поля, которые реально важны для текущей модели заказов.
ORDER_MODEL_FIELDS = [
    "order_id",
    "rid",
    "srid",
    "order_uid",
    "nm_id",
    "chrt_id",
    "article",
    "supplier_article",
    "barcode",
    "skus",
    "warehouse_id",
    "delivery_type",
    "delivery_method",
    "price",
    "sale_price",
    "final_price",
    "converted_price",
    "converted_final_price",
    "currency_code",
    "created_at",
]

orders_rows = [
    r for r in rows
    if r.get("dataset_name") in ORDER_DATASETS_FOR_CORE
]

by_field = defaultdict(list)
for r in orders_rows:
    by_field[r.get("normalized_field_name")].append(r)

clean = []

for field in ORDER_MODEL_FIELDS:
    examples = by_field.get(field, [])
    override = OVERRIDES.get(field, {})

    source_field_names = []
    json_paths = []
    datasets = []
    yaml_files = []
    json_value_types = set()

    for r in examples:
        if r.get("source_field_name") and r["source_field_name"] not in source_field_names:
            source_field_names.append(r["source_field_name"])
        if r.get("json_path") and r["json_path"] not in json_paths:
            json_paths.append(r["json_path"])
        if r.get("dataset_name") and r["dataset_name"] not in datasets:
            datasets.append(r["dataset_name"])
        if r.get("matched_yaml_file") and r["matched_yaml_file"] not in yaml_files:
            yaml_files.append(r["matched_yaml_file"])
        for t in (r.get("json_value_types") or {}).keys():
            json_value_types.add(t)

    clean.append({
        "model_layer": "staging/core",
        "model_name": "orders",
        "field_name": field,
        "business_name_ru": override.get("business_name_ru", field),
        "description_ru": override.get("description_ru", ""),
        "description_en": override.get("description_en", ""),
        "semantic_type": override.get("semantic_type", ""),
        "is_key": override.get("is_key", False),
        "source_field_names": source_field_names,
        "source_json_paths": json_paths,
        "source_datasets": datasets,
        "source_yaml_files": yaml_files,
        "json_value_types": sorted(json_value_types),
        "has_actual_examples": bool(examples),
        "notes": "manual_override" if field in OVERRIDES else "",
    })

json_path = OUT_DIR / "orders_field_dictionary_clean.json"
csv_path = OUT_DIR / "orders_field_dictionary_clean.csv"

json_path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")

with csv_path.open("w", newline="", encoding="utf-8") as f:
    fieldnames = [
        "model_layer",
        "model_name",
        "field_name",
        "business_name_ru",
        "description_ru",
        "description_en",
        "semantic_type",
        "is_key",
        "source_field_names",
        "source_json_paths",
        "source_datasets",
        "source_yaml_files",
        "json_value_types",
        "has_actual_examples",
        "notes",
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in clean:
        out = dict(r)
        for k in [
            "source_field_names",
            "source_json_paths",
            "source_datasets",
            "source_yaml_files",
            "json_value_types",
        ]:
            out[k] = json.dumps(out[k], ensure_ascii=False)
        writer.writerow(out)

for p in [json_path, csv_path]:
    target = PUBLIC_DIR / p.name
    target.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

print("OK: clean orders dictionary built")
print("fields:", len(clean))
print("fields with actual examples:", sum(1 for r in clean if r["has_actual_examples"]))
print("fields without actual examples:", sum(1 for r in clean if not r["has_actual_examples"]))
print()
print("Files:")
print(json_path)
print(csv_path)
print()
print("Public URLs:")
print("http://217.60.10.21/metadata/orders_field_dictionary_clean.json")
print("http://217.60.10.21/metadata/orders_field_dictionary_clean.csv")
print()
print("Preview:")
for r in clean:
    print()
    print(r["field_name"])
    print("  business:", r["business_name_ru"])
    print("  desc:", r["description_ru"][:180])
    print("  sources:", ", ".join(r["source_field_names"]))
    print("  datasets:", ", ".join(r["source_datasets"][:5]))
