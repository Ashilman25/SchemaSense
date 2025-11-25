CREATE SCHEMA IF NOT EXISTS analytics;


CREATE TABLE analytics.page_views (
    id SERIAL PRIMARY KEY,
    page_url TEXT NOT NULL,
    user_id INTEGER,
    view_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE analytics.events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    user_id INTEGER,
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


INSERT INTO analytics.page_views (page_url, user_id) VALUES
    ('/home', 1),
    ('/products', 1),
    ('/home', 2),
    ('/about', 2),
    ('/products', 3);

INSERT INTO analytics.events (event_type, user_id) VALUES
    ('page_view', 1),
    ('add_to_cart', 1),
    ('page_view', 2),
    ('purchase', 3);
