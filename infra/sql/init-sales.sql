CREATE SCHEMA IF NOT EXISTS sales;


CREATE TABLE IF NOT EXISTS sales.customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL
);


CREATE TABLE IF NOT EXISTS sales.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100)
);


CREATE TABLE IF NOT EXISTS sales.orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES sales.customers(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2)
);


CREATE TABLE IF NOT EXISTS sales.order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES sales.orders(id),
    product_id INTEGER NOT NULL REFERENCES sales.products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);


INSERT INTO sales.customers (first_name, last_name, email) VALUES
    ('John', 'Doe', 'john@example.com'),
    ('Jane', 'Smith', 'jane@example.com'),
    ('Bob', 'Johnson', 'bob@example.com')
ON CONFLICT (email) DO NOTHING;

INSERT INTO sales.products (name, price, category) VALUES
    ('Laptop', 999.99, 'Electronics'),
    ('Mouse', 29.99, 'Electronics'),
    ('Desk', 299.99, 'Furniture'),
    ('Chair', 199.99, 'Furniture'),
    ('Monitor', 399.99, 'Electronics');

INSERT INTO sales.orders (customer_id, total_amount) VALUES
    (1, 1029.98),
    (2, 399.99),
    (3, 499.98);

INSERT INTO sales.order_items (order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 1, 999.99),
    (1, 2, 1, 29.99),
    (2, 5, 1, 399.99),
    (3, 3, 1, 299.99),
    (3, 4, 1, 199.99);
