from pathlib import Path

from order_readers import read_orders_from_json


JSON_FILE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "orders.json"
)


if __name__ == "__main__":
    orders = read_orders_from_json(
        JSON_FILE_PATH
    )

    print(f"Orders read: {len(orders)}")

    for order in orders:
        print(
            f"Order {order.get('order_id')}: "
            f"{len(order.get('items', []))} item(s)"
        )

    assert len(orders) == 5

    assert orders[0]["order_id"] == 1001
    assert orders[1]["customer_id"] is None
    assert len(orders[2]["items"]) == 2
    assert orders[3]["order_total"] == 1000.00
    assert orders[4]["items"][0]["product_id"] == 99999

    print("\nAll order reader tests passed.")
