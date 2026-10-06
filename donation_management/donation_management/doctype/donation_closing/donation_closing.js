// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Donation Closing", {
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

		if (frm.is_new() || (frm.doc.docstatus === 0 && ["", "Draft"].includes(frm.doc.status || ""))) {
			frm.add_custom_button(__("Fetch Pending Cash Donations"), () => fetch_pending(frm));
		}

		if (!frm.is_new() && frm.doc.docstatus === 0 && frm.doc.status === "Pending Approval") {
			frm.add_custom_button(__("Approve Closing"), () => approve_closing(frm));
		}

		if (!frm.is_new() && frm.doc.docstatus === 0 && frm.doc.status === "Approved") {
			frm.add_custom_button(__("Receive Closing"), () => receive_closing(frm));
		}
	},
});

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

function receive_closing(frm) {
	frappe.call({
		doc: frm.doc,
		method: "receive_closing",
		freeze: true,
		callback() {
			frm.reload_doc();
			frappe.show_alert({ message: __("Donation Closing received"), indicator: "green" });
		},
	});
}

function approve_closing(frm) {
	frappe.call({
		doc: frm.doc,
		method: "approve_closing",
		freeze: true,
		callback() {
			frm.reload_doc();
			frappe.show_alert({ message: __("Donation Closing approved"), indicator: "green" });
		},
	});
}

function format_currency(amount) {
	return frappe.format(amount, { fieldtype: "Currency" });
}
