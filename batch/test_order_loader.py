from pathlib import Path

from connection import get_connection
from load_orders import load_orders
from order_readers import read_orders_from_json


JSON_FILE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "orders.json"
)


def get_order(order_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    order_id,
                    customer_id,
                    store_id,
                    status,
                    order_total
                FROM orders
                WHERE order_id = %s
                """,
                (order_id,),
            )

            return cursor.fetchone()

    finally:
        connection.close()


def get_order_item_count(order_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM order_items
                WHERE order_id = %s
                """,
                (order_id,),
            )

            return cursor.fetchone()[0]

    finally:
        connection.close()


def get_quarantine_count(order_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM pipeline_quarantine
                WHERE source = 'order_batch'
                  AND source_record_id = %s
                """,
                (str(order_id),),
            )

            return cursor.fetchone()[0]

    finally:
        connection.close()


if __name__ == "__main__":
    orders = read_orders_from_json(
        JSON_FILE_PATH
    )

    load_orders(
    orders,
    "ORDER-BATCH-002",
    )

    order_1001 = get_order(1001)
    order_1002 = get_order(1002)
    order_1003 = get_order(1003)
    order_1004 = get_order(1004)
    order_1005 = get_order(1005)

    assert order_1001 is not None
    assert order_1002 is not None
    assert order_1003 is not None

    assert get_order_item_count(1001) == 1
    assert get_order_item_count(1002) == 1
    assert get_order_item_count(1003) == 2

    assert order_1004 is None
    assert order_1005 is None

    assert get_quarantine_count(1004) == 1

    print("\nOrder loader integration test completed.")
