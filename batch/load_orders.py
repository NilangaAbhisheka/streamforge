from pathlib import Path

from connection import get_connection
from order_readers import read_orders_from_json
from order_validators import validate_order
from psycopg.errors import ForeignKeyViolation
from psycopg.types.json import Jsonb


JSON_FILE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "orders.json"
)


def batch_already_completed(connection, batch_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM pipeline_batches
            WHERE batch_id = %s
              AND status = 'COMPLETED'
            """,
            (batch_id,),
        )

        return cursor.fetchone() is not None


def start_batch(
    connection,
    batch_id,
    records_received,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pipeline_batches (
                batch_id,
                pipeline_name,
                records_received,
                status
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                batch_id,
                "order_batch",
                records_received,
                "STARTED",
            ),
        )


def complete_batch(
    connection,
    batch_id,
    records_processed,
    records_quarantined,
    records_skipped,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pipeline_batches
            SET
                completed_at = CURRENT_TIMESTAMP,
                status = 'COMPLETED',
                records_processed = %s,
                records_quarantined = %s,
                records_skipped = %s
            WHERE batch_id = %s
            """,
            (
                records_processed,
                records_quarantined,
                records_skipped,
                batch_id,
            ),
        )


def fail_batch(connection, batch_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pipeline_batches
            SET
                completed_at = CURRENT_TIMESTAMP,
                status = 'FAILED'
            WHERE batch_id = %s
            """,
            (batch_id,),
        )


def order_already_loaded(connection, order_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM orders
            WHERE order_id = %s
            """,
            (order_id,),
        )

        return cursor.fetchone() is not None


def insert_order(connection, order):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO orders (
                order_id,
                customer_id,
                store_id,
                status,
                order_total
            )
            OVERRIDING SYSTEM VALUE
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                order["order_id"],
                order["customer_id"],
                order["store_id"],
                order["status"],
                order["order_total"],
            ),
        )


def insert_order_items(connection, order):
    with connection.cursor() as cursor:
        for item in order["items"]:
            cursor.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    quantity,
                    unit_price
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    order["order_id"],
                    item["product_id"],
                    item["quantity"],
                    item["unit_price"],
                ),
            )


def quarantine_order(
    connection,
    order,
    batch_id,
    failure_reason,
    failure_type,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pipeline_quarantine (
                source,
                source_record_id,
                raw_record,
                failure_reason,
                failure_type,
                batch_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (
                source,
                batch_id,
                source_record_id
            )
            DO NOTHING
            """,
            (
                "order_batch",
                str(order.get("order_id")),
                Jsonb(order),
                failure_reason,
                failure_type,
                batch_id,
            ),
        )


def process_order(
    connection,
    order,
    batch_id,
):
    validation_result = validate_order(order)

    if not validation_result["valid"]:
        failure_reason = "; ".join(
            validation_result["errors"]
        )

        quarantine_order(
            connection,
            order,
            batch_id,
            failure_reason,
            "VALIDATION_ERROR",
        )

        return "QUARANTINED"

    if order_already_loaded(
        connection,
        order["order_id"],
    ):
        return "SKIPPED"

    savepoint_name = (
        f"order_{order['order_id']}_savepoint"
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SAVEPOINT {savepoint_name}"
            )

        insert_order(
            connection,
            order,
        )

        insert_order_items(
            connection,
            order,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"RELEASE SAVEPOINT {savepoint_name}"
            )

        return "PROCESSED"

    except ForeignKeyViolation as error:
        with connection.cursor() as cursor:
            cursor.execute(
                f"ROLLBACK TO SAVEPOINT {savepoint_name}"
            )

        quarantine_order(
            connection,
            order,
            batch_id,
            str(error),
            "REFERENCE_ERROR",
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"RELEASE SAVEPOINT {savepoint_name}"
            )

        return "QUARANTINED"


def load_orders(
    orders,
    batch_id,
):
    connection = get_connection()

    records_received = len(orders)
    records_processed = 0
    records_quarantined = 0
    records_skipped = 0

    try:
        if batch_already_completed(
            connection,
            batch_id,
        ):
            print(
                f"Batch {batch_id} already completed. "
                "Skipping."
            )
            return

        start_batch(
            connection,
            batch_id,
            records_received,
        )

        for order in orders:
            result = process_order(
                connection,
                order,
                batch_id,
            )

            if result == "PROCESSED":
                records_processed += 1

            elif result == "QUARANTINED":
                records_quarantined += 1

            elif result == "SKIPPED":
                records_skipped += 1

        if (
            records_received
            != records_processed
            + records_quarantined
            + records_skipped
        ):
            raise RuntimeError(
                "Batch reconciliation failed: "
                "received does not equal "
                "processed + quarantined + skipped."
            )

        complete_batch(
            connection,
            batch_id,
            records_processed,
            records_quarantined,
            records_skipped,
        )

        connection.commit()

        print(
            f"Batch {batch_id} completed successfully."
        )
        print(
            f"Records received: {records_received}"
        )
        print(
            "Records successfully processed: "
            f"{records_processed}"
        )
        print(
            f"Records quarantined: {records_quarantined}"
        )
        print(
            f"Records skipped: {records_skipped}"
        )

    except Exception as error:
        connection.rollback()

        print(
            f"Batch {batch_id} failed."
        )
        print(f"Error: {error}")

        raise

    finally:
        connection.close()


if __name__ == "__main__":
    orders = read_orders_from_json(
        JSON_FILE_PATH
    )

    load_orders(
        orders,
        "ORDER-BATCH-001",
    )