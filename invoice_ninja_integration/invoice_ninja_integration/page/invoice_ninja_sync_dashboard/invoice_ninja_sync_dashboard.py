import frappe
from frappe import _
import json
from datetime import datetime, timedelta

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    return context

@frappe.whitelist()
def get_sync_dashboard_data():
    """Get comprehensive sync dashboard data"""
    try:
        # Get settings
        settings = frappe.get_single("Invoice Ninja Settings")
        
        # Get recent sync logs from background jobs
        sync_logs = get_sync_logs()
        
        # Get sync statistics
        sync_stats = get_sync_statistics()
        
        # Get current sync configuration
        sync_config = get_sync_configuration()
        
        dashboard_data = {
            "sync_enabled": settings.enabled,
            "connection_status": settings.connection_status or "Not Tested",
            "last_sync_time": settings.last_sync_time,
            "webhook_enabled": settings.enable_webhooks,
            "webhook_url": settings.webhook_url,
            "sync_logs": sync_logs,
            "sync_stats": sync_stats,
            "sync_config": sync_config
        }
        
        return dashboard_data
        
    except Exception as e:
        frappe.log_error(f"Dashboard data error: {str(e)}", "Sync Dashboard Error")
        return {"error": str(e)}

def get_sync_logs():
    """Get recent sync job logs"""
    # Get background job logs
    job_logs = frappe.get_list(
        "RQ Job",
        filters={
            "job_name": ["like", "%invoice_ninja%"]
        },
        fields=["name", "queue", "status", "creation", "started_at", "ended_at", "exc_info"],
        order_by="creation desc",
        limit=50
    )
    
    # Get error logs
    error_logs = frappe.get_list(
        "Error Log",
        filters={
            "error": ["like", "%invoice_ninja%"]
        },
        fields=["name", "creation", "error", "method"],
        order_by="creation desc",
        limit=20
    )
    
    return {
        "job_logs": job_logs,
        "error_logs": error_logs
    }

def get_sync_statistics():
    """Get sync statistics for the dashboard"""
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Count successful syncs by type (from background jobs)
    successful_jobs = frappe.db.sql("""
        SELECT 
            CASE 
                WHEN job_name LIKE '%customer%' THEN 'Customer'
                WHEN job_name LIKE '%invoice%' THEN 'Invoice'
                WHEN job_name LIKE '%quote%' THEN 'Quotation'
                WHEN job_name LIKE '%product%' OR job_name LIKE '%item%' THEN 'Product'
                WHEN job_name LIKE '%payment%' THEN 'Payment'
                ELSE 'Other'
            END as sync_type,
            COUNT(*) as count
        FROM `tabRQ Job`
        WHERE job_name LIKE '%invoice_ninja%' 
            AND status = 'finished'
            AND DATE(creation) >= %s
        GROUP BY sync_type
    """, [week_ago], as_dict=1)
    
    # Count failed syncs
    failed_jobs = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabRQ Job`
        WHERE job_name LIKE '%invoice_ninja%' 
            AND status = 'failed'
            AND DATE(creation) >= %s
    """, [week_ago], as_dict=1)
    
    return {
        "successful_syncs": successful_jobs,
        "failed_syncs": failed_jobs[0]["count"] if failed_jobs else 0,
        "period": "Last 7 days"
    }

def get_sync_configuration():
    """Get current sync configuration summary"""
    settings = frappe.get_single("Invoice Ninja Settings")
    
    config = {
        "customer_sync": {
            "enabled": settings.enable_customer_sync,
            "direction": settings.get("customer_sync_direction", "Invoice Ninja to ERPNext")
        },
        "invoice_sync": {
            "enabled": settings.enable_invoice_sync,
            "direction": settings.get("invoice_sync_direction", "Invoice Ninja to ERPNext")
        },
        "quote_sync": {
            "enabled": settings.enable_quote_sync,
            "direction": settings.get("quote_sync_direction", "Invoice Ninja to ERPNext")
        },
        "product_sync": {
            "enabled": settings.enable_product_sync,
            "direction": settings.get("product_sync_direction", "Invoice Ninja to ERPNext")
        },
        "payment_sync": {
            "enabled": settings.enable_payment_sync,
            "direction": settings.get("payment_sync_direction", "Invoice Ninja to ERPNext")
        }
    }
    
    return config

@frappe.whitelist()
def manual_sync(sync_type, sync_direction, record_id=None):
    """Trigger manual sync"""
    try:
        # Validate inputs
        valid_types = ['Customer', 'Invoice', 'Quote', 'Product', 'Payment']
        valid_directions = ['Invoice Ninja to ERPNext', 'ERPNext to Invoice Ninja']
        
        if sync_type not in valid_types:
            return {"success": False, "error": "Invalid sync type"}
            
        if sync_direction not in valid_directions:
            return {"success": False, "error": "Invalid sync direction"}
        
        # Check if sync is enabled
        settings = frappe.get_single("Invoice Ninja Settings")
        if not settings.enabled:
            return {"success": False, "error": "Invoice Ninja integration is disabled"}
        
        # Enqueue the sync job
        job_name = f"manual_sync_{sync_type.lower()}_{sync_direction.replace(' ', '_').lower()}"
        
        if sync_direction == "ERPNext to Invoice Ninja":
            # Sync from ERPNext to Invoice Ninja
            frappe.enqueue(
                method="invoice_ninja_integration.tasks.sync_erpnext_to_invoice_ninja",
                queue="default",
                sync_type=sync_type,
                record_id=record_id,
                job_name=job_name,
                timeout=600
            )
        else:
            # Sync from Invoice Ninja to ERPNext
            frappe.enqueue(
                method="invoice_ninja_integration.tasks.sync_invoice_ninja_to_erpnext",
                queue="default",
                sync_type=sync_type,
                record_id=record_id,
                job_name=job_name,
                timeout=600
            )
        
        return {
            "success": True,
            "message": f"Manual sync for {sync_type} started successfully",
            "job_name": job_name
        }
        
    except Exception as e:
        frappe.log_error(f"Manual sync error: {str(e)}", "Manual Sync Error")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def test_connection():
    """Test connection to Invoice Ninja"""
    try:
        settings = frappe.get_single("Invoice Ninja Settings")
        result = settings.test_connection()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def toggle_auto_sync(enable=True):
    """Enable or disable automatic sync"""
    try:
        settings = frappe.get_single("Invoice Ninja Settings")
        settings.enabled = int(enable)
        settings.save()
        
        action = "enabled" if enable else "disabled"
        return {
            "success": True,
            "message": f"Automatic sync has been {action}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def clear_sync_logs():
    """Clear old sync logs"""
    try:
        # Delete RQ Jobs older than 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        frappe.db.sql("""
            DELETE FROM `tabRQ Job`
            WHERE job_name LIKE '%invoice_ninja%' 
                AND creation < %s
        """, [thirty_days_ago])
        
        # Delete Error Logs older than 30 days
        frappe.db.sql("""
            DELETE FROM `tabError Log`
            WHERE error LIKE '%invoice_ninja%' 
                AND creation < %s
        """, [thirty_days_ago])
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Old sync logs have been cleared"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
