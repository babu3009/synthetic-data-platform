from __future__ import annotations

from pathlib import Path

from app.services.relational import topo_sort, generate_to_artifacts


def test_topo_sort_simple():
    schema = {
        "tables": [
            {"name": "customers", "columns": [{"name": "id", "pk": True}]},
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "pk": True},
                    {"name": "customer_id", "fk": {"to_table": "customers", "to_column": "id"}},
                ],
            },
        ]
    }
    order = topo_sort(schema["tables"])  # type: ignore[arg-type]
    # customers must come before orders
    assert order.index("customers") < order.index("orders")


def test_generate_relational_with_fk_and_outputs(tmp_path: Path):
    # Customers -> Orders -> OrderItems, plus Products and a junction OrderItemsProducts
    schema = {
        "tables": [
            {
                "name": "customers",
                "columns": [
                    {"name": "id", "pk": True, "unique": True, "provider": {"type": "sequence", "start": 1}},
                    {"name": "name", "provider": {"type": "categorical", "categories": ["Alice", "Bob", "Cara"]}},
                ],
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "pk": True, "unique": True, "provider": {"type": "sequence", "start": 100}},
                    {"name": "customer_id", "fk": {"to_table": "customers", "to_column": "id"}},
                ],
            },
            {
                "name": "order_items",
                "columns": [
                    {"name": "id", "pk": True, "unique": True, "provider": {"type": "sequence", "start": 1000}},
                    {"name": "order_id", "fk": {"to_table": "orders", "to_column": "id"}},
                ],
            },
            {
                "name": "products",
                "columns": [
                    {"name": "id", "pk": True, "unique": True, "provider": {"type": "sequence", "start": 5000}},
                    {"name": "sku", "unique": True, "provider": {"type": "pattern", "pattern": "SKU-????"}},
                ],
            },
            {
                "name": "order_items_products",
                "columns": [
                    {"name": "order_item_id", "fk": {"to_table": "order_items", "to_column": "id"}},
                    {"name": "product_id", "fk": {"to_table": "products", "to_column": "id"}},
                ],
            },
        ]
    }

    rows_per_table = {
        "customers": 50,
        "orders": 200,
        "order_items": 400,
        "products": 25,
        "order_items_products": 400,
    }

    paths_by_table, report = generate_to_artifacts(
        target_dir=tmp_path,
        schema=schema,
        rows_per_table=rows_per_table,
        formats=["csv", "parquet", "xlsx"],
        seed=123,
        chunk_size=100,
    )

    # Output checks: csv/parquet per table, one shared xlsx
    assert set(paths_by_table.keys()) == set(rows_per_table.keys())
    xlsx_paths = set()
    for tname, fmap in paths_by_table.items():
        assert (fmap.get("csv") and fmap["csv"].exists()), f"missing csv for {tname}"
        assert (fmap.get("parquet") and fmap["parquet"].exists()), f"missing parquet for {tname}"
        assert (fmap.get("xlsx") and fmap["xlsx"].exists()), f"missing xlsx for {tname}"
        xlsx_paths.add(str(fmap["xlsx"]))
    # single workbook shared across tables
    assert len(xlsx_paths) == 1

    # FK coverage checks: orphans should be 0 and valid_pct == 1.0 for non-nullable FKs
    fk_keys = [
        "orders.customer_id",
        "order_items.order_id",
        "order_items_products.order_item_id",
        "order_items_products.product_id",
    ]
    for k in fk_keys:
        cov = report["fk_coverage"].get(k)
        assert cov is not None, f"missing coverage for {k}"
        assert cov["orphans"] == 0
        assert abs(cov["valid_pct"] - 1.0) < 1e-9

    # Uniqueness collisions should be 0 for declared unique columns
    for k, v in report["collisions"].items():
        assert v == 0, f"unexpected collisions for {k}: {v}"
