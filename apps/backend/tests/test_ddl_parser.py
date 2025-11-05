"""
Comprehensive tests for DDL parsing and schema graph utilities.

Includes test cases with junction tables, compound keys, and various constraints.
"""
import pytest

from app.schemas.schema import CanonicalSchema
from app.utils.ddl_parser import parse_ddl, validate_schema
from app.utils.schema_graph import (
    build_dag,
    compute_table_levels,
    detect_cycles,
    find_junction_tables,
    get_generation_order,
    get_leaf_tables,
    get_root_tables,
    get_table_dependencies,
    get_table_dependents,
    topological_sort,
)


# Sample DDL with comprehensive features
SAMPLE_DDL_POSTGRES = """
-- E-commerce database schema with junction tables and compound keys

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_category_id INTEGER,
    CONSTRAINT fk_parent_category FOREIGN KEY (parent_category_id) 
        REFERENCES categories(category_id)
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL CHECK (price > 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    category_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) 
        REFERENCES categories(category_id)
);

CREATE TABLE addresses (
    address_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    street VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'USA',
    is_primary BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_address_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    shipping_address_id INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    CONSTRAINT fk_order_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id),
    CONSTRAINT fk_order_address FOREIGN KEY (shipping_address_id) 
        REFERENCES addresses(address_id),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled'))
);

CREATE TABLE order_items (
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id),
    CONSTRAINT fk_order_item_order FOREIGN KEY (order_id) 
        REFERENCES orders(order_id) ON DELETE CASCADE,
    CONSTRAINT fk_order_item_product FOREIGN KEY (product_id) 
        REFERENCES products(product_id)
);

CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Junction table with compound key
CREATE TABLE product_tags (
    product_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, tag_id),
    CONSTRAINT fk_product_tag_product FOREIGN KEY (product_id) 
        REFERENCES products(product_id) ON DELETE CASCADE,
    CONSTRAINT fk_product_tag_tag FOREIGN KEY (tag_id) 
        REFERENCES tags(tag_id) ON DELETE CASCADE
);

CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_review_product FOREIGN KEY (product_id) 
        REFERENCES products(product_id) ON DELETE CASCADE,
    CONSTRAINT fk_review_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_user_product_review UNIQUE (user_id, product_id)
);
"""


SAMPLE_DDL_MYSQL = """
-- MySQL syntax variant
CREATE TABLE departments (
    dept_id INT AUTO_INCREMENT PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL UNIQUE,
    manager_id INT NULL
);

CREATE TABLE employees (
    emp_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    dept_id INT NOT NULL,
    salary DECIMAL(10, 2) CHECK (salary > 0),
    hire_date DATE NOT NULL,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

ALTER TABLE departments 
ADD CONSTRAINT fk_dept_manager 
FOREIGN KEY (manager_id) REFERENCES employees(emp_id);
"""


def test_parse_postgres_ddl():
    """Test parsing PostgreSQL DDL with various features."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    # Check that tables were parsed
    assert len(schema.tables) == 9
    table_names = {t.name for t in schema.tables}
    assert "users" in table_names
    assert "products" in table_names
    assert "order_items" in table_names
    assert "product_tags" in table_names
    
    # Check users table
    users_table = next(t for t in schema.tables if t.name == "users")
    assert len(users_table.columns) == 6
    assert users_table.pk == ["user_id"]
    
    # Check email column has PII tag
    email_col = next(c for c in users_table.columns if c.name == "email")
    assert email_col.pii_tag == "EMAIL"
    assert email_col.nullable is False
    
    # Check products table with constraints
    products_table = next(t for t in schema.tables if t.name == "products")
    assert len(products_table.checks) >= 2  # price > 0, stock_quantity >= 0
    assert len(products_table.fks) == 1
    assert products_table.fks[0].to_table == "categories"
    
    # Check order_items junction table with compound key
    order_items = next(t for t in schema.tables if t.name == "order_items")
    assert set(order_items.pk) == {"order_id", "product_id"}
    assert len(order_items.fks) == 2
    
    # Check DAG was built
    assert len(schema.dag.nodes) == 9
    assert len(schema.dag.edges) > 0


def test_parse_mysql_ddl():
    """Test parsing MySQL DDL with ALTER TABLE."""
    schema = parse_ddl(SAMPLE_DDL_MYSQL, dialect="mysql")
    
    # Check tables
    assert len(schema.tables) == 2
    table_names = {t.name for t in schema.tables}
    assert "departments" in table_names
    assert "employees" in table_names
    
    # Check that ALTER TABLE FK was captured
    departments = next(t for t in schema.tables if t.name == "departments")
    # The ALTER TABLE should add the FK
    assert len(departments.fks) >= 1 or "manager_id" in departments.pk


def test_compound_primary_keys():
    """Test parsing tables with compound primary keys."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    # Check order_items has compound PK
    order_items = next(t for t in schema.tables if t.name == "order_items")
    assert len(order_items.pk) == 2
    assert "order_id" in order_items.pk
    assert "product_id" in order_items.pk


def test_check_constraints():
    """Test parsing CHECK constraints."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    products = next(t for t in schema.tables if t.name == "products")
    assert len(products.checks) >= 2
    
    orders = next(t for t in schema.tables if t.name == "orders")
    # Should have status check constraint
    assert any("status" in check.expression.lower() for check in orders.checks)


def test_unique_constraints():
    """Test parsing UNIQUE constraints."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    users = next(t for t in schema.tables if t.name == "users")
    # Email should have unique constraint
    assert len(users.uniques) >= 1
    
    reviews = next(t for t in schema.tables if t.name == "reviews")
    # Should have compound unique on (user_id, product_id)
    assert any(len(uq) == 2 for uq in reviews.uniques)


def test_foreign_keys():
    """Test parsing foreign key relationships."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    orders = next(t for t in schema.tables if t.name == "orders")
    assert len(orders.fks) == 2
    
    fk_targets = {fk.to_table for fk in orders.fks}
    assert "users" in fk_targets
    assert "addresses" in fk_targets


def test_self_referential_fk():
    """Test self-referential foreign keys."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    categories = next(t for t in schema.tables if t.name == "categories")
    # Should have FK to itself
    self_fks = [fk for fk in categories.fks if fk.to_table == "categories"]
    assert len(self_fks) == 1


def test_pii_detection():
    """Test PII tag detection."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    users = next(t for t in schema.tables if t.name == "users")
    
    # Check various PII tags
    email = next(c for c in users.columns if c.name == "email")
    assert email.pii_tag == "EMAIL"
    
    first_name = next(c for c in users.columns if c.name == "first_name")
    assert first_name.pii_tag == "NAME"
    
    phone = next(c for c in users.columns if c.name == "phone")
    assert phone.pii_tag == "PHONE"
    
    addresses = next(t for t in schema.tables if t.name == "addresses")
    city = next(c for c in addresses.columns if c.name == "city")
    assert city.pii_tag == "ADDRESS"


def test_build_dag():
    """Test DAG construction from foreign keys."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    dag = build_dag(schema.tables)
    
    assert len(dag.nodes) == 9
    assert len(dag.edges) > 0
    
    # Check that orders -> users edge exists
    assert ["orders", "users"] in dag.edges


def test_topological_sort():
    """Test topological sorting of tables."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    sorted_tables, is_valid = topological_sort(schema.dag)
    
    assert is_valid  # Should have no cycles
    assert len(sorted_tables) == 9
    
    # Users should come before orders
    users_idx = sorted_tables.index("users")
    orders_idx = sorted_tables.index("orders")
    assert users_idx < orders_idx
    
    # Categories should come before products
    categories_idx = sorted_tables.index("categories")
    products_idx = sorted_tables.index("products")
    assert categories_idx < products_idx


def test_detect_cycles():
    """Test cycle detection in DAG."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    cycles = detect_cycles(schema.dag)
    
    # This schema should have no cycles (except self-referential categories)
    # Self-referential is not a cycle in topological sort context
    assert len(cycles) == 0


def test_find_junction_tables():
    """Test identification of junction tables."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    junction_tables = find_junction_tables(schema.tables)
    
    # Should identify order_items and product_tags as junction tables
    assert "order_items" in junction_tables
    assert "product_tags" in junction_tables
    
    # Regular tables should not be identified as junction tables
    assert "users" not in junction_tables
    assert "products" not in junction_tables


def test_get_root_tables():
    """Test finding tables with no dependencies."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    root_tables = get_root_tables(schema.dag)
    
    # Users and tags should be root tables (no FKs)
    assert "users" in root_tables
    assert "tags" in root_tables


def test_get_leaf_tables():
    """Test finding tables with no dependents."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    leaf_tables = get_leaf_tables(schema.dag)
    
    # Tables like reviews, order_items should be leaf tables
    assert len(leaf_tables) > 0


def test_table_dependencies():
    """Test getting direct dependencies of a table."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    orders_deps = get_table_dependencies("orders", schema.dag)
    assert "users" in orders_deps
    assert "addresses" in orders_deps


def test_table_dependents():
    """Test getting direct dependents of a table."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    users_dependents = get_table_dependents("users", schema.dag)
    assert "orders" in users_dependents
    assert "addresses" in users_dependents
    assert "reviews" in users_dependents


def test_compute_table_levels():
    """Test computing dependency levels."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    levels = compute_table_levels(schema.dag)
    
    # Root tables should be level 0
    assert levels["users"] == 0
    assert levels["tags"] == 0
    
    # Products depends on categories, so higher level
    assert levels["products"] > levels["categories"]
    
    # Orders depends on users and addresses
    assert levels["orders"] > levels["users"]


def test_generation_order():
    """Test getting tables grouped by dependency level."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    groups = get_generation_order(schema.dag)
    
    # Should have multiple groups
    assert len(groups) > 0
    
    # First group should contain root tables
    first_group = groups[0]
    assert "users" in first_group or "tags" in first_group


def test_validate_schema():
    """Test schema validation."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    warnings = validate_schema(schema)
    
    # Should have minimal warnings for valid schema
    # (may have warnings about self-referential FK)
    assert isinstance(warnings, list)


def test_data_type_normalization():
    """Test that data types are normalized correctly."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    users = next(t for t in schema.tables if t.name == "users")
    
    # Check various data types
    user_id = next(c for c in users.columns if c.name == "user_id")
    assert user_id.dtype in ["INTEGER", "SERIAL", "BIGINT"]
    
    email = next(c for c in users.columns if c.name == "email")
    assert "VARCHAR" in email.dtype
    
    products = next(t for t in schema.tables if t.name == "products")
    price = next(c for c in products.columns if c.name == "price")
    assert "DECIMAL" in price.dtype


def test_nullable_columns():
    """Test nullable column detection."""
    schema = parse_ddl(SAMPLE_DDL_POSTGRES, dialect="postgres")
    
    users = next(t for t in schema.tables if t.name == "users")
    
    # email is NOT NULL
    email = next(c for c in users.columns if c.name == "email")
    assert email.nullable is False
    
    # phone is nullable
    phone = next(c for c in users.columns if c.name == "phone")
    assert phone.nullable is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
