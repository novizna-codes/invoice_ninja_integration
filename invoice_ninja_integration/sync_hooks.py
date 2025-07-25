import frappe
from invoice_ninja_integration.utils.sync_manager import SyncManager

def on_customer_save(doc, method):
    """Handle Customer save events for sync to Invoice Ninja"""
    # Skip if document is being created by sync process
    if hasattr(doc, '_skip_invoice_ninja_sync'):
        return

    sync_manager = SyncManager()

    # Only sync if ERPNext to Invoice Ninja sync is enabled
    if sync_manager.should_sync_from_erpnext("Customer"):
        # Run sync in background to avoid blocking the user
        frappe.enqueue(
            method=sync_manager.sync_document_to_invoice_ninja,
            queue='default',
            doc=doc,
            timeout=300,
            is_async=True
        )

def on_invoice_save(doc, method):
    """Handle Sales Invoice save events for sync to Invoice Ninja"""
    if hasattr(doc, '_skip_invoice_ninja_sync'):
        return

    sync_manager = SyncManager()

    if sync_manager.should_sync_from_erpnext("Sales Invoice"):
        frappe.enqueue(
            method=sync_manager.sync_document_to_invoice_ninja,
            queue='default',
            doc=doc,
            timeout=300,
            is_async=True
        )

def on_quotation_save(doc, method):
    """Handle Quotation save events for sync to Invoice Ninja"""
    if hasattr(doc, '_skip_invoice_ninja_sync'):
        return

    sync_manager = SyncManager()

    if sync_manager.should_sync_from_erpnext("Quotation"):
        frappe.enqueue(
            method=sync_manager.sync_document_to_invoice_ninja,
            queue='default',
            doc=doc,
            timeout=300,
            is_async=True
        )

def on_item_save(doc, method):
    """Handle Item save events for sync to Invoice Ninja"""
    if hasattr(doc, '_skip_invoice_ninja_sync'):
        return

    sync_manager = SyncManager()

    if sync_manager.should_sync_from_erpnext("Item"):
        frappe.enqueue(
            method=sync_manager.sync_document_to_invoice_ninja,
            queue='default',
            doc=doc,
            timeout=300,
            is_async=True
        )

def on_payment_save(doc, method):
    """Handle Payment Entry save events for sync to Invoice Ninja"""
    if hasattr(doc, '_skip_invoice_ninja_sync'):
        return

    sync_manager = SyncManager()

    if sync_manager.should_sync_from_erpnext("Payment Entry"):
        frappe.enqueue(
            method=sync_manager.sync_document_to_invoice_ninja,
            queue='default',
            doc=doc,
            timeout=300,
            is_async=True
        )
