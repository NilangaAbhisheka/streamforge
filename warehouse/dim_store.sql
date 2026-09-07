CREATE TABLE dim_store (
    store_key INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_id INT NOT NULL UNIQUE,
    store_name VARCHAR(255) NOT NULL,
    store_location VARCHAR(255) NOT NULL
);