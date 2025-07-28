import frappe
from frappe import _


class CompanyMapper:
    """
    Handles mapping between ERPNext companies and Invoice Ninja companies
    Ensures proper routing of documents based on company mappings
    """

    def __init__(self):
        self.settings = frappe.get_single("Invoice Ninja Settings")

    def get_company_mapping(self, erpnext_company=None, invoice_ninja_company_id=None):
        """
        Get company mapping based on ERPNext company or Invoice Ninja company ID

        Args:
            erpnext_company: ERPNext company name
            invoice_ninja_company_id: Invoice Ninja company ID

        Returns:
            dict: Company mapping or None if not found
        """
        if not self.settings.company_mappings:
            return None

        for mapping in self.settings.company_mappings:
            if not mapping.enabled:
                continue

            if erpnext_company and mapping.erpnext_company == erpnext_company:
                return {
                    "erpnext_company": mapping.erpnext_company,
                    "invoice_ninja_company_id": mapping.invoice_ninja_company_id,
                    "invoice_ninja_company_name": mapping.invoice_ninja_company_name,
                    "is_default": mapping.is_default
                }
            elif invoice_ninja_company_id and str(mapping.invoice_ninja_company_id) == str(invoice_ninja_company_id):
                return {
                    "erpnext_company": mapping.erpnext_company,
                    "invoice_ninja_company_id": mapping.invoice_ninja_company_id,
                    "invoice_ninja_company_name": mapping.invoice_ninja_company_name,
                    "is_default": mapping.is_default
                }

        return None

    def get_default_mapping(self):
        """Get the default company mapping"""
        if not self.settings.company_mappings:
            return None

        for mapping in self.settings.company_mappings:
            if mapping.enabled and mapping.is_default:
                return {
                    "erpnext_company": mapping.erpnext_company,
                    "invoice_ninja_company_id": mapping.invoice_ninja_company_id,
                    "invoice_ninja_company_name": mapping.invoice_ninja_company_name,
                    "is_default": mapping.is_default
                }

        return None

    def get_invoice_ninja_company_id(self, erpnext_company):
        """
        Get Invoice Ninja company ID for an ERPNext company

        Args:
            erpnext_company: ERPNext company name

        Returns:
            str: Invoice Ninja company ID or None
        """
        mapping = self.get_company_mapping(erpnext_company=erpnext_company)
        if mapping:
            return mapping["invoice_ninja_company_id"]

        # Fall back to default mapping
        default_mapping = self.get_default_mapping()
        if default_mapping:
            return default_mapping["invoice_ninja_company_id"]

        return None

    def get_erpnext_company(self, invoice_ninja_company_id):
        """
        Get ERPNext company for an Invoice Ninja company ID

        Args:
            invoice_ninja_company_id: Invoice Ninja company ID

        Returns:
            str: ERPNext company name or None
        """
        mapping = self.get_company_mapping(invoice_ninja_company_id=invoice_ninja_company_id)
        if mapping:
            return mapping["erpnext_company"]

        # Fall back to default mapping
        default_mapping = self.get_default_mapping()
        if default_mapping:
            return default_mapping["erpnext_company"]

        return None

    def validate_company_mapping(self, doc):
        """
        Validate if document's company has proper mapping

        Args:
            doc: ERPNext document

        Returns:
            bool: True if mapping exists, False otherwise
        """
        if not hasattr(doc, 'company') or not doc.company:
            # If no company field, use default mapping
            return self.get_default_mapping() is not None

        return self.get_invoice_ninja_company_id(doc.company) is not None

    def get_all_mappings(self):
        """Get all enabled company mappings"""
        if not self.settings.company_mappings:
            return []

        mappings = []
        for mapping in self.settings.company_mappings:
            if mapping.enabled:
                mappings.append({
                    "erpnext_company": mapping.erpnext_company,
                    "invoice_ninja_company_id": mapping.invoice_ninja_company_id,
                    "invoice_ninja_company_name": mapping.invoice_ninja_company_name,
                    "is_default": mapping.is_default
                })

        return mappings

    def set_company_context(self, doc, invoice_ninja_data=None):
        """
        Set proper company context for document synchronization

        Args:
            doc: ERPNext document
            invoice_ninja_data: Invoice Ninja data (optional)

        Returns:
            dict: Company context with ERPNext and Invoice Ninja company info
        """
        context = {}

        if doc:
            # For ERPNext to Invoice Ninja sync
            erpnext_company = getattr(doc, 'company', None)
            if erpnext_company:
                invoice_ninja_company_id = self.get_invoice_ninja_company_id(erpnext_company)
                context = {
                    "erpnext_company": erpnext_company,
                    "invoice_ninja_company_id": invoice_ninja_company_id,
                    "sync_direction": "erpnext_to_invoice_ninja"
                }
            else:
                # Use default mapping
                default_mapping = self.get_default_mapping()
                if default_mapping:
                    context = {
                        "erpnext_company": default_mapping["erpnext_company"],
                        "invoice_ninja_company_id": default_mapping["invoice_ninja_company_id"],
                        "sync_direction": "erpnext_to_invoice_ninja"
                    }

        if invoice_ninja_data:
            # For Invoice Ninja to ERPNext sync
            invoice_ninja_company_id = invoice_ninja_data.get('company_id')
            if invoice_ninja_company_id:
                erpnext_company = self.get_erpnext_company(invoice_ninja_company_id)
                context.update({
                    "erpnext_company": erpnext_company,
                    "invoice_ninja_company_id": invoice_ninja_company_id,
                    "sync_direction": "invoice_ninja_to_erpnext"
                })
            else:
                # Use default mapping
                default_mapping = self.get_default_mapping()
                if default_mapping:
                    context.update({
                        "erpnext_company": default_mapping["erpnext_company"],
                        "invoice_ninja_company_id": default_mapping["invoice_ninja_company_id"],
                        "sync_direction": "invoice_ninja_to_erpnext"
                    })

        return context

    def should_sync_document(self, doc):
        """
        Check if document should be synced based on company mapping

        Args:
            doc: ERPNext document

        Returns:
            bool: True if document should be synced
        """
        if not self.settings.enabled:
            return False

        # Check if company mapping exists
        if not self.validate_company_mapping(doc):
            frappe.log_error(
                f"No company mapping found for document {doc.doctype} {doc.name} with company {getattr(doc, 'company', 'None')}",
                "Company Mapping Error"
            )
            return False

        return True
