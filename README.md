# Invoice Ninja Integration for ERPNext

A robust ERPNext app that provides seamless two-way synchronization between ERPNext and Invoice Ninja, allowing you to manage your business operations across both platforms efficiently.

## Features

### ✅ Bidirectional Sync
- **Customers**: Sync customer data between ERPNext and Invoice Ninja
- **Invoices**: Sync sales invoices with line items and tax information
- **Quotations**: Sync quotes and estimates
- **Items/Products**: Sync product catalog
- **Payments**: Sync payment entries and transaction records

### ✅ Real-time Integration
- **Webhooks**: Real-time sync using Invoice Ninja webhooks
- **Background Jobs**: Scheduled sync for bulk operations
- **Error Handling**: Comprehensive error tracking and notification system

### ✅ Flexible Configuration
- **Selective Sync**: Enable/disable sync for specific document types
- **Field Mapping**: Intelligent field mapping between platforms
- **Sync Status Tracking**: Monitor sync status for each record
- **Multi-Instance Support**: Connect to multiple Invoice Ninja instances simultaneously
- **Easy Company Discovery**: One-click discovery of Invoice Ninja companies

## Installation

1. **Download and Install the App**
   ```bash
   # Navigate to your ERPNext site directory
   cd /path/to/your/site

   # Install the app
   bench get-app https://github.com/novizna-codes/invoice_ninja_integration
   bench install-app invoice_ninja_integration
   ```

2. **Setup Invoice Ninja Settings**
   - Go to **Settings > Invoice Ninja Settings**
   - Configure master credentials (for company discovery)
   - Fetch companies from Invoice Ninja
   - Set per-company API tokens
   - Test connections and enable sync options

## Configuration

### Basic Setup (v2.0 - Easy Discovery Method)

1. **Configure Master Credentials (For Discovery)**
   - Go to **Invoice Ninja Settings**
   - Enter your Invoice Ninja URL (e.g., https://your-domain.invoiceninja.com)
   - Enter Master API Token (admin token with access to list companies)
   - Click "Test Master Connection" to verify

2. **Discover Companies**
   - Click "Fetch Companies from Invoice Ninja" button
   - System will automatically:
     - Fetch all companies from your Invoice Ninja instance
     - Create Invoice Ninja Company docs
     - Set company IDs, names, and URLs
   - Review the created companies in Invoice Ninja Company list

3. **Set Per-Company Tokens**
   - Go to **Invoice Ninja Company** list
   - For each company:
     - Open the company document
     - Enter the API Token specific to this company
     - Click "Test Connection" to verify
     - Company will auto-enable when token is set

4. **Configure Company Mappings**
   - Go back to **Invoice Ninja Settings**
   - In "Company Mappings" section, link:
     - ERPNext Company → Invoice Ninja Company
   - Mark one as default if needed

5. **Sync Configuration**
   - Enable sync for the document types you need:
     - ☑️ Customer Sync
     - ☑️ Invoice Sync
     - ☑️ Quote Sync
     - ☑️ Product Sync
     - ☑️ Payment Sync

### Webhook Setup (Real-time Sync)

1. **Get Webhook URL**
   - The webhook URL is automatically generated in ERPNext settings
   - Copy the webhook URL

2. **Configure Invoice Ninja Webhooks**
   - In Invoice Ninja, go to Settings > API Webhooks
   - Add a new webhook with the URL from ERPNext
   - Select the events you want to sync in real-time

### Multi-Instance & Multi-Company Support

The app supports connecting to multiple Invoice Ninja instances and/or multiple companies within a single instance:

#### Supported Scenarios:
1. **Multiple Invoice Ninja Instances**
   - Connect to different Invoice Ninja servers
   - Each with its own URL and credentials

2. **Multi-Company Invoice Ninja Setup**
   - One Invoice Ninja instance with multiple companies
   - Each company has its own API token

3. **Mixed Setup** (Most Common)
   - Multiple instances AND multiple companies per instance
   - Full flexibility in configuration

#### Security Model:
- **Master Credentials** (in Settings): Used ONLY for discovering companies
- **Per-Company Tokens** (in Invoice Ninja Company): Used for all sync operations
- Clear separation between discovery and operation credentials

#### Benefits:
- ✅ Easy company discovery with one click
- ✅ Secure per-company token management
- ✅ Proper document routing between systems
- ✅ Isolated data per company
- ✅ Accurate financial reporting
- ✅ Compliance with multi-entity requirements

📖 **Detailed documentation**:
- [MULTI_INSTANCE_IMPLEMENTATION.md](MULTI_INSTANCE_IMPLEMENTATION.md) - Multi-instance architecture
- [COMPANY_MAPPING.md](COMPANY_MAPPING.md) - Company mapping details

### Field Mapping

The app automatically maps fields between ERPNext and Invoice Ninja:

| ERPNext | Invoice Ninja |
|---------|---------------|
| Customer Name | Name/Display Name |
| Email ID | Email |
| Mobile No | Phone |
| Tax ID | VAT Number |
| Address | Address Fields |
| Invoice Amount | Invoice Total |
| Payment Amount | Payment Amount |

## Usage

### Manual Sync

You can manually trigger sync operations:

```python
# Sync customers from Invoice Ninja to ERPNext
frappe.call("invoice_ninja_integration.api.sync_from_invoice_ninja", {"doctype": "Customer"})

# Sync a specific customer to Invoice Ninja
frappe.call("invoice_ninja_integration.api.manual_sync_customer", {"customer_name": "Customer Name"})
```

### Automatic Sync

The app automatically syncs data:

- **Real-time**: Via webhooks when data changes in Invoice Ninja
- **Scheduled**: Hourly background sync for new/updated records
- **Document Events**: When ERPNext documents are created/updated

### Sync Status

Each synced record shows its sync status:
- ✅ **Synced**: Successfully synchronized
- ⏳ **Not Synced**: Pending synchronization
- ❌ **Sync Failed**: Error occurred during sync
- 🗑️ **Deleted in Invoice Ninja**: Record was deleted in Invoice Ninja

## API Methods

### Configuration
- `get_invoice_ninja_settings()`: Get current settings
- `test_connection()`: Test Invoice Ninja API connection
- `get_company_mappings()`: Get all company mappings from settings
- `get_invoice_ninja_companies()`: Fetch companies from Invoice Ninja

### Sync Operations (Updated)

**Recommended**: Use per-company sync functions
- `sync_company_entities(company_name, entity_type, limit)`: Sync specific entity for a company
- `sync_company_all_entities(company_name, entity_types, limit)`: Sync multiple entities for a company
- `trigger_manual_sync(sync_type)`: Manual sync for all enabled companies
- `manual_sync_customer(customer_name)`: Sync specific customer to Invoice Ninja
- `manual_sync_invoice(invoice_name)`: Sync specific invoice to Invoice Ninja

**Deprecated** (will be removed in future):
- `sync_from_invoice_ninja(doctype, limit)`: Old function without per-company support

**Example**:
```python
# New way - with per-company mappings
from invoice_ninja_integration.api import sync_company_entities

result = sync_company_entities(
    invoice_ninja_company="IN-COM-YourCompany-000001",
    entity_type="Customer",
    limit=100
)
```

### Entity Fetch Operations (Centralized Service)

All fetch operations now use the centralized `SyncManager` service for consistency and maintainability.

#### Customer Methods
- `get_customers_for_mapped_companies(page, per_page)`: Get customers from all mapped companies
- `get_customers_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`: Get customers for a specific company

#### Invoice Methods
- `get_invoices_for_mapped_companies(page, per_page)`: Get invoices from all mapped companies
- `get_invoices_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`: Get invoices for a specific company

#### Quotation Methods
- `get_quotations_for_mapped_companies(page, per_page)`: Get quotations from all mapped companies
- `get_quotations_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`: Get quotations for a specific company

#### Item Methods
- `get_items_for_mapped_companies(page, per_page)`: Get items from all mapped companies
- `get_items_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`: Get items for a specific company

#### Payment Methods
- `get_payments_for_mapped_companies(page, per_page)`: Get payments from all mapped companies
- `get_payments_for_company(erpnext_company, invoice_ninja_company_id, page, per_page)`: Get payments for a specific company

#### Generic Endpoint
- `fetch_entities(entity_type, scope, company_identifier, page, per_page)`: Generic endpoint to fetch any entity type

📖 **Detailed API documentation**: See [CUSTOMER_FETCH_API.md](CUSTOMER_FETCH_API.md)
🏗️ **Architecture details**: See [ARCHITECTURE.md](ARCHITECTURE.md)

### Webhook Handler
- `webhook.py`: Handles real-time webhook events from Invoice Ninja

## Scheduled Tasks

The app includes several background tasks:

- **Hourly**: `sync_invoice_ninja_data()` - Pull latest data
- **Daily**: `full_sync_check()` - Check for missing records
- **Daily**: `cleanup_sync_logs()` - Clean old logs
- **Weekly**: `weekly_sync_report()` - Generate sync reports

## Error Handling

### Error Tracking
- All sync errors are logged in ERPNext Error Log
- Email notifications for critical errors
- Automatic retry mechanism for failed syncs

### Troubleshooting

1. **Connection Issues**
   - Verify Invoice Ninja URL and API token
   - Check network connectivity
   - Review API token permissions

2. **Sync Failures**
   - Check ERPNext Error Log for details
   - Verify field mappings
   - Ensure required fields are populated

3. **Webhook Issues**
   - Verify webhook URL in Invoice Ninja
   - Check webhook secret configuration
   - Review webhook event logs

## Custom Fields

The app adds these custom fields to ERPNext doctypes:

- `invoice_ninja_id`: Stores Invoice Ninja record ID
- `sync_status`: Shows current sync status

## Development

### Project Structure
```
invoice_ninja_integration/
├── api.py                           # Main API methods (uses SyncManager)
├── tasks.py                         # Scheduled tasks
├── hooks.py                         # ERPNext hooks
├── utils/
│   ├── base_integration_service.py # Base class for integrations (reusable)
│   ├── sync_manager.py              # Centralized service (extends base)
│   ├── invoice_ninja_client.py      # API client
│   ├── field_mapper.py              # Field mapping logic
│   └── company_mapper.py            # Multi-company mapping
├── doctype/
│   ├── invoice_ninja_settings/      # Settings doctype
│   ├── invoice_ninja_company/       # Company doctype
│   └── invoice_ninja_company_mapping/ # Company mapping child table
├── www/
│   └── webhook.py                   # Webhook handler
└── fixtures/
    └── custom_field.json            # Custom field definitions
```

### Architecture

The app follows a centralized service architecture:

- **BaseIntegrationService**: Abstract base class providing reusable patterns for any third-party integration
- **SyncManager**: Concrete implementation for Invoice Ninja, handling all fetch and sync operations
- **API Layer**: Thin wrapper around SyncManager, exposing whitelisted methods
- **Supporting Components**: Client, mappers, and company context management

This architecture enables:
- Single source of truth for all operations
- Easy addition of new entity types via configuration
- Reusable pattern for other integration apps (Shopify, Stripe, etc.)

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For support and issues:
- Create an issue on GitHub
- Check the ERPNext Error Log for detailed error messages
- Review the Invoice Ninja API documentation

## License

This project is licensed under the MIT License.

---

## Multi-Currency Setup

If you work with multiple currencies, you need to map each currency to an appropriate receivable account in ERPNext. This ensures that the receivable account currency matches the invoice currency, which is required by ERPNext for multi-currency invoicing.

**Note**: Currency account mapping is **ONLY for Sales Invoice syncing**. Other entities like Payment Entries, Quotations, and Items are not affected by this mapping.

### Prerequisites

1. **Set up currency-specific receivable accounts** in ERPNext:
   - Go to: Accounting > Chart of Accounts
   - Find your Debtors/Accounts Receivable group
   - Create separate accounts for each currency (e.g., "Debtors - USD", "Debtors - EUR")
   - Set the Account Currency field for each account

2. **Configure Currency Mappings**:
   - Open your Invoice Ninja Company document
   - Scroll to "Currency Account Mapping" section
   - Add a row for each currency you use
   - Select the currency and corresponding receivable account
   - Optionally mark one as default for currencies without specific mapping

3. **Use Auto-Setup** (Optional):
   - Click "Setup Currency Mappings" button under Actions
   - The system will analyze your existing invoices and suggest mappings
   - Review and adjust as needed

### Example Setup

| Currency | Receivable Account | Is Default |
|----------|-------------------|------------|
| USD      | Debtors - USD     | ✓ Yes      |
| EUR      | Debtors - EUR     | No         |
| GBP      | Debtors - GBP     | No         |

---

## Incremental Sync & Performance Optimization

Starting with v2.1, the integration includes intelligent incremental sync that dramatically improves performance for large datasets.

### How It Works

The system uses **hash-based change detection** to identify which records have actually changed:

1. **First Sync**: All records are synced and their field hashes are calculated and stored
2. **Subsequent Syncs**: Only records with changed hashes are updated
3. **Result**: 50-90% reduction in processing time and database writes

### Tracked Fields by Entity Type

The system monitors key fields for changes:

**Customer**: name, email, phone, group, territory, tax ID
**Sales Invoice**: customer, dates, currency, amounts, line items, status
**Quotation**: customer, dates, amounts, line items, status
**Item**: code, name, group, description, rate
**Payment Entry**: party, amounts, payment references
**Tasks**: description, duration, rate, status

### Sync Statistics

Every sync operation provides detailed statistics:

- ✓ **New records created**: Records that didn't exist before
- ✓ **Records updated**: Existing records with changes
- ○ **Records unchanged**: Skipped records (no changes detected)
- ⚠ **Records skipped**: Records that couldn't be synced (e.g., missing currency mapping)
- ✗ **Records failed**: Records that encountered errors

### Usage

**Default Behavior (Incremental)**:
```python
# Only syncs changed records
frappe.call({
    method: 'invoice_ninja_integration.api.sync_company_entities',
    args: {
        invoice_ninja_company: 'Company Name',
        entity_type: 'Customer',
        limit: 100
    }
})
```

**Force Full Sync**:
```python
# Re-syncs ALL records regardless of changes
frappe.call({
    method: 'invoice_ninja_integration.api.sync_company_entities',
    args: {
        invoice_ninja_company: 'Company Name',
        entity_type: 'Customer',
        limit: 100,
        force_full_sync: true
    }
})
```

### Performance Benefits

For a typical dataset of 1,000+ records:

- **First sync**: ~2-5 minutes (all records processed)
- **Subsequent syncs**: ~20-60 seconds (only changed records)
- **API calls saved**: 50-90% reduction
- **Database writes saved**: 50-90% reduction

### Currency Validation for Invoices

Invoices require proper currency mappings to be synced. If a currency mapping is missing:

1. The invoice is **skipped** (not created)
2. A detailed error log is created
3. The sync statistics show skipped count
4. You're notified which invoices need attention

**Example skipped invoice notification**:
```
⚠ 3 invoices skipped (missing currency mapping):
- Invoice INV-001 (EUR)
- Invoice INV-002 (GBP)
- Invoice INV-003 (CAD)
```

**To resolve**: Configure currency account mappings in your Invoice Ninja Company settings.

### Best Practices

1. **Initial Setup**: Run first sync during off-peak hours for large datasets
2. **Regular Syncs**: Let incremental sync run automatically (hourly/daily)
3. **Currency Setup**: Configure all currency mappings before syncing invoices
4. **Force Full Sync**: Only use when necessary (e.g., after major data fixes)
5. **Monitor Logs**: Check sync statistics to identify skipped/failed records

---
| EUR      | Debtors - EUR     |            |
| GBP      | Debtors - GBP     |            |

### How It Works

When syncing a Sales Invoice from Invoice Ninja:
1. The invoice currency is detected (e.g., EUR)
2. The system looks up the currency mapping in the Invoice Ninja Company
3. If a mapping exists (EUR → "Debtors - EUR"), it sets the `debit_to` field
4. If no mapping exists, ERPNext uses the customer's default receivable account

## Changelog

### Version 1.0.0
- Initial release
- Full bidirectional sync support
- Real-time webhooks
- Comprehensive error handling
- Background sync tasks
- Field mapping system

---

## Advanced Features

### Smart Payment Sync

The payment sync system intelligently syncs payments only for paid invoices with comprehensive tracking:

#### Features
- ✅ **Smart Validation**: Only syncs payments for invoices marked as "Paid" in Invoice Ninja
- ✅ **Status Checking**: Validates Invoice Ninja status before attempting sync
- ✅ **Deduplication**: Prevents duplicate payment entries
- ✅ **Comprehensive Tracking**: 8 custom fields on Sales Invoice for payment audit trail
- ✅ **Automatic Sync**: Triggers on invoice submission and daily checks for unpaid invoices
- ✅ **Error Handling**: Detailed error messages and skip reasons

#### Payment Tracking Fields

| Field | Purpose |
|-------|---------|
| `invoice_ninja_payment_status` | Current sync status (Not Checked, No Payments, Synced, Failed, Not Eligible) |
| `invoice_ninja_payments_synced` | Boolean flag indicating if payments were synced |
| `invoice_ninja_last_payment_check` | Timestamp of last payment check |
| `invoice_ninja_payment_sync_count` | Number of payments synced |
| `invoice_ninja_paid_to_date` | Total amount paid in Invoice Ninja |
| `invoice_ninja_payment_skip_reason` | Reason if sync was skipped |
| `invoice_ninja_payment_error` | Error message if sync failed |

#### Workflow

1. **On Invoice Submit**: Automatically checks for payments after invoice is submitted in ERPNext
2. **Daily Task**: Checks unpaid invoices (with outstanding amounts) for new payments
3. **Status Validation**: Only syncs if Invoice Ninja status is "Paid" (status_id = 4)
4. **Payment Creation**: Creates Payment Entry documents in ERPNext
5. **Tracking Update**: Updates all tracking fields with results

#### Manual Payment Sync

```python
# Sync payments for a specific invoice
frappe.call({
    method: 'invoice_ninja_integration.api.sync_payments_for_invoice',
    args: {
        invoice_doc_name: 'SINV-00001',
        invoice_ninja_id: '123',
        invoice_ninja_company: 'Company Name'
    }
})
```

📖 **Detailed documentation**: See [PAYMENT_SYNC_IMPLEMENTATION.md](docs/PAYMENT_SYNC_IMPLEMENTATION.md) (archived for reference)

---

### Webhook Integration with Security

The webhook handler provides real-time sync with enterprise-grade security:

#### Features
- ✅ **HMAC SHA-256 Signature Verification**: Ensures webhooks are from Invoice Ninja
- ✅ **Smart Company Detection**: 4-tier fallback strategy to identify the triggering company
- ✅ **Incremental Sync**: Only updates records when data actually changes
- ✅ **Comprehensive Logging**: All webhook events are logged for auditing
- ✅ **Entity Support**: Customers, Invoices, Quotations, Items, Payments
- ✅ **Graceful Error Handling**: Detailed logging with no service disruption

#### Company Detection Strategy

The webhook handler uses a 4-tier fallback to identify which Invoice Ninja Company triggered the webhook:

1. **URL Parameter** (Most Reliable): `?company=Company-Name`
2. **Existing Entity Lookup**: Check if entity exists and get its company
3. **Company ID from Payload**: Use `company_id` field to lookup company
4. **Single Company Fallback**: If only one enabled company exists, use it

#### Setup Webhook in Invoice Ninja

1. Go to **Settings > Webhooks** in Invoice Ninja
2. Add webhook URL: `https://yoursite.com/api/method/invoice_ninja_integration.webhook_handler.handle_webhook`
3. For multi-company: Add `?company=Company-Name` parameter
4. Select events: `client.created`, `client.updated`, `invoice.created`, etc.
5. (Optional) Set webhook secret for signature verification

#### Configure Webhook Secret

1. In ERPNext, go to **Invoice Ninja Settings**
2. Set **Webhook Secret** (same as in Invoice Ninja)
3. This enables HMAC SHA-256 signature verification for security

📖 **Detailed documentation**: See [WEBHOOK_HANDLER_IMPLEMENTATION.md](docs/WEBHOOK_HANDLER_IMPLEMENTATION.md) (archived for reference)

---

### Auto-Submit Settings

Control whether synced documents are automatically submitted or remain in draft state:

#### Available Settings

| Setting | Document Type | Default |
|---------|--------------|---------|
| `auto_submit_invoices` | Sales Invoice | Off |
| `auto_submit_quotations` | Quotation | Off |
| `auto_submit_payments` | Payment Entry | Off |

#### Configuration

1. Go to **Invoice Ninja Settings**
2. Scroll to **Auto Submit Settings** section
3. Enable checkboxes for document types you want to auto-submit
4. Save settings

#### Behavior

**When OFF (Default)**:
- Documents are created in **Draft** state
- Allows manual review before submission
- Safer for compliance and review workflows

**When ON**:
- Documents are automatically submitted after sync
- Faster processing, no manual intervention
- Suitable for trusted, automated workflows

📖 **Detailed documentation**: See [AUTO_SUBMIT_SETTINGS_IMPLEMENTATION.md](docs/AUTO_SUBMIT_SETTINGS_IMPLEMENTATION.md) (archived for reference)

---

### Custom Exchange Rate Providers

The app uses a **plugin system** for exchange rate providers, allowing you to use custom exchange rate sources without modifying the app code:

#### Features
- ✅ **Zero Hardcoded Dependencies**: No proprietary app references
- ✅ **Open Source Friendly**: Works with standard ERPNext
- ✅ **Extensible**: Any app can provide custom exchange rate logic
- ✅ **Graceful Fallback**: Uses Invoice Ninja rates if no provider available

#### How It Works

**Default Behavior** (No Custom Provider):
- Uses ERPNext's standard `get_exchange_rate()` function
- Falls back to Invoice Ninja's provided exchange rate

**With Custom Provider**:
- Detects custom provider via hooks
- Uses custom logic (e.g., regional APIs, cached rates, smart routing)
- Falls back to Invoice Ninja rate if provider fails

#### Creating a Custom Provider

1. **In your custom app's `hooks.py`**:
```python
currency_exchange_provider = "your_app.exchange_rates.get_custom_exchange_rate"
```

2. **Implement the provider function**:
```python
def get_custom_exchange_rate(from_currency, to_currency, transaction_date, args=None):
    """
    Args:
        from_currency: Source currency (e.g., "USD")
        to_currency: Target currency (e.g., "PKR")
        transaction_date: Date in YYYY-MM-DD format
        args: Optional additional arguments

    Returns:
        Exchange rate as float (e.g., 279.65)
    """
    # Your custom logic here
    return fetch_rate_from_your_source(from_currency, to_currency, transaction_date)
```

3. **The Invoice Ninja Integration app automatically detects and uses your provider**

#### Example Use Cases

- **Regional APIs**: Use State Bank rates for PKR, RBI rates for INR
- **Smart Routing**: Route based on company context or currency pairs
- **Caching**: Implement rate caching for better performance
- **Multiple Fallbacks**: Try multiple sources before giving up

📖 **Full documentation**: See [EXCHANGE_RATE_PROVIDERS.md](EXCHANGE_RATE_PROVIDERS.md) for detailed examples and implementation guide

---

### Task & Time Tracking

Sync time tracking data from Invoice Ninja:

#### Features
- ✅ **Task Sync**: Sync tasks with duration and rates
- ✅ **Invoice Linking**: Automatically link tasks to invoices
- ✅ **Status Tracking**: Track billable/non-billable status
- ✅ **Client Association**: Link tasks to customers

#### Sync Tasks

```python
# Sync tasks for a company
frappe.call({
    method: 'invoice_ninja_integration.api.sync_tasks_from_invoice_ninja',
    args: {
        invoice_ninja_company_id: 'Company Name',
        limit: 100
    }
})
```

---

## Troubleshooting Guide

### Connection Issues

**Problem**: Connection test fails

**Solutions**:
1. Verify Invoice Ninja URL is correct (including https://)
2. Check API token has proper permissions
3. Ensure network connectivity (firewall, proxy)
4. Test API token directly using curl:
   ```bash
   curl -H "X-Api-Token: YOUR_TOKEN" https://your-domain.invoiceninja.com/api/v1/clients
   ```

### Sync Issues

**Problem**: Records not syncing

**Solutions**:
1. Check sync is enabled for the entity type in settings
2. Verify company mapping is configured correctly
3. Review Error Log for detailed error messages
4. Check field validation (required fields must be populated)

**Problem**: Duplicate records created

**Solutions**:
1. Ensure `invoice_ninja_id` field is properly set
2. Check deduplication logic in sync functions
3. Review sync logs for "unchanged" vs "created" actions

### Currency Mapping Issues

**Problem**: Invoices being skipped (currency mapping error)

**Solutions**:
1. Configure currency account mappings in Invoice Ninja Company
2. Create currency-specific receivable accounts in Chart of Accounts
3. Use "Setup Currency Mappings" button for auto-setup
4. Check sync statistics for list of skipped invoices with currency info

### Webhook Issues

**Problem**: Webhooks not triggering

**Solutions**:
1. Verify webhook URL is correct in Invoice Ninja
2. Check webhook is enabled for the correct events
3. Review webhook logs in Invoice Ninja
4. Test webhook using Invoice Ninja's "Test" button
5. Check ERPNext Error Log for webhook handler errors

**Problem**: Signature verification fails

**Solutions**:
1. Ensure webhook secret matches in both systems
2. Check Invoice Ninja is sending signature in headers
3. Temporarily disable verification for testing (remove webhook_secret)

### Payment Sync Issues

**Problem**: Payments not syncing for paid invoices

**Solutions**:
1. Check invoice status in Invoice Ninja (must be status 4 = Paid)
2. Verify `paid_to_date` amount is > 0
3. Check payment tracking fields on Sales Invoice
4. Review `invoice_ninja_payment_skip_reason` field for details
5. Ensure auto-submit is enabled if you want payments submitted

### Performance Issues

**Problem**: Sync taking too long

**Solutions**:
1. Use incremental sync (default behavior)
2. Reduce sync limit per batch
3. Enable incremental sync monitoring via statistics
4. Check for network latency to Invoice Ninja
5. Review unchanged record percentages in sync statistics

---

## API Reference

### Core Sync Methods

```python
# Test connection for a specific company
frappe.call('invoice_ninja_integration.api.test_invoice_ninja_company_connection',
    {'invoice_ninja_company': 'Company Name'})

# Sync entities for a company
frappe.call('invoice_ninja_integration.api.sync_company_entities',
    {
        'invoice_ninja_company': 'Company Name',
        'entity_type': 'Customer',  # Customer, Sales Invoice, Quotation, Item, Payment Entry
        'limit': 100,
        'force_full_sync': False  # Set to True to re-sync all records
    })

# Sync multiple entity types
frappe.call('invoice_ninja_integration.api.sync_company_all_entities',
    {
        'invoice_ninja_company': 'Company Name',
        'entity_types': ['Customer', 'Sales Invoice', 'Item'],
        'limit': 100
    })

# Trigger manual sync for all companies
frappe.call('invoice_ninja_integration.api.trigger_manual_sync',
    {'sync_type': 'all'})  # all, customers, invoices, quotations, items, payments
```

### Company Management

```python
# Fetch and create Invoice Ninja Companies
frappe.call('invoice_ninja_integration.api.fetch_and_create_invoice_ninja_companies')

# Get company sync statistics
frappe.call('invoice_ninja_integration.api.get_company_sync_statistics',
    {
        'invoice_ninja_company': 'Company Name',
        'days': 7
    })
```

### Payment Sync

```python
# Sync payments for a specific invoice
frappe.call('invoice_ninja_integration.api.sync_payments_for_invoice',
    {
        'invoice_doc_name': 'SINV-00001',
        'invoice_ninja_id': '123',
        'invoice_ninja_company': 'Company Name'
    })
```

### Currency Mapping

```python
# Auto-suggest currency mappings based on existing invoices
frappe.call('invoice_ninja_integration.api.suggest_currency_mappings',
    {'invoice_ninja_company': 'Company Name'})
```

### Dashboard & Monitoring

```python
# Get dashboard statistics
frappe.call('invoice_ninja_integration.api.get_dashboard_stats')

# Get recent activity
frappe.call('invoice_ninja_integration.api.get_recent_activity', {'limit': 10})

# Get sync logs
frappe.call('invoice_ninja_integration.api.get_sync_logs', {'limit': 5})
```

---

## License

This project is licensed under the MIT License - see the [license.txt](license.txt) file for details.

---

**Made with ❤️ for the ERPNext and Invoice Ninja communities**
