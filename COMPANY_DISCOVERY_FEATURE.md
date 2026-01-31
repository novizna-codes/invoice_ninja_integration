# Company Discovery Feature - Implementation Summary

## Overview

Implemented an easy company discovery workflow that separates **discovery credentials** from **operation credentials**, making it simple for users to set up multi-company Invoice Ninja integration.

## Problem Solved

Previously, users had to manually create Invoice Ninja Company documents without knowing what companies existed in their Invoice Ninja instance. This required:
- Manually looking up company IDs in Invoice Ninja
- Creating docs one by one
- Risk of typos and configuration errors

## Solution

### Two-Phase Credential Model

#### Phase 1: Discovery (Master Credentials)
- **Location**: Invoice Ninja Settings
- **Purpose**: Discover available companies
- **Permissions**: Read-only access to `/api/v1/companies`
- **Usage**: One-time or occasional use

#### Phase 2: Operations (Per-Company Tokens)
- **Location**: Invoice Ninja Company docs
- **Purpose**: All sync operations (CRUD)
- **Permissions**: Full access to specific company data
- **Usage**: Continuous use for sync

## Implementation Details

### 1. DocType Changes

#### Invoice Ninja Settings
**Added Fields:**
```json
{
  "fieldname": "invoice_ninja_url",
  "fieldtype": "Data",
  "label": "Invoice Ninja URL",
  "description": "Master Invoice Ninja instance URL (e.g., https://invoicing.example.com)"
},
{
  "fieldname": "api_token",
  "fieldtype": "Password",
  "label": "API Token",
  "description": "Master API token with access to list companies"
}
```

**Section Renamed:**
- From: "Connection Status"
- To: "Master Connection (For Discovery)"

#### Invoice Ninja Company
**No changes needed** - already has per-company credentials

### 2. API Changes

#### New Method: `fetch_and_create_invoice_ninja_companies()`
```python
@frappe.whitelist()
def fetch_and_create_invoice_ninja_companies():
    """
    Fetch companies from Invoice Ninja using master credentials
    and create/update Invoice Ninja Company docs
    """
    # 1. Get master credentials from Settings
    # 2. Call /api/v1/companies
    # 3. For each company:
    #    - Create or update Invoice Ninja Company doc
    #    - Set company_id, company_name, URL
    #    - Leave api_token blank (security)
    #    - Set enabled=0 (disabled until token set)
    # 4. Return summary
```

**Returns:**
```json
{
  "success": true,
  "message": "Created 2, Updated 1 companies",
  "companies_created": 2,
  "companies_updated": 1,
  "companies": [
    {
      "company_id": "1",
      "company_name": "Company A",
      "doc_name": "IN-COM-Company A-000001",
      "has_token": false
    }
  ]
}
```

#### Legacy Method: `get_invoice_ninja_companies()`
Now redirects to `fetch_and_create_invoice_ninja_companies()` for backward compatibility.

### 3. Client Validation

#### InvoiceNinjaClient.__init__()
Added token validation:
```python
if invoice_ninja_company:
    company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company)

    # Validate enabled
    if not company_doc.enabled:
        frappe.throw(f"Invoice Ninja Company {invoice_ninja_company} is disabled")

    # Validate token exists
    self.token = company_doc.get_password("api_token")
    if not self.token:
        frappe.throw(
            f"No API token configured for Invoice Ninja Company '{company_doc.company_name}'. "
            "Please set the token before syncing.",
            title="Token Required"
        )
```

### 4. UI Enhancements

#### Invoice Ninja Settings Form
**Enhanced "Fetch Companies" button:**
```javascript
function fetch_invoice_ninja_companies(frm) {
    // 1. Validate master credentials exist
    if (!frm.doc.invoice_ninja_url || !frm.doc.api_token) {
        frappe.msgprint({
            title: __('Master Credentials Required'),
            indicator: 'red',
            message: __('Please enter master Invoice Ninja URL and API Token first.')
        });
        return;
    }

    // 2. Call API with loading indicator
    frappe.call({
        method: 'invoice_ninja_integration.api.fetch_and_create_invoice_ninja_companies',
        freeze: true,
        freeze_message: __('Fetching companies from Invoice Ninja...'),
        callback: function(r) {
            // 3. Show results
            // 4. Alert about companies needing tokens
        }
    });
}
```

#### Invoice Ninja Company Form
**Warning when token missing:**
```javascript
refresh: function(frm) {
    // Show warning if no token
    if (!frm.doc.api_token && !frm.is_new()) {
        frm.dashboard.add_comment(
            __('API Token Required: This company cannot sync until you set an API token.'),
            'red',
            true
        );
    }

    // Only show Test Connection if token exists
    if (!frm.is_new() && frm.doc.api_token) {
        frm.add_custom_button(__('Test Connection'), function() {
            test_connection(frm);
        });
    }
}
```

**Auto-enable on token entry:**
```javascript
api_token: function(frm) {
    // Enable company when token is set
    if (frm.doc.api_token && !frm.doc.enabled) {
        frm.set_value('enabled', 1);
    }
}
```

### 5. Migration Update

Updated `migrate_to_per_company_credentials.py` to:
- Keep global credentials in Settings (don't remove them)
- They become master credentials for discovery
- Added comment explaining the new purpose

## User Workflow

### New Installation
```
1. Go to Invoice Ninja Settings
2. Enter master URL + token
3. Click "Fetch Companies from Invoice Ninja"
   → System creates Invoice Ninja Company docs automatically
4. Go to Invoice Ninja Company list
5. For each company:
   - Open doc
   - Enter API token
   - Test connection
   - Auto-enables
6. Go back to Settings
7. Configure company mappings
8. Start syncing
```

### Existing Installation
```
1. Migration keeps existing credentials in Settings
2. Existing Invoice Ninja Company docs already have tokens
3. Can use "Fetch Companies" to discover new companies
4. Set tokens manually for new companies
```

## Security Benefits

1. **Principle of Least Privilege**
   - Master token only needs read access to companies list
   - Operation tokens have full access to their specific company

2. **Token Isolation**
   - Compromise of master token doesn't expose operation data
   - Compromise of one company token doesn't affect others

3. **Mandatory Validation**
   - System refuses to sync without per-company token
   - Clear error messages guide users

4. **Audit Trail**
   - Each company has its own credentials
   - Easy to track which token was used for what operation

## Benefits

### For Users
- ✅ **Easy Setup**: One click to discover all companies
- ✅ **No Manual Entry**: Company IDs and names auto-populated
- ✅ **Clear Guidance**: System tells you exactly what to do next
- ✅ **Error Prevention**: Can't sync without proper credentials

### For Administrators
- ✅ **Secure**: Separate credentials for discovery vs operations
- ✅ **Flexible**: Can use same token for all or different per company
- ✅ **Auditable**: Clear credential ownership per company
- ✅ **Maintainable**: Easy to rotate tokens per company

### For Developers
- ✅ **Clean Architecture**: Clear separation of concerns
- ✅ **Reusable Pattern**: Can apply to other integrations
- ✅ **Testable**: Each phase can be tested independently
- ✅ **Extensible**: Easy to add more discovery features

## Testing Checklist

- [x] Fetch companies with master token
- [x] Verify Invoice Ninja Company docs created automatically
- [x] Confirm tokens are blank on new companies
- [x] Try to sync without token - fails with clear error
- [x] Set token manually - sync works
- [x] Test with multiple companies
- [x] Verify existing installations keep working
- [x] Python syntax validation passed
- [x] JSON syntax validation passed

## Files Modified

1. `doctype/invoice_ninja_settings/invoice_ninja_settings.json` - Added master credential fields
2. `doctype/invoice_ninja_settings/invoice_ninja_settings.js` - Enhanced Fetch Companies button
3. `doctype/invoice_ninja_company/invoice_ninja_company.js` - Added token warnings and auto-enable
4. `api.py` - Added `fetch_and_create_invoice_ninja_companies()`
5. `utils/invoice_ninja_client.py` - Added token validation
6. `patches/migrate_to_per_company_credentials.py` - Updated to keep Settings credentials
7. `MULTI_INSTANCE_IMPLEMENTATION.md` - Added company discovery workflow section
8. `README.md` - Updated setup instructions with discovery workflow

## Documentation

- **User Guide**: See README.md "Basic Setup (v2.0 - Easy Discovery Method)"
- **Architecture**: See MULTI_INSTANCE_IMPLEMENTATION.md "Company Discovery Workflow (v2.0)"
- **Implementation**: See this document

## Version

- **Feature Version**: v2.0
- **Implementation Date**: 2026-02-01
- **Status**: ✅ Complete

