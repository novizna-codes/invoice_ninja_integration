# Invoice Ninja Custom Fields Reorganization

## Summary

All Invoice Ninja integration custom fields have been reorganized under dedicated "Invoice Ninja" tabs in each doctype to prevent layout issues and improve UX.

## Problem Solved

Previously, Invoice Ninja fields were scattered throughout ERPNext standard forms:
- Fields inserted after various standard fields (naming_series, customer_name, item_name, etc.)
- Caused layout disruptions
- Made forms cluttered and difficult to navigate
- Mixed integration-specific fields with core business data

## Solution Implemented

Added a dedicated "**Invoice Ninja**" tab to each affected doctype with:
1. **Tab Break** - Creates a new tab labeled "Invoice Ninja"
2. **Section Break** - "Sync Details" section within the tab
3. **All Invoice Ninja fields** organized under this tab

## Doctypes Updated

### 1. ✅ Customer
**Tab added after**: `represents_company`
**Fields moved** (5):
- invoice_ninja_id
- invoice_ninja_company
- invoice_ninja_sync_status
- invoice_ninja_last_sync
- invoice_ninja_sync_hash

### 2. ✅ Sales Invoice
**Tab added after**: `other_details`
**Fields moved** (7):
- invoice_ninja_id
- invoice_ninja_company
- invoice_ninja_sync_status
- invoice_ninja_number
- invoice_ninja_tasks
- invoice_ninja_last_sync
- invoice_ninja_sync_hash

### 3. ✅ Item
**Tab added after**: `hub_publishing_sb`
**Fields moved** (5):
- invoice_ninja_id
- invoice_ninja_company
- invoice_ninja_sync_status
- invoice_ninja_last_sync
- invoice_ninja_sync_hash

### 4. ✅ Quotation
**Tab added after**: `other_information`
**Fields moved** (6):
- invoice_ninja_id
- invoice_ninja_company
- invoice_ninja_sync_status
- invoice_ninja_number
- invoice_ninja_last_sync
- invoice_ninja_sync_hash

### 5. ✅ Payment Entry
**Tab added after**: `deductions_or_loss_section`
**Fields moved** (5):
- invoice_ninja_id
- invoice_ninja_company
- invoice_ninja_sync_status
- invoice_ninja_last_sync
- invoice_ninja_sync_hash

### 6. ✅ Contact
**Tab added after**: `image`
**Fields moved** (2):
- invoice_ninja_contact_id
- invoice_ninja_company

### 7. ✅ File
**Tab added after**: `uploaded_to_dropbox`
**Fields moved** (3):
- invoice_ninja_id
- invoice_ninja_sync_status
- invoice_ninja_last_sync

### 8. ✅ Sales Invoice Item
**Child table - No tab** (fields remain hidden)
**Fields** (2 - defined in custom_fields.py):
- invoice_ninja_task_id (hidden)
- custom_is_task_based (read-only)

## Benefits

✅ **Clean Standard Forms** - ERPNext forms remain uncluttered
✅ **Organized Sync Data** - All Invoice Ninja fields in one dedicated location
✅ **Easy Navigation** - Users know exactly where to find sync information
✅ **Professional UX** - Integration data separated from core business data
✅ **Maintainable** - Easy to add more Invoice Ninja fields in the future
✅ **No Layout Conflicts** - Standard ERPNext layout preserved

## How to Apply Changes

Run bench migrate to apply the updated custom fields:

```bash
bench --site [your-site] migrate
```

This will:
1. Remove old custom field definitions
2. Add new tab breaks and section breaks
3. Recreate all Invoice Ninja fields under the new tabs
4. Maintain all existing data

## Field Visibility

Most fields remain visible in the Invoice Ninja tab, except:
- **Hidden fields**: `invoice_ninja_last_sync`, `invoice_ninja_sync_hash` (metadata)
- **Sales Invoice Item fields**: Both hidden (technical fields for task tracking)
- **List view**: `invoice_ninja_sync_status` and `invoice_ninja_number` still show in list views for quick reference

## Files Modified

```
apps/invoice_ninja_integration/invoice_ninja_integration/invoice_ninja_integration/custom/
├── customer.json          ✅ Reorganized
├── sales_invoice.json     ✅ Reorganized
├── item.json              ✅ Reorganized
├── quotation.json         ✅ Reorganized
├── payment_entry.json     ✅ Reorganized
├── contact.json           ✅ Reorganized
├── file.json              ✅ Reorganized
└── sales_invoice_item.json  (unchanged - child table)
```

## Testing

After migration:
1. Open any Customer/Sales Invoice/Item form
2. Navigate to the "Invoice Ninja" tab
3. Verify all sync fields are present and functional
4. Check that standard ERPNext forms are clean
5. Test synchronization to ensure fields populate correctly

## Rollback (if needed)

If you need to revert:
1. Restore the previous JSON files from git history
2. Run `bench --site [your-site] migrate`
3. Clear cache: `bench --site [your-site] clear-cache`

## Notes

- Tab breaks are standard ERPNext practice for organizing fields
- This change doesn't affect data - only field layout
- Existing synced data remains intact
- Integration functionality is unchanged
- Child doctypes (like Sales Invoice Item) don't support tabs - fields remain inline but hidden
