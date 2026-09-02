from pathlib import Path

from connection import get_connection
from readers import read_customers_from_csv
from validators import validate_customer
from psycopg.types.json import Jsonb
from psycopg.errors import UniqueViolation


CSV_FILE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "customers.csv"
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


def start_batch(connection, batch_id, records_received):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pipeline_batches (
                batch_id,
                pipeline_name,
                status,
                records_received
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                batch_id,
                "customer_batch",
                "STARTED",
                records_received,
            ),
        )


def complete_batch(
    connection,
    batch_id,
    records_processed,
    records_quarantined,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pipeline_batches
            SET
                completed_at = CURRENT_TIMESTAMP,
                status = 'COMPLETED',
                records_processed = %s,
                records_quarantined = %s
            WHERE batch_id = %s
            """,
            (
                records_processed,
                records_quarantined,
                batch_id,
            ),
        )


def load_valid_customer(connection, customer):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO customers (
                customer_name,
                email
            )
            VALUES (%s, %s)
            """,
            (
                customer["customer_name"],
                customer["email"],
            ),
        )


def quarantine_record(
    connection,
    record,
    failure_reason,
    failure_type,
    batch_id,
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
            """,
            (
                "customer_batch",
                None,
                Jsonb(record),
                failure_reason,
                failure_type,
                batch_id,
            ),
        )


def process_customer_with_isolation(
    connection,
    customer,
    batch_id,
):
    savepoint_name = "customer_insert"

    with connection.cursor() as cursor:
        cursor.execute(
            f"SAVEPOINT {savepoint_name}"
        )

    try:
        load_valid_customer(
            connection,
            customer,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"RELEASE SAVEPOINT {savepoint_name}"
            )

        return True

    except UniqueViolation:
        with connection.cursor() as cursor:
            cursor.execute(
                f"ROLLBACK TO SAVEPOINT {savepoint_name}"
            )

        failure_reason = (
            f"email already exists: {customer['email']}"
        )

        quarantine_record(
            connection,
            customer,
            failure_reason,
            "DUPLICATE_RECORD",
            batch_id,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"RELEASE SAVEPOINT {savepoint_name}"
            )

        return False


def load_customers(customers, batch_id):
    connection = get_connection()

    try:
        if batch_already_completed(connection, batch_id):
            print(
                f"Batch {batch_id} already completed. Skipping."
            )
            return

        records_received = len(customers)

        valid_customers = []
        invalid_customers = []

        for customer in customers:
            validation_result = validate_customer(customer)

            if validation_result["valid"]:
                valid_customers.append(customer)
            else:
                invalid_customers.append(
                    {
                        "record": customer,
                        "errors": validation_result["errors"],
                    }
                )

        print(f"Records received: {records_received}")
        print(f"Valid records: {len(valid_customers)}")
        print(f"Invalid records: {len(invalid_customers)}")

        with connection:
            start_batch(
                connection,
                batch_id,
                records_received,
            )

            for item in invalid_customers:
                quarantine_record(
                    connection,
                    item["record"],
                    "; ".join(item["errors"]),
                    "VALIDATION_ERROR",
                    batch_id,
                )

            records_processed = 0
            database_quarantined = 0

            for customer in valid_customers:
                inserted = process_customer_with_isolation(
                    connection,
                    customer,
                    batch_id,
                )

                if inserted:
                    records_processed += 1
                else:
                    database_quarantined += 1

            records_quarantined = (
                len(invalid_customers)
                + database_quarantined
            )

            complete_batch(
                connection,
                batch_id,
                records_processed,
                records_quarantined,
            )

        print(
            f"Batch {batch_id} completed successfully."
        )
        print(
            f"Records received: {records_received}"
        )
        print(
            f"Records successfully processed: "
            f"{records_processed}"
        )
        print(
            f"Records quarantined: "
            f"{records_quarantined}"
        )

    except Exception as error:
        print(f"Batch {batch_id} failed.")
        print(f"Error: {error}")
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    customers = read_customers_from_csv(
        CSV_FILE_PATH
    )

    load_customers(
        customers,
        "BATCH-009",
    )