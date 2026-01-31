# Quick Start: Fetching Customers from Invoice Ninja

This guide will help you quickly get started with fetching customers from Invoice Ninja for mapped companies.

## Prerequisites

✅ Invoice Ninja Settings configured
✅ Company mappings set up
✅ Integration enabled

## Step 1: Verify Company Mappings

First, make sure you have company mappings configured:

**Via UI:**
1. Go to `Invoice Ninja Settings`
2. Scroll to "Company Mappings" section
3. Ensure you have at least one mapping enabled

**Via Python:**
```python
import frappe

# Get all company mappings
result = frappe.call("invoice_ninja_integration.api.get_company_mappings")

if result.get("success"):
    for mapping in result["mappings"]:
        print(f"{mapping['erpnext_company']} → {mapping['invoice_ninja_company_name']}")
else:
    print("No company mappings found!")
```

## Step 2: Fetch Customers from All Companies

### Python (Server-side)

```python
import frappe

# Get customers from all mapped companies
result = frappe.call(
    "invoice_ninja_integration.api.get_customers_for_mapped_companies",
    page=1,
    per_page=50
)

if result.get("success"):
    print(f"Total Customers: {result['total_customers']}")

    for company_data in result["companies"]:
        print(f"\nCompany: {company_data['invoice_ninja_company_name']}")
        print(f"Customers: {company_data['customer_count']}")

        for customer in company_data["customers"]:
            print(f"  - {customer['name']} (ID: {customer['id']})")
```

### JavaScript (Client-side)

```javascript
frappe.call({
    method: "invoice_ninja_integration.api.get_customers_for_mapped_companies",
    args: {
        page: 1,
        per_page: 50
    },
    callback: function(r) {
        if (r.message && r.message.success) {
            console.log("Total Customers:", r.message.total_customers);

            r.message.companies.forEach(company => {
                console.log(`Company: ${company.invoice_ninja_company_name}`);
                console.log(`Customers: ${company.customer_count}`);
            });

            frappe.msgprint(`Found ${r.message.total_customers} customers`);
        } else {
            frappe.msgprint("Failed to fetch customers");
        }
    }
});
```

### REST API (cURL)

```bash
curl -X POST "http://your-site.local/api/method/invoice_ninja_integration.api.get_customers_for_mapped_companies" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "per_page": 50
  }'
```

## Step 3: Fetch Customers from a Specific Company

### Python

```python
import frappe

# Using ERPNext company name
result = frappe.call(
    "invoice_ninja_integration.api.get_customers_for_company",
    erpnext_company="Company A",
    page=1,
    per_page=50
)

if result.get("success"):
    print(f"Company: {result['invoice_ninja_company_name']}")
    print(f"Customers: {result['customer_count']}")

    for customer in result["customers"]:
        print(f"  - {customer['name']}")
```

### JavaScript

```javascript
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
            console.log("Customers:", r.message.customer_count);

            r.message.customers.forEach(customer => {
                console.log(`  - ${customer.name}`);
            });
        }
    }
});
```

## Step 4: Process Customer Data

### Example: Display Customer Details

```python
import frappe

def display_customer_details():
    result = frappe.call(
        "invoice_ninja_integration.api.get_customers_for_mapped_companies",
        per_page=10
    )

    if result.get("success"):
        for company_data in result["companies"]:
            print(f"\n{'='*60}")
            print(f"Company: {company_data['invoice_ninja_company_name']}")
            print(f"{'='*60}")

            for customer in company_data["customers"]:
                print(f"\nCustomer: {customer.get('name', 'N/A')}")
                print(f"  ID: {customer.get('id')}")
                print(f"  Number: {customer.get('number', 'N/A')}")
                print(f"  Balance: ${customer.get('balance', 0):.2f}")
                print(f"  Paid to Date: ${customer.get('paid_to_date', 0):.2f}")
                print(f"  Website: {customer.get('website', 'N/A')}")
                print(f"  VAT Number: {customer.get('vat_number', 'N/A')}")

                # Display contacts
                contacts = customer.get('contacts', [])
                if contacts:
                    print(f"  Contacts:")
                    for contact in contacts:
                        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                        email = contact.get('email', 'N/A')
                        phone = contact.get('phone', 'N/A')
                        is_primary = " (Primary)" if contact.get('is_primary') else ""
                        print(f"    - {name}{is_primary}")
                        print(f"      Email: {email}")
                        print(f"      Phone: {phone}")
```

### Example: Export to JSON

```python
import frappe
import json

def export_customers_to_json(filename="customers.json"):
    result = frappe.call(
        "invoice_ninja_integration.api.get_customers_for_mapped_companies",
        per_page=100
    )

    if result.get("success"):
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Customers exported to {filename}")
    else:
        print(f"Error: {result.get('message')}")
```

### Example: Sync Customers to ERPNext

```python
import frappe
from frappe import _

def sync_customers_to_erpnext():
    """Fetch and sync all customers from Invoice Ninja to ERPNext"""

    result = frappe.call(
        "invoice_ninja_integration.api.get_customers_for_mapped_companies",
        per_page=100
    )

    if not result.get("success"):
        frappe.throw(_(result.get("message")))

    synced_count = 0
    error_count = 0

    for company_data in result["companies"]:
        erpnext_company = company_data["erpnext_company"]

        for customer in company_data["customers"]:
            try:
                # Check if customer already exists
                existing = frappe.db.exists(
                    "Customer",
                    {"invoice_ninja_id": str(customer.get('id'))}
                )

                if existing:
                    print(f"Customer {customer.get('name')} already exists. Skipping.")
                    continue

                # Create new customer in ERPNext
                customer_doc = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": customer.get("name"),
                    "customer_type": "Company",
                    "customer_group": "Commercial",  # Adjust as needed
                    "territory": "All Territories",  # Adjust as needed
                    "company": erpnext_company,
                    "invoice_ninja_id": str(customer.get("id")),
                    "invoice_ninja_sync_status": "Synced"
                })

                customer_doc.insert(ignore_permissions=True)
                synced_count += 1
                print(f"Created customer: {customer.get('name')}")

            except Exception as e:
                error_count += 1
                frappe.log_error(
                    f"Error syncing customer {customer.get('name')}: {str(e)}",
                    "Customer Sync Error"
                )

    frappe.db.commit()

    print(f"\nSync Complete!")
    print(f"Synced: {synced_count}")
    print(f"Errors: {error_count}")

    return {
        "synced": synced_count,
        "errors": error_count
    }
```

## Step 5: Test Your Implementation

Run the test script to verify everything works:

```bash
# From your bench directory
bench --site [site-name] execute invoice_ninja_integration.test_customer_fetch.test_fetch_customers
```

Or run individual tests:

```python
import frappe

# Test company mappings
frappe.call("invoice_ninja_integration.test_customer_fetch.test_company_mappings")

# Test fetching from all companies
frappe.call("invoice_ninja_integration.test_customer_fetch.test_fetch_customers_all_companies")

# Test fetching from single company
frappe.call("invoice_ninja_integration.test_customer_fetch.test_fetch_customers_single_company")
```

## Common Use Cases

### 1. Dashboard Widget

Create a dashboard widget showing customer counts per company:

```javascript
frappe.ui.form.on('Dashboard', {
    refresh: function(frm) {
        frappe.call({
            method: "invoice_ninja_integration.api.get_customers_for_mapped_companies",
            args: { per_page: 1 },  // Just get count
            callback: function(r) {
                if (r.message && r.message.success) {
                    let html = '<div class="invoice-ninja-stats">';
                    html += `<h4>Invoice Ninja Customers: ${r.message.total_customers}</h4>`;
                    html += '<ul>';

                    r.message.companies.forEach(company => {
                        html += `<li>${company.invoice_ninja_company_name}: ${company.customer_count}</li>`;
                    });

                    html += '</ul></div>';

                    $(frm.fields_dict.customer_stats.wrapper).html(html);
                }
            }
        });
    }
});
```

### 2. Scheduled Sync

Create a scheduled job to sync customers daily:

```python
# In hooks.py, add to scheduler_events
scheduler_events = {
    "daily": [
        "invoice_ninja_integration.tasks.sync_all_customers"
    ]
}

# In tasks.py
def sync_all_customers():
    """Scheduled task to sync customers from Invoice Ninja"""
    from invoice_ninja_integration.api import sync_from_invoice_ninja

    result = sync_from_invoice_ninja("Customer", limit=200)

    if result.get("success"):
        frappe.log(f"Synced {result.get('synced_count')} customers")
    else:
        frappe.log_error(result.get("message"), "Customer Sync Failed")
```

### 3. Custom Report

Create a report showing Invoice Ninja customers:

```python
def execute(filters=None):
    columns = [
        {"fieldname": "customer_name", "label": "Customer", "fieldtype": "Data", "width": 200},
        {"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"fieldname": "balance", "label": "Balance", "fieldtype": "Currency", "width": 120},
        {"fieldname": "paid_to_date", "label": "Paid to Date", "fieldtype": "Currency", "width": 120}
    ]

    result = frappe.call(
        "invoice_ninja_integration.api.get_customers_for_mapped_companies",
        per_page=500
    )

    data = []
    if result.get("success"):
        for company_data in result["companies"]:
            for customer in company_data["customers"]:
                data.append({
                    "customer_name": customer.get("name"),
                    "company": company_data["erpnext_company"],
                    "balance": customer.get("balance", 0),
                    "paid_to_date": customer.get("paid_to_date", 0)
                })

    return columns, data
```

## Troubleshooting

### Issue: Empty Results

```python
# Check if company mappings exist
result = frappe.call("invoice_ninja_integration.api.get_company_mappings")
print(result)

# Check if integration is enabled
settings = frappe.get_single("Invoice Ninja Settings")
print(f"Enabled: {settings.enabled}")
print(f"URL: {settings.invoice_ninja_url}")
```

### Issue: API Errors

```python
# Test connection
result = frappe.call("invoice_ninja_integration.api.test_connection")
print(result)

# Check error logs
error_logs = frappe.get_all(
    "Error Log",
    filters={"method": ["like", "%invoice_ninja%"]},
    fields=["creation", "error"],
    limit=5
)
for log in error_logs:
    print(f"{log.creation}: {log.error[:100]}...")
```

## Next Steps

- Review the full API documentation: [CUSTOMER_FETCH_API.md](CUSTOMER_FETCH_API.md)
- Learn about company mapping: [COMPANY_MAPPING.md](COMPANY_MAPPING.md)
- Explore the codebase: [README.md](README.md)

## Support

If you encounter issues:
1. Check the ERPNext Error Log
2. Review Invoice Ninja Sync Logs
3. Verify company mappings
4. Test API connection

Happy coding! 🚀

