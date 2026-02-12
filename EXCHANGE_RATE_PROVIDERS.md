# Exchange Rate Providers - Plugin System

This document explains how the Invoice Ninja Integration app uses a plugin system for exchange rate providers, allowing other apps to provide enhanced exchange rate functionality without hardcoding dependencies.

## Overview

The Invoice Ninja Integration uses a **generic hook-based system** to support custom exchange rate providers. This means:

✅ **Zero Hardcoded Dependencies**: No references to private/proprietary apps
✅ **Open Source Friendly**: Works out-of-the-box with standard ERPNext
✅ **Extensible**: Any app can provide custom exchange rate logic
✅ **Graceful Fallback**: Automatically falls back to ERPNext standard if no custom provider is available

## How It Works

### Default Behavior (No Custom Provider)

When no custom exchange rate provider is registered:

```
Invoice Ninja Invoice → field_mapper.py → ERPNext get_exchange_rate()
```

The app uses ERPNext's standard `erpnext.setup.utils.get_exchange_rate` function, which:
- Checks Currency Exchange table
- Falls back to frankfurter.app API
- Creates Currency Exchange records automatically

### With Custom Provider

When a custom provider is registered via hooks:

```
Invoice Ninja Invoice → field_mapper.py → Custom Provider → Enhanced Rates
```

The app automatically detects and uses the custom provider, which might offer:
- Regional exchange rate APIs (e.g., State Bank of Pakistan)
- Smart routing based on company context
- Cached rates for better performance
- Multiple fallback sources

## Registering a Custom Provider

To register your custom exchange rate provider, add this to your app's `hooks.py`:

```python
# In your_app/hooks.py

currency_exchange_provider = "your_app.path.to.your_function"
```

### Provider Function Signature

Your provider function must match ERPNext's standard signature:

```python
def your_custom_exchange_rate_function(
    from_currency: str,
    to_currency: str,
    transaction_date: str,
    args=None
) -> float:
    """
    Get exchange rate

    Args:
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "PKR")
        transaction_date: Date in YYYY-MM-DD format
        args: Optional additional arguments

    Returns:
        Exchange rate as float (e.g., 279.65)
        Returns 0 or None if rate not available
    """
    # Your custom logic here
    rate = fetch_rate_from_your_source(from_currency, to_currency, transaction_date)

    return rate
```

### Example: Simple Custom Provider

```python
# In your_app/exchange_rates.py

import frappe
import requests

def get_custom_exchange_rate(from_currency, to_currency, transaction_date, args=None):
    """Custom exchange rate provider using your preferred API"""

    # Same currency
    if from_currency == to_currency:
        return 1.0

    try:
        # Call your preferred exchange rate API
        response = requests.get(
            f"https://your-api.com/rates",
            params={
                "from": from_currency,
                "to": to_currency,
                "date": transaction_date
            }
        )

        data = response.json()
        return float(data["rate"])

    except Exception as e:
        frappe.log_error(f"Exchange rate fetch failed: {str(e)}")
        return 0.0
```

Then in `hooks.py`:

```python
currency_exchange_provider = "your_app.exchange_rates.get_custom_exchange_rate"
```

## Real-World Example: Enhanced Provider with Smart Routing

Here's a more sophisticated example that uses smart routing based on company context:

```python
def smart_exchange_rate_provider(from_currency, to_currency, transaction_date, args=None):
    """
    Smart provider that routes to different sources based on context
    """
    # Same currency check
    if from_currency == to_currency:
        return 1.0

    # Get company from current context
    company = frappe.defaults.get_user_default("Company")

    # Check if company is in a specific country
    if company:
        country = frappe.get_cached_value("Company", company, "country")

        # Use regional API for local companies
        if country == "Pakistan" and "PKR" in [from_currency, to_currency]:
            return get_sbp_rate(from_currency, to_currency, transaction_date)

        elif country == "India" and "INR" in [from_currency, to_currency]:
            return get_rbi_rate(from_currency, to_currency, transaction_date)

    # Fall back to international API
    return get_international_rate(from_currency, to_currency, transaction_date)
```

## Testing Your Provider

### 1. Verify Registration

```python
import frappe

# Check if your provider is registered
providers = frappe.get_hooks("currency_exchange_provider")
print(f"Registered providers: {providers}")
```

### 2. Test Exchange Rate Fetch

```python
# Test your provider directly
from your_app.exchange_rates import get_custom_exchange_rate

rate = get_custom_exchange_rate("USD", "PKR", "2026-02-10")
print(f"USD to PKR rate: {rate}")
```

### 3. Test with Invoice Ninja Integration

Create a test invoice in Invoice Ninja with multi-currency and sync it. Check the logs:

```python
# Check the frappe logs
frappe.logger().info("Check for: 'Using custom exchange rate provider'")
```

## Benefits

### For Invoice Ninja Integration Users

- **Automatic Detection**: No configuration needed - works automatically if provider is installed
- **Transparent**: Same interface whether using custom or standard provider
- **Reliable**: Falls back gracefully if custom provider fails

### For Custom Provider Developers

- **Standard Interface**: Follow ERPNext's standard function signature
- **Flexible**: Implement any logic you need
- **Isolated**: Your code lives in your app, not in invoice_ninja_integration

### For Open Source Community

- **No Vendor Lock-in**: Invoice Ninja Integration doesn't depend on proprietary apps
- **Extensible**: Anyone can create custom providers
- **Clean Code**: No hardcoded dependencies or conditional imports

## Troubleshooting

### Provider Not Being Used

**Check 1**: Verify provider is registered in hooks

```python
import frappe
providers = frappe.get_hooks("currency_exchange_provider")
print(providers)  # Should show your provider path
```

**Check 2**: Verify function path is correct

```python
import frappe
func = frappe.get_attr("your_app.path.to.function")
print(func)  # Should return your function
```

**Check 3**: Check for import errors

```bash
bench console
>>> from your_app.exchange_rates import get_custom_exchange_rate
```

### Provider Fails Silently

The system will fall back to Invoice Ninja's provided rate if your provider:
- Returns 0 or None
- Raises an exception
- Takes too long to respond

Check logs:
```python
# View error logs
frappe.get_doc("Error Log", {"error": ["like", "%exchange rate%"]})
```

## Multiple Providers

If multiple apps register `currency_exchange_provider`, the **first registered provider wins**. This is determined by app installation order in `apps.txt`.

To control priority, ensure your app is listed appropriately in the site's `apps.txt`.

## Migration from Hardcoded Dependencies

If you previously had hardcoded imports like:

```python
# OLD (Hardcoded)
from some_private_app.rates import get_rate
rate = get_rate(from_currency, to_currency, date)
```

Migrate to:

```python
# NEW (Hook-based)
from invoice_ninja_integration.utils.field_mapper import FieldMapper

rate_func = FieldMapper.get_exchange_rate_provider()
rate = rate_func(from_currency, to_currency, date, None)
```

Or even better, use the existing `get_conversion_rate_for_transaction()` method which handles all this for you!

## API Reference

### FieldMapper.get_exchange_rate_provider()

```python
@staticmethod
def get_exchange_rate_provider() -> callable:
    """
    Get the best available exchange rate provider

    Returns:
        callable: Function with signature
                  get_exchange_rate(from_currency, to_currency, transaction_date, args=None)
    """
```

### FieldMapper.get_conversion_rate_for_transaction()

```python
@staticmethod
def get_conversion_rate_for_transaction(
    invoice_currency: str,
    company_currency: str,
    posting_date: str,
    in_exchange_rate: float = None
) -> float:
    """
    Get conversion rate using the best available provider

    Automatically:
    - Detects custom providers via hooks
    - Falls back to Invoice Ninja rate if provider fails
    - Falls back to 1.0 as last resort
    - Logs all operations

    Args:
        invoice_currency: Currency from Invoice Ninja
        company_currency: ERPNext company's currency
        posting_date: Transaction date
        in_exchange_rate: Invoice Ninja's rate (fallback)

    Returns:
        Conversion rate as float
    """
```

## Support

For issues related to:
- **Invoice Ninja Integration**: Create an issue in the invoice_ninja_integration repository
- **Custom Provider**: Contact your custom provider's maintainer
- **ERPNext Core**: Refer to ERPNext documentation

## License

This plugin system is part of Invoice Ninja Integration and follows the same license.
