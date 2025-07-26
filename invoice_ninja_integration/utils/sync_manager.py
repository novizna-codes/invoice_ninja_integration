import frappe
from invoice_ninja_integration.utils.invoice_ninja_client import InvoiceNinjaClient
from invoice_ninja_integration.utils.field_mapper import FieldMapper

class SyncManager:
    """
    Manages bidirectional synchronization between Invoice Ninja and ERPNext
    based on user-configured sync directions.
    """

    def __init__(self):
        self.settings = frappe.get_single("Invoice Ninja Settings")
        self.client = InvoiceNinjaClient()
        self.mapper = FieldMapper()

    def get_sync_direction(self, doc_type):
        """Get sync direction for a specific document type"""
        field_map = {
            "Customer": "customer_sync_direction",
            "Sales Invoice": "invoice_sync_direction",
            "Quotation": "quote_sync_direction",
            "Item": "product_sync_direction",
            "Payment Entry": "payment_sync_direction"
        }

        field_name = field_map.get(doc_type)
        if not field_name:
            return None

        return self.settings.get(field_name, "Invoice Ninja to ERPNext")

    def should_sync_from_erpnext(self, doc_type):
        """Check if document should be synced from ERPNext to Invoice Ninja"""
        direction = self.get_sync_direction(doc_type)
        return direction in ["ERPNext to Invoice Ninja", "Bidirectional"]

    def should_sync_from_invoice_ninja(self, doc_type):
        """Check if document should be synced from Invoice Ninja to ERPNext"""
        direction = self.get_sync_direction(doc_type)
        return direction in ["Invoice Ninja to ERPNext", "Bidirectional"]

    def is_sync_enabled(self, doc_type):
        """Check if sync is enabled for a document type"""
        enable_map = {
            "Customer": "enable_customer_sync",
            "Sales Invoice": "enable_invoice_sync",
            "Quotation": "enable_quote_sync",
            "Item": "enable_product_sync",
            "Payment Entry": "enable_payment_sync"
        }

        field_name = enable_map.get(doc_type)
        if not field_name:
            return False

        return self.settings.get(field_name, 0)

    def sync_document_to_invoice_ninja(self, doc):
        """
        Sync ERPNext document to Invoice Ninja based on configuration
        """
        if not self.is_sync_enabled(doc.doctype):
            frappe.logger().info(f"Sync disabled for {doc.doctype}")
            return

        if not self.should_sync_from_erpnext(doc.doctype):
            frappe.logger().info(f"ERPNext to Invoice Ninja sync disabled for {doc.doctype}")
            return

        try:
            if doc.doctype == "Customer":
                return self._sync_customer_to_invoice_ninja(doc)
            elif doc.doctype == "Sales Invoice":
                return self._sync_invoice_to_invoice_ninja(doc)
            elif doc.doctype == "Quotation":
                return self._sync_quote_to_invoice_ninja(doc)
            elif doc.doctype == "Item":
                return self._sync_product_to_invoice_ninja(doc)
            elif doc.doctype == "Payment Entry":
                return self._sync_payment_to_invoice_ninja(doc)

        except Exception as e:
            frappe.logger().error(f"Error syncing {doc.doctype} {doc.name} to Invoice Ninja: {str(e)}")
            self._log_sync_error(doc, "ERPNext to Invoice Ninja", str(e))

    def sync_document_from_invoice_ninja(self, invoice_ninja_data, doc_type):
        """
        Sync Invoice Ninja data to ERPNext based on configuration
        """
        if not self.is_sync_enabled(doc_type):
            frappe.logger().info(f"Sync disabled for {doc_type}")
            return

        if not self.should_sync_from_invoice_ninja(doc_type):
            frappe.logger().info(f"Invoice Ninja to ERPNext sync disabled for {doc_type}")
            return

        try:
            if doc_type == "Customer":
                return self._sync_customer_from_invoice_ninja(invoice_ninja_data)
            elif doc_type == "Sales Invoice":
                return self._sync_invoice_from_invoice_ninja(invoice_ninja_data)
            elif doc_type == "Quotation":
                return self._sync_quote_from_invoice_ninja(invoice_ninja_data)
            elif doc_type == "Item":
                return self._sync_product_from_invoice_ninja(invoice_ninja_data)
            elif doc_type == "Payment Entry":
                return self._sync_payment_from_invoice_ninja(invoice_ninja_data)

        except Exception as e:
            frappe.logger().error(f"Error syncing {doc_type} from Invoice Ninja: {str(e)}")
            self._log_sync_error(None, "Invoice Ninja to ERPNext", str(e), invoice_ninja_data)

    def _sync_customer_to_invoice_ninja(self, customer):
        """Sync ERPNext Customer to Invoice Ninja"""
        # Check if customer already exists in Invoice Ninja
        in_customer_id = customer.get("custom_invoice_ninja_id")

        # Map ERPNext customer to Invoice Ninja format
        customer_data = self.mapper.map_customer_to_invoice_ninja(customer)

        if in_customer_id:
            # Update existing customer
            result = self.client.update_customer(in_customer_id, customer_data)
        else:
            # Create new customer
            result = self.client.create_customer(customer_data)
            if result.get("id"):
                # Update ERPNext with Invoice Ninja ID
                frappe.db.set_value("Customer", customer.name, "custom_invoice_ninja_id", result["id"])
                frappe.db.commit()

        return result

    def _sync_customer_from_invoice_ninja(self, customer_data):
        """Sync Invoice Ninja Customer to ERPNext"""
        # Check if customer already exists
        existing_customer = frappe.db.get_value(
            "Customer",
            {"custom_invoice_ninja_id": customer_data.get("id")},
            "name"
        )

        # Map Invoice Ninja customer to ERPNext format
        erpnext_data = self.mapper.map_customer_from_invoice_ninja(customer_data)

        if existing_customer:
            # Update existing customer
            customer_doc = frappe.get_doc("Customer", existing_customer)
            customer_doc.update(erpnext_data)
            customer_doc.save()
        else:
            # Create new customer
            customer_doc = frappe.new_doc("Customer")
            customer_doc.update(erpnext_data)
            customer_doc.custom_invoice_ninja_id = customer_data.get("id")
            customer_doc.insert()

        return customer_doc

    def _sync_invoice_to_invoice_ninja(self, invoice):
        """Sync ERPNext Sales Invoice to Invoice Ninja"""
        # Implementation for invoice sync to Invoice Ninja
        invoice_data = self.mapper.map_invoice_to_invoice_ninja(invoice)

        in_invoice_id = invoice.get("custom_invoice_ninja_id")
        if in_invoice_id:
            result = self.client.update_invoice(in_invoice_id, invoice_data)
        else:
            result = self.client.create_invoice(invoice_data)
            if result.get("id"):
                frappe.db.set_value("Sales Invoice", invoice.name, "custom_invoice_ninja_id", result["id"])
                frappe.db.commit()

        return result

    def _sync_invoice_from_invoice_ninja(self, invoice_data):
        """Sync Invoice Ninja Invoice to ERPNext"""
        # Implementation for invoice sync from Invoice Ninja
        existing_invoice = frappe.db.get_value(
            "Sales Invoice",
            {"custom_invoice_ninja_id": invoice_data.get("id")},
            "name"
        )

        erpnext_data = self.mapper.map_invoice_from_invoice_ninja(invoice_data)

        if existing_invoice:
            invoice_doc = frappe.get_doc("Sales Invoice", existing_invoice)
            invoice_doc.update(erpnext_data)
            invoice_doc.save()
        else:
            invoice_doc = frappe.new_doc("Sales Invoice")
            invoice_doc.update(erpnext_data)
            invoice_doc.custom_invoice_ninja_id = invoice_data.get("id")
            invoice_doc.insert()

        return invoice_doc

    def _sync_quote_to_invoice_ninja(self, quote):
        """Sync ERPNext Quotation to Invoice Ninja"""
        quote_data = self.mapper.map_quote_to_invoice_ninja(quote)

        in_quote_id = quote.get("custom_invoice_ninja_id")
        if in_quote_id:
            result = self.client.update_quote(in_quote_id, quote_data)
        else:
            result = self.client.create_quote(quote_data)
            if result.get("id"):
                frappe.db.set_value("Quotation", quote.name, "custom_invoice_ninja_id", result["id"])
                frappe.db.commit()

        return result

    def _sync_quote_from_invoice_ninja(self, quote_data):
        """Sync Invoice Ninja Quote to ERPNext"""
        existing_quote = frappe.db.get_value(
            "Quotation",
            {"custom_invoice_ninja_id": quote_data.get("id")},
            "name"
        )

        erpnext_data = self.mapper.map_quote_from_invoice_ninja(quote_data)

        if existing_quote:
            quote_doc = frappe.get_doc("Quotation", existing_quote)
            quote_doc.update(erpnext_data)
            quote_doc.save()
        else:
            quote_doc = frappe.new_doc("Quotation")
            quote_doc.update(erpnext_data)
            quote_doc.custom_invoice_ninja_id = quote_data.get("id")
            quote_doc.insert()

        return quote_doc

    def _sync_product_to_invoice_ninja(self, item):
        """Sync ERPNext Item to Invoice Ninja"""
        product_data = self.mapper.map_product_to_invoice_ninja(item)

        in_product_id = item.get("custom_invoice_ninja_id")
        if in_product_id:
            result = self.client.update_product(in_product_id, product_data)
        else:
            result = self.client.create_product(product_data)
            if result.get("id"):
                frappe.db.set_value("Item", item.name, "custom_invoice_ninja_id", result["id"])
                frappe.db.commit()

        return result

    def _sync_product_from_invoice_ninja(self, product_data):
        """Sync Invoice Ninja Product to ERPNext"""
        existing_item = frappe.db.get_value(
            "Item",
            {"custom_invoice_ninja_id": product_data.get("id")},
            "name"
        )

        erpnext_data = self.mapper.map_product_from_invoice_ninja(product_data)

        if existing_item:
            item_doc = frappe.get_doc("Item", existing_item)
            item_doc.update(erpnext_data)
            item_doc.save()
        else:
            item_doc = frappe.new_doc("Item")
            item_doc.update(erpnext_data)
            item_doc.custom_invoice_ninja_id = product_data.get("id")
            item_doc.insert()

        return item_doc

    def _sync_payment_to_invoice_ninja(self, payment):
        """Sync ERPNext Payment Entry to Invoice Ninja"""
        payment_data = self.mapper.map_payment_to_invoice_ninja(payment)

        in_payment_id = payment.get("custom_invoice_ninja_id")
        if in_payment_id:
            result = self.client.update_payment(in_payment_id, payment_data)
        else:
            result = self.client.create_payment(payment_data)
            if result.get("id"):
                frappe.db.set_value("Payment Entry", payment.name, "custom_invoice_ninja_id", result["id"])
                frappe.db.commit()

        return result

    def _sync_payment_from_invoice_ninja(self, payment_data):
        """Sync Invoice Ninja Payment to ERPNext"""
        existing_payment = frappe.db.get_value(
            "Payment Entry",
            {"custom_invoice_ninja_id": payment_data.get("id")},
            "name"
        )

        erpnext_data = self.mapper.map_payment_from_invoice_ninja(payment_data)

        if existing_payment:
            payment_doc = frappe.get_doc("Payment Entry", existing_payment)
            payment_doc.update(erpnext_data)
            payment_doc.save()
        else:
            payment_doc = frappe.new_doc("Payment Entry")
            payment_doc.update(erpnext_data)
            payment_doc.custom_invoice_ninja_id = payment_data.get("id")
            payment_doc.insert()

        return payment_doc

    def _log_sync_error(self, doc, direction, error_message, invoice_ninja_data=None):
        """Log synchronization errors for troubleshooting"""
        error_log = frappe.new_doc("Error Log")
        error_log.method = f"invoice_ninja_integration.sync_manager.{direction.lower().replace(' ', '_')}"
        error_log.error = error_message

        if doc:
            error_log.reference_doctype = doc.doctype
            error_log.reference_name = doc.name

        error_log.insert(ignore_permissions=True)

        # Send error notification if enabled
        if self.settings.send_error_notifications and self.settings.notification_email:
            self._send_error_notification(doc, direction, error_message, invoice_ninja_data)

    def _send_error_notification(self, doc, direction, error_message, invoice_ninja_data=None):
        """Send error notification email"""
        subject = f"Invoice Ninja Integration Error - {direction}"

        message = f"""
        An error occurred during {direction} synchronization:

        Error: {error_message}

        Document: {doc.doctype if doc else 'Unknown'} - {doc.name if doc else 'N/A'}
        Direction: {direction}
        Time: {frappe.utils.now()}

        Please check the Error Log for more details.
        """

        frappe.sendmail(
            recipients=[self.settings.notification_email],
            subject=subject,
            message=message
        )

    def get_sync_configuration_summary(self):
        """Get a summary of current sync configuration"""
        summary = {
            "enabled_syncs": [],
            "sync_directions": {},
            "potential_issues": []
        }

        doc_types = ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]

        for doc_type in doc_types:
            if self.is_sync_enabled(doc_type):
                direction = self.get_sync_direction(doc_type)
                summary["enabled_syncs"].append(doc_type)
                summary["sync_directions"][doc_type] = direction

                # Check for potential bidirectional loop issues
                if direction == "Bidirectional":
                    summary["potential_issues"].append(
                        f"{doc_type}: Bidirectional sync may cause loops if not configured properly"
                    )

        return summary

    def validate_sync_configuration(self):
        """Validate sync configuration and return warnings/errors"""
        issues = []

        # Check if any sync is enabled but API not configured
        if any(self.is_sync_enabled(dt) for dt in ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]):
            if not self.settings.invoice_ninja_url or not self.settings.api_token:
                issues.append("ERROR: Sync enabled but Invoice Ninja URL or API token not configured")

        # Check webhook configuration for Invoice Ninja → ERPNext sync
        needs_webhooks = False
        for doc_type in ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]:
            if self.is_sync_enabled(doc_type) and self.should_sync_from_invoice_ninja(doc_type):
                needs_webhooks = True
                break

        if needs_webhooks and not self.settings.enable_webhooks:
            issues.append("WARNING: Invoice Ninja to ERPNext sync enabled but webhooks not enabled")

        # Check for all bidirectional syncs (potential loop risk)
        bidirectional_count = 0
        for doc_type in ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]:
            if self.is_sync_enabled(doc_type) and self.get_sync_direction(doc_type) == "Bidirectional":
                bidirectional_count += 1

        if bidirectional_count > 2:
            issues.append("WARNING: Multiple bidirectional syncs enabled - risk of sync loops")

        return issues

    def sync_single_record_from_invoice_ninja(self, sync_type, record_id):
        """Sync a single record from Invoice Ninja to ERPNext"""
        try:
            # Map sync types to Invoice Ninja API endpoints
            endpoint_map = {
                'Customer': 'clients',
                'Invoice': 'invoices',
                'Quote': 'quotes',
                'Product': 'products',
                'Payment': 'payments'
            }

            endpoint = endpoint_map.get(sync_type)
            if not endpoint:
                raise Exception(f"Invalid sync type: {sync_type}")

            # Fetch record from Invoice Ninja
            data = self.client.get(f"{endpoint}/{record_id}")
            if not data:
                raise Exception(f"Record not found in Invoice Ninja: {record_id}")

            # Map to ERPNext doctype
            doctype_map = {
                'Customer': 'Customer',
                'Invoice': 'Sales Invoice',
                'Quote': 'Quotation',
                'Product': 'Item',
                'Payment': 'Payment Entry'
            }

            doc_type = doctype_map[sync_type]
            result = self.sync_document_from_invoice_ninja(data, doc_type)

            return {"synced": 1, "record": result.name if result else None}

        except Exception as e:
            frappe.log_error(f"Single record sync failed: {str(e)}", "Single Record Sync Error")
            raise e

    def sync_all_records_from_invoice_ninja(self, sync_type, limit=100):
        """Sync all records of a type from Invoice Ninja to ERPNext"""
        try:
            # Map sync types to Invoice Ninja API endpoints
            endpoint_map = {
                'Customer': 'clients',
                'Invoice': 'invoices',
                'Quote': 'quotes',
                'Product': 'products',
                'Payment': 'payments'
            }

            endpoint = endpoint_map.get(sync_type)
            if not endpoint:
                raise Exception(f"Invalid sync type: {sync_type}")

            # Fetch records from Invoice Ninja
            data = self.client.get(f"{endpoint}?per_page={limit}")
            if not data or not data.get('data'):
                return {"synced": 0, "message": "No records found"}

            # Map to ERPNext doctype
            doctype_map = {
                'Customer': 'Customer',
                'Invoice': 'Sales Invoice',
                'Quote': 'Quotation',
                'Product': 'Item',
                'Payment': 'Payment Entry'
            }

            doc_type = doctype_map[sync_type]
            synced_count = 0

            for record in data['data']:
                try:
                    result = self.sync_document_from_invoice_ninja(record, doc_type)
                    if result:
                        synced_count += 1
                except Exception as e:
                    frappe.log_error(f"Failed to sync {sync_type} {record.get('id')}: {str(e)}", "Record Sync Error")
                    continue

            return {"synced": synced_count, "total": len(data['data'])}

        except Exception as e:
            frappe.log_error(f"Bulk sync failed: {str(e)}", "Bulk Sync Error")
            raise e

    def sync_all_records_to_invoice_ninja(self, doc_type, limit=100):
        """Sync all records of a type from ERPNext to Invoice Ninja"""
        try:
            # Get all records of this doctype that don't have Invoice Ninja ID yet
            filters = {
                "custom_invoice_ninja_id": ["is", "not set"]
            }

            # Add additional filters based on doctype
            if doc_type == "Sales Invoice":
                filters["docstatus"] = 1  # Only submitted invoices
            elif doc_type == "Quotation":
                filters["status"] = ["!=", "Cancelled"]
            elif doc_type == "Payment Entry":
                filters["docstatus"] = 1  # Only submitted payments

            records = frappe.get_list(
                doc_type,
                filters=filters,
                limit=limit,
                fields=["name"]
            )

            if not records:
                return {"synced": 0, "message": "No records to sync"}

            synced_count = 0

            for record in records:
                try:
                    doc = frappe.get_doc(doc_type, record.name)
                    result = self.sync_document_to_invoice_ninja(doc)
                    if result:
                        synced_count += 1
                except Exception as e:
                    frappe.log_error(f"Failed to sync {doc_type} {record.name}: {str(e)}", "Record Sync Error")
                    continue

            return {"synced": synced_count, "total": len(records)}

        except Exception as e:
            frappe.log_error(f"Bulk sync to Invoice Ninja failed: {str(e)}", "Bulk Sync Error")
            raise e
