CREATE TABLE dim_product (
    product_key INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id INT NOT NULL UNIQUE,
    product_name VARCHAR(255) NOT NULL,
    product_category VARCHAR(255),
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0)
);