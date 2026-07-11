# Fix IN/OUT Quantities Not Updating

## Problem
IN Qty and OUT Qty columns show 0.00 even after creating GRN, Material Issue, or Material Return.

## Root Cause
The database columns `total_in_quantity` and `total_out_quantity` either:
1. Don't exist yet (migration not run)
2. Exist but have incorrect/zero values

## Solution

### Step 1: Check if Migration Was Applied

Run this command:
```bash
python manage.py showmigrations inventory
```

Look for these migrations:
```
[X] 0017_inventoryitem_total_in_quantity_and_more
[X] 0018_populate_in_out_quantities
```

If they show `[ ]` (not checked), run:
```bash
python manage.py migrate
```

### Step 2: Fix Existing Data

Even if migrations are applied, existing data might have zero values. Run this command to recalculate:

```bash
python manage.py fix_inventory_quantities
```

This will:
- Calculate IN quantities from all completed GRNs and Returns
- Calculate OUT quantities from all Material Issues
- Update all inventory items with correct values
- Show you the changes being made

### Step 3: Verify the Fix

1. Restart Django server
2. Go to Stock Dashboard
3. Refresh the page
4. You should now see correct IN/OUT quantities

## Expected Behavior After Fix

### When you complete a GRN:
- ✅ `total_in_quantity` increases by received quantity
- ✅ `quantity` increases by received quantity
- ✅ Stock Dashboard shows updated IN Qty

### When you create a Material Issue:
- ✅ `total_out_quantity` increases by issued quantity
- ✅ `quantity` decreases by issued quantity
- ✅ Stock Dashboard shows updated OUT Qty

### When you complete a Material Return:
- ✅ `total_in_quantity` increases by returned quantity
- ✅ `quantity` increases by returned quantity
- ✅ Stock Dashboard shows updated IN Qty

## Example

If you:
1. Complete GRN with 10 items
2. Issue 3 items
3. Return 1 item

You should see:
- **IN Qty**: 11.00 (10 from GRN + 1 from return)
- **OUT Qty**: 3.00 (3 issued)
- **Current Qty**: 8.00 (11 - 3)

## Troubleshooting

### Issue: "no such column: total_in_quantity"
**Solution:** Run migrations
```bash
python manage.py migrate
```

### Issue: "Command not found: fix_inventory_quantities"
**Solution:** Make sure the file exists at:
```
krishna_air-backend/inventory/management/commands/fix_inventory_quantities.py
```

Then try again:
```bash
python manage.py fix_inventory_quantities
```

### Issue: Values still showing 0.00 after fix
**Solution:** 
1. Check Django server logs for errors
2. Verify migrations are applied:
   ```bash
   python manage.py showmigrations inventory
   ```
3. Check database directly:
   ```bash
   python manage.py dbshell
   ```
   Then:
   ```sql
   SELECT id, quantity, total_in_quantity, total_out_quantity 
   FROM inventory_inventoryitem 
   LIMIT 5;
   ```

### Issue: Frontend still shows 0.00
**Solution:**
1. Clear browser cache (Ctrl+Shift+R)
2. Check browser console for errors
3. Verify API response in Network tab
4. Restart Django server

## Quick Fix Command

Run all steps at once:
```bash
python manage.py migrate && python manage.py fix_inventory_quantities
```

Then restart Django server.

## Need More Help?

Check:
1. Django server terminal for error messages
2. Browser console (F12) for frontend errors
3. Database has the columns with correct data
4. API response includes `total_in_quantity` and `total_out_quantity` fields
