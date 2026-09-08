// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

const denominations = [10, 20, 50, 100, 500, 1000, 5000];
const mohasil_employee_filters = {
	status: "Active",
	designation: "Mohasil",
};
const assignment_fields = [
	"donation_location",
	"location_type",
	"location_name",
	"donor_location",
	"contact",
	"contact_number",
	"care_of_trustee",
	"care_of_donor",
	"deployment_officer",
];
const always_locked_fields = [
	"box_number",
	"box_code",
	"donation_head",
	"box_shape",
	"status",
	"assignment_date",
	"collection_date",
	"collection_office",
	"collected_amount",
];

frappe.ui.form.on("Box Collection", {
	setup(frm) {
		frm.set_query("mode_of_payment", () => ({
			filters: {
				enabled: 1,
				type: "Cash",
			},
		}));

		frm.set_query("debit_account", () => {
			const filters = {
				is_group: 0,
				account_type: "Cash",
			};

			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}

			return { filters };
		});

		frm.set_query("credit_account", () => {
			const filters = {
				is_group: 0,
				root_type: "Income",
			};
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("deployment_officer", () => ({
			filters: mohasil_employee_filters,
		}));

		frm.set_query("collection_office", () => ({
			filters: mohasil_employee_filters,
		}));
	},

	refresh(frm) {
		set_field_locks(frm);

		if (frm.is_new() || frm.doc.docstatus !== 1) {
			return;
		}

		if (["Available", "Collected"].includes(frm.doc.status)) {
			const label = frm.doc.status === "Collected" ? __("Reissuance") : __("Issuance");
			const method = frm.doc.status === "Collected" ? "set_reissuance_date" : "set_issuance_date";
			frm.add_custom_button(label, () => show_assignment_dialog(frm, label, method), __("Actions"));
		}

		if (frm.doc.status === "Issued") {
			frm.add_custom_button(__("Collection"), () => show_collection_dialog(frm), __("Actions"));
		}
		if (frm.doc.status === "Collected") {
			frm.add_custom_button(__("Receive"), () => run_simple_box_action(frm, "receive_box", __("Receive this box?")), __("Actions"));
		}
		if (frm.doc.status === "Received") {
			frm.add_custom_button(__("Close"), () => run_simple_box_action(frm, "close_box", __("Close this box?")), __("Actions"));
		}
		if (!["Closed", "Cancelled"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel Box"), () => show_cancel_dialog(frm), __("Actions"));
		}
	},

	donation_location(frm) {
		set_location_details_from_master(frm);
	},
});

function set_field_locks(frm) {
	always_locked_fields.forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", 1);
	});

	const lock_assignment = frm.doc.docstatus === 1 && frm.doc.status === "Issued";
	assignment_fields.forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", lock_assignment ? 1 : 0);
	});
}

function show_assignment_dialog(frm, title, method) {
	let dialog;
	dialog = new frappe.ui.Dialog({
		title,
		fields: [
			{
				fieldname: "donation_location",
				fieldtype: "Link",
				label: __("Donation Location"),
				options: "Donation Location",
				reqd: 1,
				default: frm.doc.donation_location,
				onchange: () => set_dialog_location_details(dialog),
			},
			{
				fieldname: "location_type",
				fieldtype: "Link",
				label: __("Location Type"),
				options: "Location Type",
				default: frm.doc.location_type,
			},
			{
				fieldname: "location_name",
				fieldtype: "Data",
				label: __("Shop/House Name"),
				default: frm.doc.location_name,
			},
			{
				fieldname: "donor_location",
				fieldtype: "Data",
				label: __("Address for Box Delivery"),
				default: frm.doc.donor_location,
			},
			{
				fieldname: "contact",
				fieldtype: "Data",
				label: __("Contact"),
				default: frm.doc.contact,
			},
			{
				fieldname: "contact_number",
				fieldtype: "Phone",
				label: __("Contact Number"),
				default: frm.doc.contact_number,
			},
			{
				fieldname: "care_of_trustee",
				fieldtype: "Link",
				label: __("Care Of Trustee"),
				options: "Trustee",
				default: frm.doc.care_of_trustee,
			},
			{
				fieldname: "care_of_donor",
				fieldtype: "Link",
				label: __("Care Of Donor"),
				options: "Donor",
				default: frm.doc.care_of_donor,
			},
			{
				fieldname: "deployment_officer",
				fieldtype: "Link",
				label: __("Delivery Staff"),
				options: "Employee",
				reqd: 1,
				default: frm.doc.deployment_officer,
				get_query: () => ({
					filters: mohasil_employee_filters,
				}),
			},
			{
				fieldname: "approval_section",
				fieldtype: "Section Break",
				label: __("Approval"),
			},
			{
				fieldname: "approval_reference",
				fieldtype: "Data",
				label: __("Approval Reference"),
				reqd: 1,
				default: frm.doc.approval_reference,
			},
			{
				fieldname: "approved_by",
				fieldtype: "Link",
				label: __("Approved By"),
				options: "User",
				reqd: 1,
				default: frm.doc.approved_by,
			},
		],
		primary_action_label: title,
		primary_action(values) {
			frm.call(method, values).then(() => {
				dialog.hide();
				frm.reload_doc();
			});
		},
	});

	dialog.show();
}

function run_simple_box_action(frm, method, confirmation) {
	frappe.confirm(confirmation, () => {
		frm.call(method).then(() => frm.reload_doc());
	});
}

function show_cancel_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Cancel Box"),
		fields: [
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason"),
				reqd: 1,
			},
		],
		primary_action_label: __("Cancel Box"),
		primary_action(values) {
			frm.call("cancel_box", { reason: values.reason }).then(() => {
				dialog.hide();
				frm.reload_doc();
			});
		},
	});
	dialog.show();
}

function set_location_details_from_master(frm) {
	if (!frm.doc.donation_location) {
		["location_type", "location_name", "donor_location", "contact", "contact_number"].forEach(
			(fieldname) => frm.set_value(fieldname, "")
		);
		return;
	}

	frappe.db
		.get_value("Donation Location", frm.doc.donation_location, [
			"location_type",
			"contact",
			"contact_person",
			"shophouse_name",
			"address",
		])
		.then((response) => {
			const location = response.message || {};
			frm.set_value({
				location_type: location.location_type || "",
				contact_number: location.contact || "",
				contact: location.contact_person || "",
				location_name: location.shophouse_name || "",
				donor_location: location.address || "",
			});
		});
}

function set_dialog_location_details(dialog) {
	const donation_location = dialog.get_value("donation_location");
	if (!donation_location) {
		["location_type", "location_name", "donor_location", "contact", "contact_number"].forEach(
			(fieldname) => dialog.set_value(fieldname, "")
		);
		return;
	}

	frappe.db
		.get_value("Donation Location", donation_location, [
			"location_type",
			"contact",
			"contact_person",
			"shophouse_name",
			"address",
		])
		.then((response) => {
			const location = response.message || {};
			dialog.set_value("location_type", location.location_type || "");
			dialog.set_value("contact_number", location.contact || "");
			dialog.set_value("contact", location.contact_person || "");
			dialog.set_value("location_name", location.shophouse_name || "");
			dialog.set_value("donor_location", location.address || "");
		});
}

function show_collection_dialog(frm) {
	frappe.call({
		method: "donation_management.donation_management.api.get_collection_cash_accounting_defaults",
		args: {
			source_type: "Box Collection",
			donation_type: frm.doc.donation_head,
		},
		callback(response) {
			build_collection_dialog(frm, response.message || {});
		},
	});
}

function build_collection_dialog(frm, accounting_defaults) {
	const fields = [
		{
			fieldname: "collection_office",
			fieldtype: "Link",
			label: __("Collection Staff"),
			options: "Employee",
			reqd: 1,
			default: frm.doc.collection_office,
			get_query: () => ({
				filters: mohasil_employee_filters,
			}),
		},
		{
			fieldname: "collected_amount",
			fieldtype: "Currency",
			label: __("Collected Amount"),
			reqd: 1,
			onchange: () => update_denomination_total(dialog),
		},
		{
			fieldname: "accounting_section",
			fieldtype: "Section Break",
			label: __("Accounting"),
		},
		{
			fieldname: "mode_of_payment",
			fieldtype: "Link",
			label: __("Mode of Payment"),
			options: "Mode of Payment",
			reqd: 1,
			default: accounting_defaults.mode_of_payment || frm.doc.mode_of_payment,
			read_only: 1,
		},
		{
			fieldname: "debit_account",
			fieldtype: "Link",
			label: __("Debit Account"),
			options: "Account",
			reqd: 1,
			default: accounting_defaults.debit_account || frm.doc.debit_account,
			read_only: 1,
		},
		{
			fieldname: "credit_account",
			fieldtype: "Link",
			label: __("Income Account"),
			options: "Account",
			reqd: 1,
			default: frm.doc.credit_account || accounting_defaults.credit_account,
			get_query: () => {
				const filters = {
					is_group: 0,
					root_type: "Income",
				};
				const company = accounting_defaults.company || frm.doc.company;
				if (company) {
					filters.company = company;
				}
				return { filters };
			},
		},
		{
			fieldname: "denomination_section",
			fieldtype: "Section Break",
			label: __("Cash Denominations"),
		},
	];

	denominations.forEach((denomination) => {
		fields.push({
			fieldname: `denomination_${denomination}`,
			fieldtype: "Int",
			label: __("{0} Rs Notes", [denomination]),
			default: 0,
			non_negative: 1,
			onchange: () => update_denomination_total(dialog),
		});
	});

	fields.push({
		fieldname: "denomination_total",
		fieldtype: "Currency",
		label: __("Denomination Total"),
		read_only: 1,
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Collection"),
		fields,
		primary_action_label: __("Collection"),
		primary_action(values) {
			if (!validate_denomination_total(dialog)) {
				return;
			}

			const denomination_values = {};
			denominations.forEach((denomination) => {
				denomination_values[denomination] = values[`denomination_${denomination}`] || 0;
			});

			frm.call("set_collection_date", {
				collection_office: values.collection_office,
				collected_amount: values.collected_amount,
				denominations: denomination_values,
				mode_of_payment: values.mode_of_payment,
				debit_account: values.debit_account,
				credit_account: values.credit_account,
			}).then(() => {
				dialog.hide();
				frm.reload_doc();
			});
		},
	});

	dialog.show();
	update_denomination_total(dialog);
}

function update_denomination_total(dialog) {
	let total = 0;
	denominations.forEach((denomination) => {
		total += denomination * flt(dialog.get_value(`denomination_${denomination}`));
	});
	dialog.set_value("denomination_total", total);
}

function validate_denomination_total(dialog) {
	const collected_amount = flt(dialog.get_value("collected_amount"));
	const denomination_total = flt(dialog.get_value("denomination_total"));

	if (collected_amount !== denomination_total) {
		frappe.msgprint(
			__("Denomination total {0} must match Collected Amount {1}.", [
				format_currency(denomination_total),
				format_currency(collected_amount),
			])
		);
		return false;
	}

	return true;
}
