# Company Mapping Feature Documentation

## Overview
The Invoice Ninja Integration now includes a Company Mapping feature that allows you to map ERPNext companies to Invoice Ninja companies. This ensures that documents (invoices, quotes, customers, etc.) are properly routed to the correct company on both sides.

## Why Company Mapping is Important
- **Multi-Company Support**: Both ERPNext and Invoice Ninja support multiple companies
- **Data Integrity**: Ensures documents are created in the correct company context
- **Accurate Reporting**: Keeps financial data separated by company
- **Compliance**: Meets requirements for businesses operating multiple entities

## Configuration

### 1. Setting Up Company Mappings
1. Go to **Invoice Ninja Settings**
2. In the **Company Mappings** section, add mappings between:
   - **ERPNext Company**: Select from your ERPNext companies
   - **Invoice Ninja Company ID**: The company ID from Invoice Ninja
   - **Invoice Ninja Company Name**: The display name for reference
   - **Is Default**: Mark one mapping as default for unmapped documents
   - **Enabled**: Enable/disable specific mappings

### 2. Auto-Fetch Invoice Ninja Companies
1. Ensure your Invoice Ninja connection is working (Test Connection = Connected)
2. Click **"Fetch Invoice Ninja Companies"** button
3. Select ERPNext companies to map to each Invoice Ninja company
4. Click **"Add Selected Mappings"** to create the mappings

### 3. Validation
- Click **"Validate Mappings"** to check for:
  - Duplicate mappings
  - Missing default mapping
  - Conflicting configurations

## How It Works

### From Invoice Ninja to ERPNext
When syncing data from Invoice Ninja:
1. The system reads the `company_id` from the Invoice Ninja document
2. Looks up the corresponding ERPNext company in the mapping table
3. Creates/updates the ERPNext document with the correct company

### From ERPNext to Invoice Ninja
When syncing data to Invoice Ninja:
1. The system gets the company from the ERPNext document
2. Looks up the corresponding Invoice Ninja company ID in the mapping table
3. Sends the data to Invoice Ninja with the correct `company_id`

## Field Mapper Updates

### New Functions Added:
- `get_company_mapping()` - Get mapping by ERPNext or Invoice Ninja company
- `get_erpnext_company()` - Get ERPNext company from Invoice Ninja ID
- `get_invoice_ninja_company_id()` - Get Invoice Ninja ID from ERPNext company
- `validate_company_mapping()` - Validate document has proper company mapping

### Updated Mapping Functions:
- `map_customer_from_invoice_ninja()` - Now includes company mapping
- `map_invoice_from_invoice_ninja()` - Now includes company mapping
- `map_quote_from_invoice_ninja()` - Now includes company mapping
- `map_customer_to_invoice_ninja()` - Now includes company mapping
- `map_invoice_to_invoice_ninja()` - Now includes company mapping
- `map_quotation_to_invoice_ninja()` - Now includes company mapping

## Child DocType: Invoice Ninja Company Mapping

### Fields:
- **ERPNext Company** (Link to Company) - Required
- **Invoice Ninja Company ID** (Data) - Required
- **Invoice Ninja Company Name** (Data) - Required
- **Is Default** (Check) - Only one can be default
- **Enabled** (Check) - Enable/disable mapping
- **Description** (Small Text) - Optional notes

### Validation Rules:
- Unique mapping (one-to-one relationship)
- Only one default mapping allowed
- Both ERPNext and Invoice Ninja companies must be unique

## API Endpoints

### `get_invoice_ninja_companies()`
Fetches available companies from Invoice Ninja API for mapping setup.

**Response:**
```json
{
  "success": true,
  "companies": [
    {
      "id": "1",
      "name": "Main Company",
      "settings": {}
    }
  ]
}
```

## Error Handling
- Documents without proper company mapping will fail sync with clear error messages
- Validation prevents duplicate or conflicting mappings
- Fallback to default mapping when specific mapping not found
- Detailed error logging for troubleshooting

## Best Practices
1. **Set up mappings before starting sync** - Prevents sync failures
2. **Use meaningful names** - Makes management easier
3. **Test with small data sets first** - Validate mappings work correctly
4. **Monitor sync logs** - Check for mapping-related errors
5. **Keep mappings updated** - When adding new companies

## Migration Notes
- Existing installations will need to set up company mappings
- Default fallback ensures compatibility during transition
- Custom fields updated to use new field names (invoice_ninja_sync_status vs sync_status)

This feature provides robust multi-company support for the Invoice Ninja integration, ensuring proper data segregation and compliance with business requirements.
