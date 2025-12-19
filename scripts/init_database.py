#!/usr/bin/env python3
"""
Initialize DuckDB database with sample data.

This script creates the database schema and inserts sample data
matching the structure defined in metadata/schema.json.
"""
import sys
from pathlib import Path
import duckdb
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
DB_PATH = Path(__file__).parent.parent / "data" / "sample.duckdb"
SCHEMA_PATH = Path(__file__).parent.parent / "metadata" / "schema.json"


def create_database(db_path: Path, reset: bool = False):
    """
    Create or reset the DuckDB database.
    
    Args:
        db_path: Path to database file
        reset: If True, delete existing database first
    """
    if reset and db_path.exists():
        print(f"Removing existing database: {db_path}")
        db_path.unlink()
    
    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating database: {db_path}")
    conn = duckdb.connect(str(db_path))
    return conn


def create_tables(conn: duckdb.DuckDBPyConnection):
    """Create all tables based on schema.json."""
    print("\nCreating tables...")
    
    # Categories table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        )
    """)
    print("✓ Created table: categories")
    
    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            country VARCHAR(2) NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            has_purchased BOOLEAN DEFAULT FALSE
        )
    """)
    print("✓ Created table: users")
    
    # Products table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category_id INTEGER NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
    """)
    print("✓ Created table: products")
    
    # Orders table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    print("✓ Created table: orders")


def insert_sample_data(conn: duckdb.DuckDBPyConnection):
    """Insert realistic sample data."""
    print("\nInserting sample data...")
    
    # Categories
    categories = [
        (1, 'Electronics'),
        (2, 'Clothing'),
        (3, 'Books'),
        (4, 'Home & Garden'),
        (5, 'Sports & Outdoors')
    ]
    conn.executemany("INSERT INTO categories VALUES (?, ?)", categories)
    print(f"✓ Inserted {len(categories)} categories")
    
    # Products
    products = [
        (1, 'Laptop Pro', 1, 1299.99),
        (2, 'Wireless Mouse', 1, 29.99),
        (3, 'Smartphone', 1, 799.99),
        (4, 'T-Shirt', 2, 19.99),
        (5, 'Jeans', 2, 49.99),
        (6, 'Winter Jacket', 2, 149.99),
        (7, 'Python Guide', 3, 39.99),
        (8, 'Data Science Book', 3, 49.99),
        (9, 'Garden Tools Set', 4, 79.99),
        (10, 'Coffee Maker', 4, 89.99),
        (11, 'Running Shoes', 5, 99.99),
        (12, 'Yoga Mat', 5, 24.99)
    ]
    conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)
    print(f"✓ Inserted {len(products)} products")
    
    # Users - Generate users from different countries
    countries = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP', 'SG', 'VN', 'IN']
    users = []
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, 51):  # 50 users
        country = random.choice(countries)
        email = f"user{i}@example.com"
        created_at = base_date + timedelta(days=random.randint(0, 365))
        has_purchased = random.choice([True, True, True, False])  # 75% have purchased
        users.append((i, country, email, created_at, has_purchased))
    
    conn.executemany(
        "INSERT INTO users (user_id, country, email, created_at, has_purchased) VALUES (?, ?, ?, ?, ?)",
        users
    )
    print(f"✓ Inserted {len(users)} users")
    
    # Orders - Generate orders across different time periods
    orders = []
    order_id = 1
    base_date = datetime(2024, 1, 1)
    
    # Generate orders for last 6 months
    for month_offset in range(6):
        month_start = base_date + timedelta(days=30 * month_offset)
        
        # Generate 20-40 orders per month
        num_orders = random.randint(20, 40)
        
        for _ in range(num_orders):
            user_id = random.randint(1, 50)
            product_id = random.randint(1, 12)
            
            # Get product price
            product_price = next(p[3] for p in products if p[0] == product_id)
            # Add some variation (discounts, etc.)
            amount = round(product_price * random.uniform(0.8, 1.2), 2)
            
            # 85% completed, 10% pending, 5% cancelled
            status_rand = random.random()
            if status_rand < 0.85:
                status = 'completed'
            elif status_rand < 0.95:
                status = 'pending'
            else:
                status = 'cancelled'
            
            # Random date within the month
            day_offset = random.randint(0, 29)
            created_at = month_start + timedelta(days=day_offset, hours=random.randint(0, 23))
            
            orders.append((order_id, user_id, product_id, amount, status, created_at))
            order_id += 1
    
    conn.executemany(
        "INSERT INTO orders (order_id, user_id, product_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        orders
    )
    print(f"✓ Inserted {len(orders)} orders")
    
    # Update users.has_purchased based on actual orders
    conn.execute("""
        UPDATE users
        SET has_purchased = TRUE
        WHERE user_id IN (
            SELECT DISTINCT user_id FROM orders WHERE status = 'completed'
        )
    """)
    print("✓ Updated user purchase status")


def verify_data(conn: duckdb.DuckDBPyConnection):
    """Verify the inserted data."""
    print("\nVerifying data...")
    
    # Count records
    counts = {
        'categories': conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0],
        'users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'products': conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        'orders': conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
    }
    
    for table, count in counts.items():
        print(f"✓ {table}: {count} records")
    
    # Test metrics
    print("\nTesting metrics...")
    
    # Total revenue (completed orders)
    total_revenue = conn.execute("""
        SELECT SUM(amount) 
        FROM orders 
        WHERE status = 'completed'
    """).fetchone()[0]
    print(f"✓ Total revenue (completed): ${total_revenue:,.2f}")
    
    # Order count
    order_count = conn.execute("""
        SELECT COUNT(*) 
        FROM orders 
        WHERE status = 'completed'
    """).fetchone()[0]
    print(f"✓ Completed orders: {order_count}")
    
    # Revenue by country
    revenue_by_country = conn.execute("""
        SELECT u.country, SUM(o.amount) as revenue
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        WHERE o.status = 'completed'
        GROUP BY u.country
        ORDER BY revenue DESC
        LIMIT 5
    """).fetchall()
    
    print("\nTop 5 countries by revenue:")
    for country, revenue in revenue_by_country:
        print(f"  {country}: ${revenue:,.2f}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize DuckDB database with sample data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing database and recreate"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(DB_PATH),
        help=f"Path to database file (default: {DB_PATH})"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("DataPilot Database Initialization")
    print("=" * 60)
    
    try:
        # Create database
        conn = create_database(Path(args.db_path), reset=args.reset)
        
        # Create tables
        create_tables(conn)
        
        # Insert sample data
        insert_sample_data(conn)
        
        # Verify data
        verify_data(conn)
        
        # Close connection
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Database initialization completed successfully!")
        print(f"✓ Database location: {Path(args.db_path).absolute()}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

