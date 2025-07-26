# Copyright (c) 2025, Novizna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime

class InvoiceNinjaSyncLogs(Document):
	def before_insert(self):
		if not self.sync_timestamp:
			self.sync_timestamp = frappe.utils.now()

	@staticmethod
	def create_log(sync_type, sync_direction, record_type, status="In Progress",
				   record_id=None, record_name=None, message=None, error_details=None,
				   invoice_ninja_id=None, erpnext_id=None, webhook_triggered=False, job_id=None):
		"""Create a new sync log entry"""
		try:
			log = frappe.get_doc({
				"doctype": "Invoice Ninja Sync Logs",
				"sync_type": sync_type,
				"sync_direction": sync_direction,
				"record_type": record_type,
				"record_id": record_id,
				"record_name": record_name,
				"status": status,
				"message": message,
				"error_details": error_details,
				"sync_timestamp": frappe.utils.now(),
				"invoice_ninja_id": invoice_ninja_id,
				"erpnext_id": erpnext_id,
				"webhook_triggered": webhook_triggered,
				"job_id": job_id
			})
			log.insert(ignore_permissions=True)
			frappe.db.commit()
			return log.name
		except Exception as e:
			frappe.log_error(f"Error creating sync log: {str(e)}", "Sync Log Creation Error")
			return None

	@staticmethod
	def update_log(log_name, status=None, message=None, error_details=None, duration=None):
		"""Update an existing sync log"""
		try:
			if not frappe.db.exists("Invoice Ninja Sync Logs", log_name):
				return False

			log = frappe.get_doc("Invoice Ninja Sync Logs", log_name)

			if status:
				log.status = status
			if message:
				log.message = message
			if error_details:
				log.error_details = error_details
			if duration:
				log.duration = duration

			log.save(ignore_permissions=True)
			frappe.db.commit()
			return True
		except Exception as e:
			frappe.log_error(f"Error updating sync log {log_name}: {str(e)}", "Sync Log Update Error")
			return False

	@staticmethod
	def get_recent_logs(limit=50, filters=None):
		"""Get recent sync logs with optional filters"""
		try:
			filter_conditions = filters or {}

			logs = frappe.get_list(
				"Invoice Ninja Sync Logs",
				filters=filter_conditions,
				fields=["name", "sync_type", "sync_direction", "record_type", "record_name",
						"status", "message", "sync_timestamp", "duration", "webhook_triggered"],
				order_by="sync_timestamp desc",
				limit=limit
			)

			return logs
		except Exception as e:
			frappe.log_error(f"Error fetching sync logs: {str(e)}", "Sync Log Fetch Error")
			return []

	@staticmethod
	def get_sync_statistics(days=7):
		"""Get sync statistics for the dashboard"""
		try:
			from datetime import datetime, timedelta

			start_date = datetime.now() - timedelta(days=days)

			# Get successful syncs by type
			successful_stats = frappe.db.sql("""
				SELECT
					record_type,
					sync_direction,
					COUNT(*) as count
				FROM `tabInvoice Ninja Sync Logs`
				WHERE status = 'Success'
					AND sync_timestamp >= %s
				GROUP BY record_type, sync_direction
			""", [start_date], as_dict=1)

			# Get failed syncs
			failed_stats = frappe.db.sql("""
				SELECT
					record_type,
					COUNT(*) as count
				FROM `tabInvoice Ninja Sync Logs`
				WHERE status = 'Failed'
					AND sync_timestamp >= %s
				GROUP BY record_type
			""", [start_date], as_dict=1)

			# Get overall counts
			total_stats = frappe.db.sql("""
				SELECT
					status,
					COUNT(*) as count
				FROM `tabInvoice Ninja Sync Logs`
				WHERE sync_timestamp >= %s
				GROUP BY status
			""", [start_date], as_dict=1)

			return {
				"successful_syncs": successful_stats,
				"failed_syncs": failed_stats,
				"total_stats": total_stats,
				"period": f"Last {days} days"
			}
		except Exception as e:
			frappe.log_error(f"Error getting sync statistics: {str(e)}", "Sync Statistics Error")
			return {
				"successful_syncs": [],
				"failed_syncs": [],
				"total_stats": [],
				"period": f"Last {days} days"
			}

	@staticmethod
	def cleanup_old_logs(days=30):
		"""Clean up old sync logs"""
		try:
			from datetime import datetime, timedelta

			cutoff_date = datetime.now() - timedelta(days=days)

			# Delete old logs
			frappe.db.sql("""
				DELETE FROM `tabInvoice Ninja Sync Logs`
				WHERE sync_timestamp < %s
			""", [cutoff_date])

			frappe.db.commit()
			return True
		except Exception as e:
			frappe.log_error(f"Error cleaning up sync logs: {str(e)}", "Sync Log Cleanup Error")
			return False
