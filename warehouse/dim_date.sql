CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    day_of_week INT NOT NULL,
    week_of_year INT NOT NULL
);