CREATE TABLE dim_customer (
    customer_key INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id INT UNIQUE,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255)
);