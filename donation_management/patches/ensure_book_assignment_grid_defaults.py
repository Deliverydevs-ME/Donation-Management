import json

import frappe


DONATION_BOOK_COLUMNS = (
	"receipt_format",
	"from_receipt_no",
	"to_receipt_no",
	"used_receipts",
	"remaining_receipts",
)


def execute():
	settings_rows = frappe.db.sql(
		"select `user`, `data` from `__UserSettings` where `doctype` = %s",
		("Book Assignment",),
		as_dict=True,
	)
	for setting in settings_rows:
		try:
			settings = json.loads(setting.data or "{}")
		except (TypeError, ValueError):
			continue

		grid_settings = settings.get("GridView") or {}
		columns = grid_settings.get("Book Assignment Detail")
		if not isinstance(columns, list) or not columns:
			continue

		existing = {column.get("fieldname") for column in columns if isinstance(column, dict)}
		updated = False
		for fieldname in DONATION_BOOK_COLUMNS:
			if fieldname not in existing:
				columns.append({"fieldname": fieldname, "columns": 1})
				updated = True

		if updated:
			frappe.db.sql(
				"update `__UserSettings` set `data` = %s where `user` = %s and `doctype` = %s",
				(json.dumps(settings), setting.user, "Book Assignment"),
			)
			frappe.cache.hset(
				"_user_settings",
				f"Book Assignment::{setting.user}",
				json.dumps(settings),
			)
