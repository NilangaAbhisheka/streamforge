import csv


def read_customers_from_csv(file_path):
    customers = []

    with open(file_path, mode="r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            customer = {
                "customer_name": row.get("customer_name", "").strip(),
                "email": row.get("email", "").strip(),
            }

            customers.append(customer)

    return customers