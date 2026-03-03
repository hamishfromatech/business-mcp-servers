# Inventory Manager MCP Server

A FastMCP server for managing inventory, stock, and product tracking.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Category Management

| Tool | Description |
|------|-------------|
| `create_category` | Create a product category |
| `list_categories` | List all categories |

### Location Management

| Tool | Description |
|------|-------------|
| `create_location` | Create a storage location |
| `list_locations` | List all locations |

### Product Management

| Tool | Description |
|------|-------------|
| `create_product` | Create a new product |
| `get_product` | Get product by ID |
| `get_product_by_sku` | Get product by SKU |
| `update_product` | Update product details |
| `delete_product` | Delete a product |
| `list_products` | List products with filters |
| `search_products` | Search products |

### Stock Operations

| Tool | Description |
|------|-------------|
| `stock_in` | Add stock to a product |
| `stock_out` | Remove stock from a product |
| `transfer_stock` | Transfer stock between locations |
| `get_movement_history` | Get inventory movement history |

### Alerts

| Tool | Description |
|------|-------------|
| `get_active_alerts` | Get active low-stock alerts |
| `resolve_alert` | Mark alert as resolved |

### Analytics

| Tool | Description |
|------|-------------|
| `get_inventory_summary` | Get overall inventory statistics |

## Resources

| Resource | Description |
|----------|-------------|
| `inventory://summary` | Inventory summary with counts and values |
| `inventory://low-stock` | Products below threshold |

## Example Usage

```python
# Create category and location
cat = create_category(name="Electronics")
loc = create_location(name="Warehouse A")

# Create a product
product = create_product(
    name="Laptop",
    sku="LAP-001",
    quantity=50,
    price=999.99,
    category_id=1,
    location_id=1,
    low_stock_threshold=10
)

# Add stock
stock_in(product_id=1, quantity=20, notes="New shipment")

# Remove stock
stock_out(product_id=1, quantity=5, notes="Sale #1234")

# Check inventory
summary = get_inventory_summary()
# Returns: total_products, total_quantity, total_value, low_stock_count

# Get low stock alerts
alerts = get_active_alerts()

# Get movement history
history = get_movement_history(product_id=1, limit=50)
```

## Movement Types

- `in` - Stock added
- `out` - Stock removed
- `transfer` - Stock moved between locations

## Storage

This server uses in-memory storage. Data is not persisted between restarts.