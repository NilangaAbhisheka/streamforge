CREATE TABLE fact_sales (
    sales_key INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id INT NOT NULL,
    product_key INT NOT NULL,
    customer_key INT NOT NULL,
    store_key INT NOT NULL,
    date_key INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),
    sales_amount DECIMAL(10,2) NOT NULL CHECK (sales_amount >= 0),

    CONSTRAINT fact_sales_product_fk
        FOREIGN KEY (product_key)
        REFERENCES dim_product(product_key),

    CONSTRAINT fact_sales_customer_fk
        FOREIGN KEY (customer_key)
        REFERENCES dim_customer(customer_key),

    CONSTRAINT fact_sales_store_fk
        FOREIGN KEY (store_key)
        REFERENCES dim_store(store_key),

    CONSTRAINT fact_sales_date_fk
        FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key),

    CONSTRAINT fact_sales_amount_check
        CHECK (sales_amount = quantity * unit_price)
);