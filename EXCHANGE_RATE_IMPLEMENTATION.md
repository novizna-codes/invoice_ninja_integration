# Automatic Exchange Rate Fetching Implementation

## Overview
Implemented automatic currency exchange rate fetching for Invoice Ninja invoices and quotations. The system now intelligently retrieves exchange rates using ERPNext's built-in Currency Exchange system with API fallback support.

## What Was Changed

### 1. New Helper Method: `get_conversion_rate_for_transaction()`
**Location:** `field_mapper.py`

**Purpose:** Centralized method for getting exchange rates with multiple fallback strategies.

**Logic Flow:**
1. ✅ **Check if currencies match** - Returns 1.0 if same currency
2. ✅ **Query Currency Exchange table** - Looks for existing rate on posting date
3. ✅ **API Fallback** - Automatically fetches from API (frankfurter.dev by default) if not found
4. ✅ **Auto-create record** - Creates Currency Exchange record when fetched from API
5. ✅ **Invoice Ninja rate fallback** - Uses IN's rate if API is disabled or fails
6. ✅ **Last resort** - Defaults to 1.0 with error logging

### 2. Updated Invoice Mapping
**Method:** `map_invoice_from_invoice_ninja()`

**Changes:**
- Gets company's default currency
- Calls `get_conversion_rate_for_transaction()` with:
  - Invoice currency from Invoice Ninja
  - Company currency from ERPNext
  - Posting date from invoice
  - Invoice Ninja's exchange rate as fallback
- Sets `conversion_rate` field with the fetched rate

### 3. Updated Quotation Mapping
**Method:** `map_quote_from_invoice_ninja()`

**Changes:**
- Same logic as invoices
- Uses transaction_date instead of posting_date
- Applies to quotations/quotes from Invoice Ninja

## Benefits

✅ **Automatic API Fetching** - No manual Currency Exchange record creation needed
✅ **Always Up-to-Date** - Gets latest rates for posting date
✅ **Respects Configuration** - Uses Currency Exchange Settings (disabled state, provider choice)
✅ **Multiple Fallbacks** - IN rate → API → Default with comprehensive logging
✅ **Audit Trail** - Creates Currency Exchange records for compliance
✅ **Works Offline** - Falls back gracefully if API unavailable
✅ **Same Currency Optimization** - Skip conversion when currencies match

## Configuration

### Currency Exchange Settings
Navigate to: **Setup > Currency Exchange Settings**

**Available API Providers:**
- frankfurter.dev (default, free)
- exchangerate.host
- Custom providers

**Settings:**
- Enable/disable automatic fetching
- Choose API provider
- Set base currency

### How It Works

**Scenario 1: Currency Exchange Record Exists**
```
Invoice Currency: EUR
Company Currency: USD
Posting Date: 2026-02-05

Result: Uses existing rate from Currency Exchange table
```

**Scenario 2: No Record, API Enabled**
```
Invoice Currency: GBP
Company Currency: USD
Posting Date: 2026-02-05

Process:
1. Checks Currency Exchange table ❌
2. Calls frankfurter.dev API ✅
3. Gets rate: 1.27
4. Creates Currency Exchange record
5. Uses rate: 1.27
```

**Scenario 3: API Disabled/Failed**
```
Invoice Currency: CAD
Company Currency: USD
Posting Date: 2026-02-05
Invoice Ninja Rate: 0.75

Process:
1. Checks Currency Exchange table ❌
2. API call fails/disabled ❌
3. Falls back to IN rate: 0.75 ✅
4. Logs warning
```

**Scenario 4: No Rate Available**
```
Invoice Currency: XYZ
Company Currency: USD
Posting Date: 2026-02-05

Process:
1. Checks Currency Exchange table ❌
2. API call fails ❌
3. No IN rate provided ❌
4. Uses default: 1.0 ⚠️
5. Logs error for manual review
```

## Logging

The system provides comprehensive logging:

### Info Logs
```python
frappe.logger().info(
    f"Using exchange rate {rate} for {from_currency} to {to_currency} on {date}"
)
```

### Warning Logs
```python
frappe.logger().warning(
    f"ERPNext exchange rate API unavailable. Using Invoice Ninja rate {rate}"
)
```

### Error Logs
```python
frappe.logger().error(
    f"No exchange rate found. Defaulting to 1.0. Please create record manually."
)
```

## Testing Scenarios

### Test 1: Same Currency (No Conversion Needed)
- Invoice Currency: USD
- Company Currency: USD
- Expected Result: conversion_rate = 1.0

### Test 2: Different Currency with Existing Record
- Invoice Currency: EUR
- Company Currency: USD
- Existing Rate: 1.08
- Expected Result: conversion_rate = 1.08

### Test 3: Different Currency, API Fetch
- Invoice Currency: GBP
- Company Currency: USD
- No existing record
- API returns: 1.27
- Expected Result: conversion_rate = 1.27, new Currency Exchange record created

### Test 4: API Disabled, Use IN Rate
- Invoice Currency: CAD
- Company Currency: USD
- API disabled
- IN provides: 0.74
- Expected Result: conversion_rate = 0.74, warning logged

### Test 5: No Rate Available
- Invoice Currency: Unknown
- Company Currency: USD
- No API, no IN rate
- Expected Result: conversion_rate = 1.0, error logged

## Monitoring

### Check Currency Exchange Records
```sql
SELECT * FROM `tabCurrency Exchange`
WHERE from_currency = 'EUR'
AND to_currency = 'USD'
ORDER BY date DESC;
```

### Review Error Logs
Navigate to: **Setup > Error Log**
Filter by: "Exchange Rate Fetch Error"

### Verify Conversion Rates
Check Sales Invoice:
- Open any synced invoice
- Go to "Currency and Price List" section
- Verify `Exchange Rate` field

## Troubleshooting

### Issue: Rate always defaults to 1.0
**Solution:**
1. Check Currency Exchange Settings is not disabled
2. Verify API provider is configured correctly
3. Check network connectivity to API
4. Review Error Log for specific failures

### Issue: Wrong exchange rate used
**Solution:**
1. Check Currency Exchange table for date
2. Verify posting date is correct
3. Manually create Currency Exchange record if needed
4. Re-sync invoice

### Issue: API errors in logs
**Solution:**
1. Verify API provider URL in settings
2. Check firewall/proxy settings
3. Consider switching to different provider
4. Fall back to manual Currency Exchange records

## Future Enhancements

- [ ] Support for mid-market rates vs buy/sell rates
- [ ] Historical rate caching for performance
- [ ] Bulk update of missing rates
- [ ] Custom rate adjustment factors
- [ ] Multi-currency reporting integration

## API Providers

### Frankfurter.dev (Default)
- **URL:** https://frankfurter.app
- **Free:** Yes
- **Rate Limit:** None
- **Historical Data:** Yes
- **Currencies:** 30+ major currencies

### Exchangerate.host
- **URL:** https://api.exchangerate.host
- **Free:** Yes (with limits)
- **Rate Limit:** 1000/month free
- **Historical Data:** Yes
- **Currencies:** 150+ currencies

## Related Documentation
- [ERPNext Currency Exchange](https://docs.erpnext.com/docs/user/manual/en/accounts/multi-currency-accounting)
- [Invoice Ninja API](https://docs.invoiceninja.com)
- [Frankfurter API](https://www.frankfurter.app/docs/)
