import frappe

def check_app_permission():
	"""Check if user has permission to access the app (for showing the app on app screen)"""
	if frappe.session.user == "Administrator":
		return True

	# Check for System Manager role
	if frappe.utils.has_common(frappe.get_roles(), ["System Manager"]):
		return True

	# Check if user has read permission on main doctype (e.g., Sales Invoice)
	# This ensures users who can see invoices can see the app
	if frappe.has_permission("Sales Invoice", ptype="read"):
		return True

	return False
