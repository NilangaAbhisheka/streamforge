import json
from decimal import Decimal

from connection import get_connection
from psycopg.errors import ForeignKeyViolation
from psycopg.types.json import Jsonb


PIPELINE_NAME = "fact_sales_batch"
SAVEPOINT_NAME = "fact_order_savepoint"


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
                PIPELINE_NAME,
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


def build_raw_order(
    order,
    formatted_items,
):
    (
        order_id,
        customer_id,
        store_id,
        order_timestamp,
        status,
        order_total,
    ) = order

    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "store_id": store_id,
        "order_timestamp": str(order_timestamp),
        "status": status,
        "order_total": str(order_total),
        "items": formatted_items,
    }


def quarantine_order(
    connection,
    order_id,
    batch_id,
    raw_record,
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
                PIPELINE_NAME,
                str(order_id),
                Jsonb(
                    raw_record,
                    dumps=lambda value: json.dumps(
                        value,
                        default=str,
                    ),
                ),
                failure_reason,
                failure_type,
                batch_id,
            ),
        )


def get_completed_orders(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                o.order_id,
                o.customer_id,
                o.store_id,
                o.order_timestamp,
                o.status,
                o.order_total
            FROM orders o
            WHERE o.status = 'COMPLETED'
            ORDER BY o.order_id
            """
        )

        return cursor.fetchall()


def get_order_items(connection, order_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                order_item_id,
                product_id,
                quantity,
                unit_price
            FROM order_items
            WHERE order_id = %s
            ORDER BY order_item_id
            """,
            (order_id,),
        )

        return cursor.fetchall()


def calculate_order_total(items):
    total = Decimal("0.00")

    for item in items:
        total += (
            Decimal(item["quantity"])
            * Decimal(str(item["unit_price"]))
        )

    return total


def get_product_key(connection, product_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT product_key
            FROM dim_product
            WHERE product_id = %s
            """,
            (product_id,),
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                f"Product dimension lookup failed "
                f"for product_id={product_id}"
            )

        return row[0]


def get_customer_key(connection, customer_id):
    if customer_id is None:
        return 0

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT customer_key
            FROM dim_customer
            WHERE customer_id = %s
            """,
            (customer_id,),
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                f"Customer dimension lookup failed "
                f"for customer_id={customer_id}"
            )

        return row[0]


def get_store_key(connection, store_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT store_key
            FROM dim_store
            WHERE store_id = %s
            """,
            (store_id,),
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                f"Store dimension lookup failed "
                f"for store_id={store_id}"
            )

        return row[0]


def get_date_key(connection, order_timestamp):
    order_date = order_timestamp.date()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT date_key
            FROM dim_date
            WHERE full_date = %s
            """,
            (order_date,),
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                f"Date dimension lookup failed "
                f"for date={order_date}"
            )

        return row[0]


def insert_fact_row(
    connection,
    order_id,
    order_item_id,
    product_key,
    customer_key,
    store_key,
    date_key,
    quantity,
    unit_price,
):
    sales_amount = (
        Decimal(quantity)
        * Decimal(str(unit_price))
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO fact_sales (
                order_id,
                order_item_id,
                product_key,
                customer_key,
                store_key,
                date_key,
                quantity,
                unit_price,
                sales_amount
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (order_item_id)
            DO NOTHING
            """,
            (
                order_id,
                order_item_id,
                product_key,
                customer_key,
                store_key,
                date_key,
                quantity,
                unit_price,
                sales_amount,
            ),
        )

        return cursor.rowcount == 1


def process_order(
    connection,
    order,
    batch_id,
):
    (
        order_id,
        customer_id,
        store_id,
        order_timestamp,
        status,
        order_total,
    ) = order

    items = get_order_items(
        connection,
        order_id,
    )

    if not items:
        return "SKIPPED"

    formatted_items = []

    for item in items:
        formatted_items.append(
            {
                "order_item_id": item[0],
                "product_id": item[1],
                "quantity": item[2],
                "unit_price": item[3],
            }
        )

    raw_order = build_raw_order(
        order,
        formatted_items,
    )

    calculated_total = calculate_order_total(
        formatted_items
    )

    if (
        Decimal(str(order_total))
        != calculated_total
    ):
        quarantine_order(
            connection,
            order_id,
            batch_id,
            raw_order,
            (
                f"Order total mismatch: "
                f"stored={order_total}, "
                f"calculated={calculated_total}"
            ),
            "FACT_VALIDATION_ERROR",
        )

        return "QUARANTINED"

    customer_key = get_customer_key(
        connection,
        customer_id,
    )

    store_key = get_store_key(
        connection,
        store_id,
    )

    date_key = get_date_key(
        connection,
        order_timestamp,
    )

    processed_rows = 0
    skipped_rows = 0

    for item in formatted_items:
        product_key = get_product_key(
            connection,
            item["product_id"],
        )

        inserted = insert_fact_row(
            connection,
            order_id,
            item["order_item_id"],
            product_key,
            customer_key,
            store_key,
            date_key,
            item["quantity"],
            item["unit_price"],
        )

        if inserted:
            processed_rows += 1
        else:
            skipped_rows += 1

    if processed_rows == 0:
        return "SKIPPED"

    return "PROCESSED"


def load_fact_sales(batch_id):
    connection = get_connection()

    try:
        completed_orders = get_completed_orders(
            connection
        )

        records_received = len(
            completed_orders
        )

        records_processed = 0
        records_quarantined = 0
        records_skipped = 0

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

        for order in completed_orders:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"SAVEPOINT {SAVEPOINT_NAME}"
                    )

                result = process_order(
                    connection,
                    order,
                    batch_id,
                )

                with connection.cursor() as cursor:
                    cursor.execute(
                        f"RELEASE SAVEPOINT "
                        f"{SAVEPOINT_NAME}"
                    )

                if result == "PROCESSED":
                    records_processed += 1

                elif result == "QUARANTINED":
                    records_quarantined += 1

                elif result == "SKIPPED":
                    records_skipped += 1

            except (
                ForeignKeyViolation,
                ValueError,
            ) as error:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"ROLLBACK TO SAVEPOINT "
                        f"{SAVEPOINT_NAME}"
                    )

                order_id = order[0]
                items = get_order_items(
                    connection,
                    order_id,
                )

                formatted_items = []

                for item in items:
                    formatted_items.append(
                        {
                            "order_item_id": item[0],
                            "product_id": item[1],
                            "quantity": item[2],
                            "unit_price": item[3],
                        }
                    )

                quarantine_order(
                    connection,
                    order_id,
                    batch_id,
                    build_raw_order(
                        order,
                        formatted_items,
                    ),
                    str(error),
                    "REFERENCE_ERROR",
                )

                with connection.cursor() as cursor:
                    cursor.execute(
                        f"RELEASE SAVEPOINT "
                        f"{SAVEPOINT_NAME}"
                    )

                records_quarantined += 1

        if (
            records_received
            != records_processed
            + records_quarantined
            + records_skipped
        ):
            raise RuntimeError(
                "Fact batch reconciliation failed: "
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
            f"Completed orders received: "
            f"{records_received}"
        )
        print(
            f"Orders successfully processed: "
            f"{records_processed}"
        )
        print(
            f"Orders quarantined: "
            f"{records_quarantined}"
        )
        print(
            f"Orders skipped: "
            f"{records_skipped}"
        )

    except Exception as error:
        connection.rollback()

        print(
            f"Batch {batch_id} failed."
        )
        print(
            f"Error: {error}"
        )

        raise

    finally:
        connection.close()


if __name__ == "__main__":
    load_fact_sales(
        "FACT-BATCH-001"
    )