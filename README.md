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

## Installation

1. **Download and Install the App**
   ```bash
   # Navigate to your ERPNext site directory
   cd /path/to/your/site

   # Install the app
   bench get-app https://github.com/your-org/invoice_ninja_integration
   bench install-app invoice_ninja_integration
   ```

2. **Setup Invoice Ninja Settings**
   - Go to **Settings > Invoice Ninja Settings**
   - Configure your Invoice Ninja URL and API Token
   - Test the connection
   - Enable the sync options you need

## Configuration

### Basic Setup

1. **Invoice Ninja API Token**
   - In Invoice Ninja, go to Settings > API Tokens
   - Create a new token with appropriate permissions
   - Copy the token to ERPNext Invoice Ninja Settings

2. **Connection Settings**
   - Enter your Invoice Ninja URL (e.g., https://your-domain.invoiceninja.com)
   - Paste your API Token
   - Click "Test Connection" to verify

3. **Sync Configuration**
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

### Sync Operations
- `sync_from_invoice_ninja(doctype, limit)`: Pull data from Invoice Ninja
- `manual_sync_customer(customer_name)`: Sync specific customer
- `manual_sync_invoice(invoice_name)`: Sync specific invoice

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
├── api.py                 # Main API methods
├── tasks.py              # Scheduled tasks
├── hooks.py              # ERPNext hooks
├── utils/
│   ├── invoice_ninja_client.py  # API client
│   └── field_mapper.py          # Field mapping logic
├── doctype/
│   └── invoice_ninja_settings/  # Settings doctype
├── www/
│   └── webhook.py               # Webhook handler
└── fixtures/
    └── custom_field.json       # Custom field definitions
```

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

## Changelog

### Version 1.0.0
- Initial release
- Full bidirectional sync support
- Real-time webhooks
- Comprehensive error handling
- Background sync tasks
- Field mapping system

---

**Made with ❤️ for the ERPNext and Invoice Ninja communities**
