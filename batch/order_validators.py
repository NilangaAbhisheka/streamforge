from decimal import Decimal


VALID_ORDER_STATUSES = {
    "PENDING",
    "COMPLETED",
    "CANCELLED",
    "REFUNDED",
}


def validate_order(order):
    errors = []

    customer_id = order.get("customer_id")
    store_id = order.get("store_id")
    status = order.get("status")
    order_total = order.get("order_total")
    items = order.get("items")

    # Customer ID is optional because walk-in customers are allowed.
    if customer_id is not None:
        if not isinstance(customer_id, int) or customer_id <= 0:
            errors.append("customer_id is invalid")

    # Store is required.
    if store_id is None:
        errors.append("store_id is missing")
    elif not isinstance(store_id, int) or store_id <= 0:
        errors.append("store_id is invalid")

    # Status is required and must be one of the supported values.
    if not status:
        errors.append("status is missing")
    elif status not in VALID_ORDER_STATUSES:
        errors.append(
            f"invalid order status: {status}"
        )

    # Order total is required and cannot be negative.
    if order_total is None:
        errors.append("order_total is missing")
    else:
        try:
            order_total = Decimal(str(order_total))

            if order_total < 0:
                errors.append(
                    "order_total cannot be negative"
                )

        except Exception:
            errors.append("order_total is invalid")

    # An order must contain at least one item.
    if not items:
        errors.append("order must contain at least one item")
    elif not isinstance(items, list):
        errors.append("items must be a list")
    else:
        for index, item in enumerate(items, start=1):
            item_errors = validate_order_item(item)

            for error in item_errors:
                errors.append(
                    f"item {index}: {error}"
                )

    # Validate the relationship between the order total
    # and its items only when the required data is valid.
    if (
        order_total is not None
        and isinstance(items, list)
        and items
        and all(
            isinstance(item, dict)
            for item in items
        )
    ):
        item_validation_errors = []

        for item in items:
            item_validation_errors.extend(
                validate_order_item(item)
            )

        if not item_validation_errors:
            calculated_total = Decimal("0.00")

            for item in items:
                quantity = item["quantity"]
                unit_price = Decimal(
                    str(item["unit_price"])
                )

                calculated_total += (
                    Decimal(quantity) * unit_price
                )

            if order_total != calculated_total:
                errors.append(
                    "order_total does not match "
                    "calculated item total"
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_order_item(item):
    errors = []

    product_id = item.get("product_id")
    quantity = item.get("quantity")
    unit_price = item.get("unit_price")

    # Product ID is required.
    if product_id is None:
        errors.append("product_id is missing")
    elif not isinstance(product_id, int) or product_id <= 0:
        errors.append("product_id is invalid")

    # Quantity must be a positive integer.
    if quantity is None:
        errors.append("quantity is missing")
    elif not isinstance(quantity, int) or quantity <= 0:
        errors.append("quantity must be greater than zero")

    # Unit price must be positive.
    if unit_price is None:
        errors.append("unit_price is missing")
    else:
        try:
            unit_price = Decimal(str(unit_price))

            if unit_price <= 0:
                errors.append(
                    "unit_price must be greater than zero"
                )

        except Exception:
            errors.append("unit_price is invalid")

    return errors