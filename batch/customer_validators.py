import re


def validate_customer(customer):
    errors = []

    if not customer.get("customer_name"):
        errors.append("customer_name is missing")

    email = customer.get("email")

    if email:
        email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

        if not re.match(email_pattern, email):
            errors.append("email is malformed")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }

if __name__ == "__main__":
    test_customers = [
        {
            "customer_name": "Amal Perera",
            "email": "amal@example.com",
        },
        {
            "customer_name": "",
            "email": "test@example.com",
        },
        {
            "customer_name": "Sarah Fernando",
            "email": "not-an-email",
        },
        {
            "customer_name": "",
            "email": "not-an-email",
        },
    ]

    for customer in test_customers:
        print(customer)
        print(validate_customer(customer))
        print()