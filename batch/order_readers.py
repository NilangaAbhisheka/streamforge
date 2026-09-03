import json


def read_orders_from_json(file_path):
    with open(
        file_path,
        mode="r",
        encoding="utf-8",
    ) as json_file:
        orders = json.load(json_file)

    if not isinstance(orders, list):
        raise ValueError(
            "Orders JSON must contain a list of orders."
        )

    return orders

