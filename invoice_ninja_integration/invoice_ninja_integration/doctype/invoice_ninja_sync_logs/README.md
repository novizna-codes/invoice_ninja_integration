# Invoice Ninja Sync Logs

Tracks all synchronization operations between Invoice Ninja and ERPNext.

## Fields

- **Sync Type**: Manual, Automatic, Webhook, or Scheduled
- **Sync Direction**: Invoice Ninja to ERPNext, ERPNext to Invoice Ninja, or Bidirectional
- **Record Type**: Customer, Invoice, Quotation, Item, Payment, or File
- **Status**: Success, Failed, Partial, Skipped, or In Progress
- **Record Details**: ID, Name, and associated Invoice Ninja/ERPNext IDs
- **Timing**: Sync timestamp and duration
- **Messages**: Success message or error details

## Features

- **Automatic Logging**: All sync operations are automatically logged
- **Retry Failed Syncs**: Retry button available for failed sync operations
- **Dashboard Integration**: Statistics and recent logs displayed on sync dashboard
- **Cleanup**: Automatic cleanup of old logs (configurable retention period)
