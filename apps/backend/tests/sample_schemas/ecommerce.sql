-- Comprehensive E-commerce Database Schema
-- Includes junction tables, compound keys, self-referential FKs, and various constraints

-- Users table with PII data
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories with self-referential FK (hierarchical)
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_category_id INTEGER,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_parent_category 
        FOREIGN KEY (parent_category_id) 
        REFERENCES categories(category_id) 
        ON DELETE SET NULL
);

-- Products table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL CHECK (price > 0),
    cost DECIMAL(10, 2) CHECK (cost >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    weight_kg DECIMAL(8, 3) CHECK (weight_kg > 0),
    category_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_category 
        FOREIGN KEY (category_id) 
        REFERENCES categories(category_id)
);

-- Create indexes for products
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_sku ON products(sku);

-- Addresses for users
CREATE TABLE addresses (
    address_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    address_type VARCHAR(20) NOT NULL DEFAULT 'shipping',
    street_line1 VARCHAR(255) NOT NULL,
    street_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'USA',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_address_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE,
    CONSTRAINT chk_address_type 
        CHECK (address_type IN ('shipping', 'billing', 'both'))
);

-- Orders table
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    billing_address_id INTEGER NOT NULL,
    shipping_address_id INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    shipped_date TIMESTAMP,
    delivered_date TIMESTAMP,
    subtotal DECIMAL(12, 2) NOT NULL CHECK (subtotal >= 0),
    tax DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (tax >= 0),
    shipping_cost DECIMAL(10, 2) NOT NULL DEFAULT 0 CHECK (shipping_cost >= 0),
    total_amount DECIMAL(12, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    notes TEXT,
    CONSTRAINT fk_order_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id),
    CONSTRAINT fk_order_billing_address 
        FOREIGN KEY (billing_address_id) 
        REFERENCES addresses(address_id),
    CONSTRAINT fk_order_shipping_address 
        FOREIGN KEY (shipping_address_id) 
        REFERENCES addresses(address_id),
    CONSTRAINT chk_order_status 
        CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'))
);

-- Order items (junction table with compound PK)
CREATE TABLE order_items (
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL,
    discount_percent DECIMAL(5, 2) DEFAULT 0 CHECK (discount_percent >= 0 AND discount_percent <= 100),
    line_total DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id),
    CONSTRAINT fk_order_item_order 
        FOREIGN KEY (order_id) 
        REFERENCES orders(order_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_order_item_product 
        FOREIGN KEY (product_id) 
        REFERENCES products(product_id)
);

-- Tags for products
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7) DEFAULT '#000000'
);

-- Product tags junction table
CREATE TABLE product_tags (
    product_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, tag_id),
    CONSTRAINT fk_product_tag_product 
        FOREIGN KEY (product_id) 
        REFERENCES products(product_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_product_tag_tag 
        FOREIGN KEY (tag_id) 
        REFERENCES tags(tag_id) 
        ON DELETE CASCADE
);

-- Product reviews
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(255),
    comment TEXT,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_review_product 
        FOREIGN KEY (product_id) 
        REFERENCES products(product_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_review_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE,
    CONSTRAINT uq_user_product_review 
        UNIQUE (user_id, product_id)
);

-- Wishlists
CREATE TABLE wishlists (
    wishlist_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL DEFAULT 'My Wishlist',
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_wishlist_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE
);

-- Wishlist items (junction table)
CREATE TABLE wishlist_items (
    wishlist_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority INTEGER DEFAULT 0,
    notes TEXT,
    PRIMARY KEY (wishlist_id, product_id),
    CONSTRAINT fk_wishlist_item_wishlist 
        FOREIGN KEY (wishlist_id) 
        REFERENCES wishlists(wishlist_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_wishlist_item_product 
        FOREIGN KEY (product_id) 
        REFERENCES products(product_id) 
        ON DELETE CASCADE
);

-- Payment methods
CREATE TABLE payment_methods (
    payment_method_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    method_type VARCHAR(20) NOT NULL,
    card_last_four VARCHAR(4),
    card_brand VARCHAR(20),
    expiry_month INTEGER CHECK (expiry_month BETWEEN 1 AND 12),
    expiry_year INTEGER,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_method_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE,
    CONSTRAINT chk_payment_method_type 
        CHECK (method_type IN ('credit_card', 'debit_card', 'paypal', 'bank_transfer'))
);

-- Inventory transactions
CREATE TABLE inventory_transactions (
    transaction_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    reference_id INTEGER,
    reference_type VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    CONSTRAINT fk_inventory_product 
        FOREIGN KEY (product_id) 
        REFERENCES products(product_id),
    CONSTRAINT chk_inventory_transaction_type 
        CHECK (transaction_type IN ('purchase', 'sale', 'return', 'adjustment', 'damage'))
);

-- Promotions
CREATE TABLE promotions (
    promotion_id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL,
    discount_value DECIMAL(10, 2) NOT NULL CHECK (discount_value > 0),
    min_purchase_amount DECIMAL(10, 2) DEFAULT 0,
    max_uses INTEGER,
    uses_count INTEGER DEFAULT 0,
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT chk_promotion_discount_type 
        CHECK (discount_type IN ('percentage', 'fixed_amount')),
    CONSTRAINT chk_promotion_dates 
        CHECK (valid_until > valid_from)
);

-- Promotion products (which products are eligible)
CREATE TABLE promotion_products (
    promotion_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    PRIMARY KEY (promotion_id, product_id),
    CONSTRAINT fk_promotion_product_promotion 
        FOREIGN KEY (promotion_id) 
        REFERENCES promotions(promotion_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_promotion_product_product 
        FOREIGN KEY (product_id) 
        REFERENCES products(product_id) 
        ON DELETE CASCADE
);
