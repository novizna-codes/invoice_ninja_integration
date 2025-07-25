app_name = "invoice_ninja_integration"
app_title = "Invoice Ninja Integration"
app_publisher = "Novizna"
app_description = "Integration with Invoice Ninja"
app_email = "developers@novizna.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "invoice_ninja_integration",
# 		"logo": "/assets/invoice_ninja_integration/logo.png",
# 		"title": "Invoice Ninja Integration",
# 		"route": "/invoice_ninja_integration",
# 		"has_permission": "invoice_ninja_integration.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/invoice_ninja_integration/css/invoice_ninja_integration.css"
# app_include_js = "/assets/invoice_ninja_integration/js/invoice_ninja_integration.js"

# include js, css files in header of web template
# web_include_css = "/assets/invoice_ninja_integration/css/invoice_ninja_integration.css"
# web_include_js = "/assets/invoice_ninja_integration/js/invoice_ninja_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "invoice_ninja_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "invoice_ninja_integration/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "invoice_ninja_integration.utils.jinja_methods",
# 	"filters": "invoice_ninja_integration.utils.jinja_filters"
# }

# Document Events
# ---------------

doc_events = {
    "Customer": {
        "after_insert": "invoice_ninja_integration.sync_hooks.on_customer_save",
        "on_update": "invoice_ninja_integration.sync_hooks.on_customer_save",
    },
    "Sales Invoice": {
        "on_submit": "invoice_ninja_integration.sync_hooks.on_invoice_save",
        "on_update_after_submit": "invoice_ninja_integration.sync_hooks.on_invoice_save",
    },
    "Quotation": {
        "after_insert": "invoice_ninja_integration.sync_hooks.on_quotation_save",
        "on_update": "invoice_ninja_integration.sync_hooks.on_quotation_save",
    },
    "Item": {
        "after_insert": "invoice_ninja_integration.sync_hooks.on_item_save",
        "on_update": "invoice_ninja_integration.sync_hooks.on_item_save",
    },
    "Payment Entry": {
        "on_submit": "invoice_ninja_integration.sync_hooks.on_payment_save",
        "on_update_after_submit": "invoice_ninja_integration.sync_hooks.on_payment_save",
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "hourly": [
        "invoice_ninja_integration.tasks.sync_from_invoice_ninja"
    ],
    "daily": [
        "invoice_ninja_integration.tasks.cleanup_sync_logs"
    ]
}

# Installation
# ------------

# before_install = "invoice_ninja_integration.install.before_install"
# after_install = "invoice_ninja_integration.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "invoice_ninja_integration.uninstall.before_uninstall"
# after_uninstall = "invoice_ninja_integration.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "invoice_ninja_integration.utils.before_app_install"
# after_app_install = "invoice_ninja_integration.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "invoice_ninja_integration.utils.before_app_uninstall"
# after_app_uninstall = "invoice_ninja_integration.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "invoice_ninja_integration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"invoice_ninja_integration.tasks.all"
# 	],
# 	"daily": [
# 		"invoice_ninja_integration.tasks.daily"
# 	],
# 	"hourly": [
# 		"invoice_ninja_integration.tasks.hourly"
# 	],
# 	"weekly": [
# 		"invoice_ninja_integration.tasks.weekly"
# 	],
# 	"monthly": [
# 		"invoice_ninja_integration.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "invoice_ninja_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "invoice_ninja_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "invoice_ninja_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["invoice_ninja_integration.utils.before_request"]
# after_request = ["invoice_ninja_integration.utils.after_request"]

# Job Events
# ----------
# before_job = ["invoice_ninja_integration.utils.before_job"]
# after_job = ["invoice_ninja_integration.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"invoice_ninja_integration.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

