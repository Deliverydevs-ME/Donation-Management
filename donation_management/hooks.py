app_name = "donation_management"
app_title = "Donation Management"
app_publisher = "osama.ahmed@deliverydevs.com"
app_description = "Donation Management For Trust"
app_email = "osama.ahmed@deliverydevs.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "donation_management",
# 		"logo": "/assets/donation_management/logo.png",
# 		"title": "Donation Management",
# 		"route": "/donation_management",
# 		"has_permission": "donation_management.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/donation_management/css/donation_management.css"
app_include_js = [
	"/assets/donation_management/js/frappe_model_guard.js",
	"/assets/donation_management/js/purchase_taxes_and_charges.js",
	
]

# include js, css files in header of web template
# web_include_css = "/assets/donation_management/css/donation_management.css"
# web_include_js = "/assets/donation_management/js/donation_management.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "donation_management/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Journal Entry": "public/js/journal_entry.js",
	"Additional Salary": "public/js/additional_salary.js",
	"Data Import": "public/js/data_import.js",
}
doctype_list_js = {
	"Journal Entry": "public/js/journal_entry_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Fixtures
# --------
fixtures = [
	{
		"dt": "Property Setter",
		"filters": [
			["doc_type", "=", "Party Type"],
			["field_name", "=", "account_type"],
		],
	},
]

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "donation_management/public/icons.svg"

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
# 	"methods": "donation_management.utils.jinja_methods",
# 	"filters": "donation_management.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "donation_management.install.before_install"
# after_install = "donation_management.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "donation_management.uninstall.before_uninstall"
# after_uninstall = "donation_management.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "donation_management.utils.before_app_install"
# after_app_install = "donation_management.utils.after_app_install"
after_migrate = "donation_management.patches.ensure_enhancement_customizations.execute"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "donation_management.utils.before_app_uninstall"
# after_app_uninstall = "donation_management.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "donation_management.notifications.get_notification_config"

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

override_doctype_class = {
	"GL Entry": "donation_management.gl_entry.CustomGLEntry",
}

# Document Events
# ---------------
# Hook on document methods and events

purchase_tax_doc_events = {
	"before_validate": "donation_management.purchase_taxes.force_purchase_tax_deduction",
}

doc_events = {
	"Purchase Invoice": purchase_tax_doc_events,
	"Purchase Order": purchase_tax_doc_events,
	"Purchase Receipt": purchase_tax_doc_events,
	"Supplier Quotation": purchase_tax_doc_events,
	"Additional Salary": {
		"before_validate": "donation_management.hr_payroll.sync_additional_salary_controls",
		"before_update_after_submit": "donation_management.hr_payroll.sync_additional_salary_controls",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"donation_management.pdc_reminders.send_pdc_reminders",
	],
}

# Testing
# -------

# before_tests = "donation_management.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.desk.form.load.getdoctype": "donation_management.donation_management.api.safe_getdoctype",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Donor": "donation_management.donation_management.doctype.donor.donor_dashboard.get_data",
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["donation_management.utils.before_request"]
# after_request = ["donation_management.utils.after_request"]

# Job Events
# ----------
# before_job = ["donation_management.utils.before_job"]
# after_job = ["donation_management.utils.after_job"]

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
# 	"donation_management.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
