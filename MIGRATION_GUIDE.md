# Migration Guide for IN/OUT Quantity Tracking

## Steps to Apply the Changes:

### 1. Stop the Django Server
Press `Ctrl+C` in the terminal where Django is running.

### 2. Run Migrations
Open a terminal in the `krishna_air-backend` folder and run:

```bash
python manage.py migrate
```

This will:
- Add `total_in_quantity` column to InventoryItem table
- Add `total_out_quantity` column to InventoryItem table
- Populate existing data with correct values based on GRN and Material Issue history

### 3. Verify Migration
Check if migrations were successful:

```bash
python manage.py showmigrations inventory
```

You should see:
```
[X] 0017_inventoryitem_total_in_quantity_and_more
[X] 0018_populate_in_out_quantities
```

### 4. Restart Django Server
```bash
python manage.py runserver
```

### 5. Test the Stock Dashboard
1. Go to Inventory Management
2. Click on "Stock" tab
3. You should now see:
   - **In Qty** column (green) - showing total received
   - **Out Qty** column (red) - showing total issued
   - **Current Qty** column (blue) - showing current stock

## What the Migration Does:

### Migration 0017:
- Adds two new fields to InventoryItem:
  - `total_in_quantity` (default: 0)
  - `total_out_quantity` (default: 0)

### Migration 0018 (Data Migration):
For each existing inventory item, it calculates:

**Total IN Quantity:**
- Sum of all completed GRN quantities (received - rejected)
- Plus sum of all completed Material Return quantities

**Total OUT Quantity:**
- Sum of all Material Issue quantities

**Formula:**
```
current_quantity = total_in_quantity - total_out_quantity
```

## Troubleshooting:

### If you get "column already exists" error:
```bash
python manage.py migrate inventory 0016 --fake
python manage.py migrate
```

### If you get "no such column" error:
The migration hasn't been applied yet. Run:
```bash
python manage.py migrate
```

### To check current database state:
```bash
python manage.py dbshell
```
Then run:
```sql
PRAGMA table_info(inventory_inventoryitem);
```
Look for `total_in_quantity` and `total_out_quantity` columns.

## After Migration:

From now on:
- ✅ When you complete a GRN → `total_in_quantity` increases
- ✅ When you create a Material Issue → `total_out_quantity` increases
- ✅ When you complete a Material Return → `total_in_quantity` increases
- ✅ Stock Dashboard shows all three values

## Need Help?

If you encounter any issues, check:
1. Django server logs for error messages
2. Browser console for frontend errors
3. Database has the new columns: `total_in_quantity`, `total_out_quantity`
