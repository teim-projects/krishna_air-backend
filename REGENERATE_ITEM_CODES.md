# Regenerate Item Codes with Shortcuts

## Problem
The Purchase Order PDF was showing item codes generated with the old logic (taking first 2 letters of each word) instead of using the new shortcut fields that were added to the database.

## Solution
A management command has been created to regenerate all item codes using the shortcut fields.

## How to Use

### Step 1: Preview Changes (Dry Run)
First, run the command in dry-run mode to see what will change without actually updating the database:

```bash
cd krishna_air-backend
python manage.py regenerate_item_codes --dry-run
```

This will show you:
- Which item codes will be changed
- Old code → New code
- Total number of items that will be updated

### Step 2: Apply Changes
Once you've reviewed the changes and are satisfied, run the command without the `--dry-run` flag:

```bash
python manage.py regenerate_item_codes
```

This will:
1. Loop through all items in the database
2. Regenerate their `item_code` using the shortcut fields (if available)
3. Handle duplicates by appending a number suffix (e.g., `MT-IT-1`, `MT-IT-2`)
4. Update the database with the new codes

### Step 3: Verify in PO PDF
After running the command:
1. Create a new Purchase Order or view an existing one
2. Generate the PDF
3. Check that the item codes now use the shortcuts you defined

## Example

**Before (Old Logic):**
- Material Type: "Copper Pipe" → Code: "CO" (first 2 letters)
- Item Type: "Insulation" → Code: "IN" (first 2 letters)
- Result: `CO-IN-15MM`

**After (With Shortcuts):**
- Material Type: "Copper Pipe" with shortcut "CP" → Code: "CP"
- Item Type: "Insulation" with shortcut "INS" → Code: "INS"
- Result: `CP-INS-15MM`

## Important Notes

1. **Backup First**: It's recommended to backup your database before running this command
2. **Existing POs**: Existing Purchase Orders will automatically show the new codes since they reference the item by ID, not by the code string
3. **Shortcuts Required**: Make sure you've added shortcuts to all material_type, item_type, feature_type, and item_class records before running this command
4. **Duplicates**: The command automatically handles duplicate codes by appending a number

## Troubleshooting

If you see many unchanged items, it means:
- The shortcuts are already being used correctly, OR
- No shortcuts have been defined (the command falls back to the old logic)

To add shortcuts:
1. Go to Django Admin or your frontend
2. Edit material_type, item_type, feature_type, and item_class records
3. Add appropriate shortcuts (e.g., "CP" for Copper Pipe, "INS" for Insulation)
4. Run the regenerate command again
