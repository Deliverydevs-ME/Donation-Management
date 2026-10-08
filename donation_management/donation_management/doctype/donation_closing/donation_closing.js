// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Donation Closing", {
	setup(frm) {
		frm.ignore_doctypes_on_cancel_all = ["Donation Cash Handover"];
	},

	onload(frm) {
		if (frappe.route_options && frappe.route_options.show_fetch_alert) {
			frappe.show_alert({
				message: frappe.route_options.show_fetch_alert,
				indicator: "green",
			});
			delete frappe.route_options.show_fetch_alert;
		}
	},

	refresh(frm) {
		frm.remove_custom_button(__("Record Bank Deposit"));
		frm.remove_custom_button(__("Donation Cash Handover"), __("Create"));
		add_cash_handover_button_if_needed(frm);

		if (
			frm.is_new() ||
			(frm.doc.docstatus === 0 &&
				["", "Draft"].includes(frm.doc.status || "") &&
				!(frm.doc.closing_details || []).length)
		) {
			frm.add_custom_button(__("Fetch Pending Cash Donations"), () => fetch_pending(frm));
		}

	},
});

function add_cash_handover_button_if_needed(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0 || frm.doc.cash_handover) {
		return;
	}

	const closing_name = frm.doc.name;
	frappe.db.get_value(
		"Donation Cash Handover",
		{ donation_closing: closing_name, docstatus: ["<", 2] },
		"name",
		(handover) => {
			if (
				frm.doc.name !== closing_name ||
				frm.doc.docstatus !== 0 ||
				frm.doc.cash_handover ||
				handover?.name
			) {
				return;
			}

			frm.add_custom_button(__("Donation Cash Handover"), () => {
				frappe.new_doc("Donation Cash Handover", {
					donation_closing: frm.doc.name,
					company: frm.doc.company,
					cashier: frm.doc.cashier,
					amount: frm.doc.total_amount,
					reference: frm.doc.name,
				});
			}, __("Create"));
		}
	);
}

function fetch_pending(frm) {
	if (!frm.doc.company) {
		frappe.msgprint(__("Company is required before fetching pending cash donations."));
		return;
	}
	if (!frm.doc.closing_date) {
		frappe.msgprint(__("Closing Date is required before fetching pending cash donations."));
		return;
	}

	frappe.call({
		doc: frm.doc,
		method: "fetch_pending_cash_donations",
		freeze: true,
		callback(response) {
			const result = response.message || {};

			if (!result.count) {
				frm.clear_table("closing_details");
				frm.set_value("total_amount", 0);
				frm.set_value("pending_items_count", 0);
				frm.refresh_field("closing_details");
				frappe.msgprint({
					title: __("No Pending Cash"),
					message: result.message || __("No pending cash donations were found."),
					indicator: "orange",
				});
				return;
			}

			const alert_message = __("Fetched {0} items totaling {1}", [
				result.count || 0,
				format_currency(result.total_amount || 0),
			]);

			if (result.name && frm.doc.name !== result.name) {
				frappe.route_options = { show_fetch_alert: alert_message };
				frappe.set_route("Form", "Donation Closing", result.name);
				return;
			}

			apply_fetch_result(frm, result);
			frappe.show_alert({ message: alert_message, indicator: "green" });
		},
	});
}

function apply_fetch_result(frm, result) {
	frm.clear_table("closing_details");
	(result.closing_details || []).forEach((row) => {
		frm.add_child("closing_details", row);
	});
	frm.set_value("total_amount", result.total_amount || 0);
	frm.set_value("pending_items_count", result.count || 0);
	frm.refresh_field("closing_details");
}

function format_currency(amount) {
	return frappe.format(amount, { fieldtype: "Currency" });
}
