# Database Initialization Scripts

## init_database.py

Initializes the DuckDB database with sample data matching the schema defined in `metadata/schema.json`.

### Usage

```bash
# Create database with sample data
python scripts/init_database.py

# Reset existing database (delete and recreate)
python scripts/init_database.py --reset

# Specify custom database path
python scripts/init_database.py --db-path ./data/custom.duckdb
```

### What it does

1. **Creates tables** matching `metadata/schema.json`:
   - `categories` - Product categories
   - `users` - User accounts
   - `products` - Product catalog
   - `orders` - Order records

2. **Inserts sample data**:
   - 5 categories (Electronics, Clothing, Books, etc.)
   - 12 products across categories
   - 50 users from 10 different countries
   - 150+ orders distributed across last 6 months
   - Realistic status distribution (85% completed, 10% pending, 5% cancelled)

3. **Verifies data**:
   - Counts records in each table
   - Tests metric calculations
   - Shows sample statistics

### Sample Data Characteristics

- **Time distribution**: Orders spread across last 6 months for time-based queries
- **Geographic diversity**: Users from 10 countries (US, GB, CA, AU, DE, FR, JP, SG, VN, IN)
- **Status distribution**: Realistic order statuses for testing filters
- **Price variation**: Products with different price points
- **Relationships**: All foreign keys properly linked

### Requirements

- DuckDB installed (`pip install duckdb`)
- Python 3.9+

### Output

The script will:
- Create `data/sample.duckdb` (or specified path)
- Print progress for each step
- Show verification statistics
- Display sample queries results

Example output:
```
============================================================
DataPilot Database Initialization
============================================================
Creating database: data/sample.duckdb

Creating tables...
✓ Created table: categories
✓ Created table: users
✓ Created table: products
✓ Created table: orders

Inserting sample data...
✓ Inserted 5 categories
✓ Inserted 12 products
✓ Inserted 50 users
✓ Inserted 156 orders
✓ Updated user purchase status

Verifying data...
✓ categories: 5 records
✓ users: 50 records
✓ products: 12 records
✓ orders: 156 records

Testing metrics...
✓ Total revenue (completed): $XX,XXX.XX
✓ Completed orders: XXX

Top 5 countries by revenue:
  US: $X,XXX.XX
  GB: $X,XXX.XX
  ...

============================================================
✓ Database initialization completed successfully!
✓ Database location: /path/to/data/sample.duckdb
============================================================
```

