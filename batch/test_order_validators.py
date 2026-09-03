from order_validators import validate_order


valid_registered_order = {
    "customer_id": 1,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 900.00,
    "items": [
        {
            "product_id": 1,
            "quantity": 2,
            "unit_price": 450.00,
        }
    ],
}


valid_walk_in_order = {
    "customer_id": None,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 450.00,
    "items": [
        {
            "product_id": 1,
            "quantity": 1,
            "unit_price": 450.00,
        }
    ],
}


invalid_quantity_order = {
    "customer_id": 1,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 900.00,
    "items": [
        {
            "product_id": 1,
            "quantity": -2,
            "unit_price": 450.00,
        }
    ],
}


invalid_total_order = {
    "customer_id": 1,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 1000.00,
    "items": [
        {
            "product_id": 1,
            "quantity": 2,
            "unit_price": 450.00,
        }
    ],
}


invalid_status_order = {
    "customer_id": 1,
    "store_id": 1,
    "status": "UNKNOWN",
    "order_total": 450.00,
    "items": [
        {
            "product_id": 1,
            "quantity": 1,
            "unit_price": 450.00,
        }
    ],
}


multiple_invalid_items_order = {
    "customer_id": 1,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 900.00,
    "items": [
        {
            "product_id": 1,
            "quantity": -2,
            "unit_price": 450.00,
        },
        {
            "product_id": 99999,
            "quantity": 0,
            "unit_price": -100.00,
        },
    ],
}


missing_items_order = {
    "customer_id": 1,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 0.00,
    "items": [],
}


zero_total_order = {
    "customer_id": None,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 0.00,
    "items": [
        {
            "product_id": 1,
            "quantity": 1,
            "unit_price": 450.00,
        }
    ],
}


invalid_customer_id_order = {
    "customer_id": -10,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 450.00,
    "items": [
        {
            "product_id": 1,
            "quantity": 1,
            "unit_price": 450.00,
        }
    ],
}


missing_item_fields_order = {
    "customer_id": 1,
    "store_id": 1,
    "status": "COMPLETED",
    "order_total": 450.00,
    "items": [
        {}
    ],
}


def run_test(name, order, expected_valid):
    result = validate_order(order)

    print(f"\n{name}")
    print(f"Valid: {result['valid']}")
    print(f"Errors: {result['errors']}")

    assert result["valid"] == expected_valid


if __name__ == "__main__":
    run_test(
        "Valid registered order",
        valid_registered_order,
        True,
    )

    run_test(
        "Valid walk-in order",
        valid_walk_in_order,
        True,
    )

    run_test(
        "Invalid quantity",
        invalid_quantity_order,
        False,
    )

    run_test(
        "Invalid order total",
        invalid_total_order,
        False,
    )

    run_test(
        "Invalid status",
        invalid_status_order,
        False,
    )

    run_test(
        "Multiple invalid items",
        multiple_invalid_items_order,
        False,
    )

    run_test(
        "Missing items",
        missing_items_order,
        False,
    )

    run_test(
        "Zero order total",
        zero_total_order,
        False,
    )

    run_test(
        "Invalid customer ID",
        invalid_customer_id_order,
        False,
    )

    run_test(
        "Missing item fields",
        missing_item_fields_order,
        False,
    )

    print("\nAll order validator tests passed.")