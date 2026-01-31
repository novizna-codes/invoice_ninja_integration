# Customer Fetch API Documentation

## Overview
The Invoice Ninja Integration app provides API endpoints to fetch customers from Invoice Ninja for all mapped companies or for a specific company. These endpoints use the centralized `SyncManager` service, which provides a consistent interface for all entity types.

## Architecture Note
All fetch operations now use the centralized `SyncManager` service (which extends `BaseIntegrationService`). This ensures:
- Consistent behavior across all entity types
- Single source of truth for data operations
- Easy maintenance and extensibility
- Reusable patterns for other integration apps

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## Prerequisites
1. Invoice Ninja Settings must be properly configured
2. Company mappings must be set up (ERPNext Company → Invoice Ninja Company)
3. Integration must be enabled

## API Endpoints

### 1. Get Customers for All Mapped Companies

Fetches customers from Invoice Ninja for all companies that are mapped in the settings.

**Endpoint:** `invoice_ninja_integration.api.get_customers_for_mapped_companies`

**Method:** `@frappe.whitelist()`

**Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of customers per page (default: 100)

**Response:**
```json
{
  "success": true,
  "companies": [
    {
      "erpnext_company": "Company A",
      "invoice_ninja_company_id": "1",
      "invoice_ninja_company_name": "Main Company",
      "customers": [...],
      "customer_count": 25,
      "is_default": true
    },
    {
      "erpnext_company": "Company B",
      "invoice_ninja_company_id": "2",
      "invoice_ninja_company_name": "Secondary Company",
      "customers": [...],
      "customer_count": 15,
      "is_default": false
    }
  ],
  "total_customers": 40,
  "message": "Successfully fetched customers from 2 mapped companies"
}
```

**Example Usage:**

**Python (Server-side):**
```python
import frappe

# Get customers for all mapped companies
result = frappe.call(
    "invoice_ninja_integration.api.get_customers_for_mapped_companies",
    page=1,
    per_page=100
)

if result.get("success"):
    for company_data in result["companies"]:
        print(f"\nCompany: {company_data['invoice_ninja_company_name']}")
        print(f"Customer Count: {company_data['customer_count']}")

        for customer in company_data["customers"]:
            print(f"  - {customer.get('name')} (ID: {customer.get('id')})")
else:
    print(f"Error: {result.get('message')}")
```

**JavaScript (Client-side):**
```javascript
frappe.call({
    method: "invoice_ninja_integration.api.get_customers_for_mapped_companies",
    args: {
        page: 1,
        per_page: 100
    },
    callback: function(r) {
        if (r.message && r.message.success) {
            console.log("Total Customers:", r.message.total_customers);

            r.message.companies.forEach(company => {
                console.log(`\nCompany: ${company.invoice_ninja_company_name}`);
                console.log(`Customer Count: ${company.customer_count}`);

                company.customers.forEach(customer => {
                    console.log(`  - ${customer.name} (ID: ${customer.id})`);
                });
            });
        } else {
            frappe.msgprint(r.message.message || "Failed to fetch customers");
        }
    }
});
```

**cURL (REST API):**
```bash
curl -X POST "http://your-site.local/api/method/invoice_ninja_integration.api.get_customers_for_mapped_companies" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "per_page": 100
  }'
```

---

### 2. Get Customers for a Specific Company

Fetches customers from Invoice Ninja for a single company identified by either ERPNext company name or Invoice Ninja company ID.

**Endpoint:** `invoice_ninja_integration.api.get_customers_for_company`

**Method:** `@frappe.whitelist()`

**Parameters:**
- `erpnext_company` (optional): ERPNext company name
- `invoice_ninja_company_id` (optional): Invoice Ninja company ID
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of customers per page (default: 100)

**Note:** You must provide either `erpnext_company` OR `invoice_ninja_company_id`.

**Response:**
```json
{
  "success": true,
  "erpnext_company": "Company A",
  "invoice_ninja_company_id": "1",
  "invoice_ninja_company_name": "Main Company",
  "customers": [...],
  "customer_count": 25,
  "message": "Successfully fetched 25 customers for Main Company"
}
```

**Example Usage:**

**Python (Server-side):**
```python
import frappe

# Get customers for a specific ERPNext company
result = frappe.call(
    "invoice_ninja_integration.api.get_customers_for_company",
    erpnext_company="Company A",
    page=1,
    per_page=50
)

# OR get customers for a specific Invoice Ninja company ID
result = frappe.call(
    "invoice_ninja_integration.api.get_customers_for_company",
    invoice_ninja_company_id="1",
    page=1,
    per_page=50
)

if result.get("success"):
    print(f"Company: {result['invoice_ninja_company_name']}")
    print(f"Customer Count: {result['customer_count']}")

    for customer in result["customers"]:
        print(f"  - {customer.get('name')} (ID: {customer.get('id')})")
else:
    print(f"Error: {result.get('message')}")
```

**JavaScript (Client-side):**
```javascript
// Using ERPNext company name
frappe.call({
    method: "invoice_ninja_integration.api.get_customers_for_company",
    args: {
        erpnext_company: "Company A",
        page: 1,
        per_page: 50
    },
    callback: function(r) {
        if (r.message && r.message.success) {
            console.log("Company:", r.message.invoice_ninja_company_name);
            console.log("Customer Count:", r.message.customer_count);

            r.message.customers.forEach(customer => {
                console.log(`  - ${customer.name} (ID: ${customer.id})`);
            });
        } else {
            frappe.msgprint(r.message.message || "Failed to fetch customers");
        }
    }
});

// OR using Invoice Ninja company ID
frappe.call({
    method: "invoice_ninja_integration.api.get_customers_for_company",
    args: {
        invoice_ninja_company_id: "1",
        page: 1,
        per_page: 50
    },
    callback: function(r) {
        // Same callback handling as above
    }
});
```

**cURL (REST API):**
```bash
# Using ERPNext company name
curl -X POST "http://your-site.local/api/method/invoice_ninja_integration.api.get_customers_for_company" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "erpnext_company": "Company A",
    "page": 1,
    "per_page": 50
  }'

# OR using Invoice Ninja company ID
curl -X POST "http://your-site.local/api/method/invoice_ninja_integration.api.get_customers_for_company" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_ninja_company_id": "1",
    "page": 1,
    "per_page": 50
  }'
```

---

## Customer Data Structure

Each customer object in the response contains the following fields (as returned by Invoice Ninja API):

```json
{
  "id": "1",
  "user_id": "1",
  "company_id": "1",
  "name": "John Doe",
  "display_name": "John Doe",
  "balance": 0,
  "paid_to_date": 1000.00,
  "credit_balance": 0,
  "last_login": 1234567890,
  "size_id": null,
  "public_notes": "Customer notes",
  "private_notes": "Private notes",
  "website": "https://example.com",
  "industry_id": null,
  "vat_number": "VAT123456",
  "id_number": "ID123",
  "number": "0001",
  "shipping_address1": "123 Shipping St",
  "shipping_address2": "",
  "shipping_city": "City",
  "shipping_state": "State",
  "shipping_postal_code": "12345",
  "shipping_country_id": "840",
  "is_deleted": false,
  "group_settings_id": "1",
  "created_at": 1234567890,
  "updated_at": 1234567890,
  "contacts": [
    {
      "id": "1",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "phone": "+1234567890",
      "is_primary": true
    }
  ]
}
```

---

## Error Handling

### Common Error Responses:

**1. Integration Not Enabled:**
```json
{
  "success": false,
  "message": "Invoice Ninja integration is not enabled",
  "companies": [],
  "total_customers": 0
}
```

**2. No Company Mappings:**
```json
{
  "success": false,
  "message": "No company mappings found. Please configure company mappings in Invoice Ninja Settings.",
  "companies": [],
  "total_customers": 0
}
```

**3. Company Mapping Not Found:**
```json
{
  "success": false,
  "message": "No company mapping found for Company A"
}
```

**4. API Connection Error:**
```json
{
  "success": false,
  "message": "Error fetching customers for mapped companies: Connection timeout",
  "companies": [],
  "total_customers": 0
}
```

---

## Use Cases

### 1. Sync All Customers from All Companies
```python
import frappe

def sync_all_customers():
    """Sync customers from all mapped companies"""
    result = frappe.call(
        "invoice_ninja_integration.api.get_customers_for_mapped_companies",
        per_page=100
    )

    if result.get("success"):
        for company_data in result["companies"]:
            erpnext_company = company_data["erpnext_company"]

            for customer in company_data["customers"]:
                # Process or sync customer to ERPNext
                sync_customer_to_erpnext(customer, erpnext_company)

        frappe.msgprint(f"Synced {result['total_customers']} customers")
    else:
        frappe.throw(result.get("message"))
```

### 2. Display Customers in a Custom Page
```javascript
// In a custom page or dashboard
function displayCustomers() {
    frappe.call({
        method: "invoice_ninja_integration.api.get_customers_for_mapped_companies",
        args: { per_page: 50 },
        callback: function(r) {
            if (r.message && r.message.success) {
                // Build HTML to display customers
                let html = `<h3>Total Customers: ${r.message.total_customers}</h3>`;

                r.message.companies.forEach(company => {
                    html += `<h4>${company.invoice_ninja_company_name}</h4>`;
                    html += `<ul>`;

                    company.customers.forEach(customer => {
                        html += `<li>${customer.name} - ${customer.email || 'No email'}</li>`;
                    });

                    html += `</ul>`;
                });

                // Display in page
                $('#customer-list').html(html);
            }
        }
    });
}
```

### 3. Filter Customers by Company in a Report
```python
import frappe

@frappe.whitelist()
def get_customer_report(company=None):
    """Generate customer report for a specific company"""

    if not company:
        frappe.throw("Please select a company")

    result = frappe.call(
        "invoice_ninja_integration.api.get_customers_for_company",
        erpnext_company=company,
        per_page=1000
    )

    if result.get("success"):
        customers = result["customers"]

        # Process customers for report
        report_data = []
        for customer in customers:
            report_data.append({
                "customer_name": customer.get("name"),
                "email": customer.get("contacts", [{}])[0].get("email"),
                "balance": customer.get("balance"),
                "paid_to_date": customer.get("paid_to_date")
            })

        return report_data
    else:
        frappe.throw(result.get("message"))
```

---

## Pagination

Both API endpoints support pagination for handling large datasets:

```python
# Fetch first 50 customers
page_1 = frappe.call(
    "invoice_ninja_integration.api.get_customers_for_mapped_companies",
    page=1,
    per_page=50
)

# Fetch next 50 customers
page_2 = frappe.call(
    "invoice_ninja_integration.api.get_customers_for_mapped_companies",
    page=2,
    per_page=50
)

# Combine results
all_customers = []
for company in page_1["companies"]:
    all_customers.extend(company["customers"])
for company in page_2["companies"]:
    all_customers.extend(company["customers"])
```

---

## Best Practices

1. **Use Pagination**: When dealing with large customer lists, use pagination to avoid timeouts
2. **Error Handling**: Always check the `success` field in the response before processing data
3. **Company Context**: When syncing data to ERPNext, use the `erpnext_company` field to ensure correct company assignment
4. **Rate Limiting**: Be mindful of API rate limits when making multiple requests
5. **Caching**: Consider caching customer data to reduce API calls

---

## Troubleshooting

### Issue: Empty Customer List
**Cause:** No company mappings configured or Invoice Ninja companies have no customers
**Solution:**
1. Go to Invoice Ninja Settings
2. Configure company mappings
3. Verify customers exist in Invoice Ninja

### Issue: Connection Timeout
**Cause:** Invoice Ninja server not responding or incorrect URL
**Solution:**
1. Test connection in Invoice Ninja Settings
2. Verify Invoice Ninja URL and API token
3. Check network connectivity

### Issue: "No company mapping found"
**Cause:** Company mapping doesn't exist for the specified company
**Solution:**
1. Go to Invoice Ninja Settings
2. Add mapping for the specific company
3. Ensure mapping is enabled

---

## Similar Endpoints for Other Entity Types

The same pattern is available for other entity types:

### Invoices
- `get_invoices_for_mapped_companies(page, per_page)`
- `get_invoices_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`

### Quotations
- `get_quotations_for_mapped_companies(page, per_page)`
- `get_quotations_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`

### Items
- `get_items_for_mapped_companies(page, per_page)`
- `get_items_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`

### Payments
- `get_payments_for_mapped_companies(page, per_page)`
- `get_payments_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`

### Generic Endpoint
- `fetch_entities(entity_type, scope, company_identifier, page, per_page)` - Works with any entity type

## Related Documentation

- [Architecture Documentation](ARCHITECTURE.md) - Detailed architecture and design patterns
- [Company Mapping Feature](COMPANY_MAPPING.md) - Multi-company support
- [Setup Guide](SETUP_COMPLETE.md) - Installation and configuration
- [README](README.md) - General overview

## Support

For issues or questions, check the logs in:
- **Error Log**: ERPNext → Error Log
- **Invoice Ninja Sync Logs**: ERPNext → Invoice Ninja Sync Logs

For architecture questions, see [ARCHITECTURE.md](ARCHITECTURE.md)

