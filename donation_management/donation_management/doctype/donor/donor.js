// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

const donor_types = [
	"Walk-in",
	"Refered by Trustee",
	"Key Donor",
	"Sub General Donor",
	"General Donor",
	"Sub Key Donor",
];
const confidential_reference_roles = ["Donation Confidential Reference User", "System Manager"];
const mohasil_employee_filters = {
	status: "Active",
	designation: "Mohasil",
};

frappe.ui.form.on("Donor", {
	setup(frm) {
		set_donor_type_options(frm);

		frm.set_query("parent_donor", () => ({
			filters: {
				is_group: 1,
				name: ["!=", frm.doc.name || ""],
			},
		}));

		frm.set_query("referred_by_trustee", () => ({
			filters: {
				is_group: 1,
			},
		}));

		frm.set_query("mohasil", () => ({
			filters: mohasil_employee_filters,
		}));

		frm.set_query("person_name", "esaal_e_sawab", () => ({
			filters: {
				is_group: 0,
				name: ["!=", frm.doc.name || ""],
			},
		}));
	},

	refresh(frm) {
		set_donor_type_options(frm);
		toggle_donor_reference_fields(frm);
		show_donor_information_request_audit_fields(frm);
		toggle_donor_contact_requirement(frm);
		add_donor_ledger_buttons(frm);
	},

	after_save(frm) {
		return_to_donation_order_after_esaal_person_added(frm);
	},

	customer_type(frm) {
		toggle_donor_reference_fields(frm);
		if (frm.doc.customer_type !== "Refered by Trustee") {
			set_value_if_changed(frm, "referred_by_trustee", "");
		}
		if (frm.doc.customer_type === "Refered by Trustee") {
			set_value_if_changed(frm, "parent_donor", "");
		}
	},

	donor_information_request_status(frm) {
		show_donor_information_request_audit_fields(frm);
	},
});

function has_confidential_reference_access() {
	return confidential_reference_roles.some((role) => frappe.user.has_role(role));
}

const DONOR_ESAAL_E_SAWAB_RETURN_CONTEXT_KEY = "donation_management.esaal_e_sawab_return_context";
const DONOR_ESAAL_E_SAWAB_RETURN_CONTEXT_TTL = 2 * 60 * 60 * 1000;

function return_to_donation_order_after_esaal_person_added(frm) {
	const saved_context = window.sessionStorage.getItem(DONOR_ESAAL_E_SAWAB_RETURN_CONTEXT_KEY);
	if (!saved_context) {
		return;
	}

	let context;
	try {
		context = JSON.parse(saved_context);
	} catch (error) {
		window.sessionStorage.removeItem(DONOR_ESAAL_E_SAWAB_RETURN_CONTEXT_KEY);
		return;
	}

	if (
		context.donor !== frm.doc.name ||
		Date.now() - context.created_at > DONOR_ESAAL_E_SAWAB_RETURN_CONTEXT_TTL ||
		!(frm.doc.esaal_e_sawab || []).some((row) => row.person_name)
	) {
		return;
	}

	window.sessionStorage.removeItem(DONOR_ESAAL_E_SAWAB_RETURN_CONTEXT_KEY);
	frappe.model.sync(context.document);
	frappe.set_route(...context.route);
}

function set_donor_type_options(frm) {
	const options = has_confidential_reference_access()
		? donor_types
		: donor_types.filter((type) => type !== "Refered by Trustee");
	frm.set_df_property("customer_type", "options", ["", ...options].join("\n"));
}

function toggle_donor_reference_fields(frm) {
	const is_referred_by_trustee =
		frm.doc.customer_type === "Refered by Trustee" && has_confidential_reference_access();
	frm.toggle_display("referred_by_trustee", is_referred_by_trustee);
	frm.toggle_reqd("referred_by_trustee", is_referred_by_trustee);
	frm.toggle_display("parent_donor", !is_referred_by_trustee);
}

function toggle_donor_contact_requirement(frm) {
	frappe.db.get_doc("Donation Settings", "Donation Settings").then((settings) => {
		const messages = [];

		if (cint(settings.allow_donor_without_phone_or_email)) {
			messages.push(__("Phone or Email is optional as per Donation Settings."));
		} else {
			messages.push(__("Either Donor Phone Number or Donor Email is required."));
		}

		if (cint(settings.allow_duplicate_donor_phone)) {
			messages.push(__("Duplicate phone numbers are allowed."));
		}

		frm.set_intro(messages.join(" "), cint(settings.allow_donor_without_phone_or_email) ? "blue" : "yellow");
	});
}

function show_donor_information_request_audit_fields(frm) {
	["requesting_user", "request_date", "request_remarks"].forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.toggle_display(fieldname, true);
		}
	});

	["requesting_user", "request_date"].forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "read_only", 1);
		}
	});
}

function add_donor_ledger_buttons(frm) {
	if (frm.is_new()) {
		return;
	}

	const ledger_group = __("Ledger");

	frm.add_custom_button(
		__("Donation History"),
		() => frappe.set_route("List", "Donation Order", { donor_name: frm.doc.name }),
		ledger_group
	);

	frm.add_custom_button(
		__("Donation Statement"),
		() => frappe.set_route("query-report", "Donor Donation Statement", { donor: frm.doc.name }),
		ledger_group
	);

	frm.add_custom_button(
		__("Balance Summary"),
		() => frappe.set_route("query-report", "Donor Balance Report", { donor: frm.doc.name }),
		ledger_group
	);

	frm.add_custom_button(
		__("General Ledger"),
		() =>
			frappe.set_route("query-report", "General Ledger", {
				party_type: "Donor",
				party: frm.doc.name,
			}),
		ledger_group
	);
}

function set_value_if_changed(frm, fieldname, value) {
	const current_value = frm.doc[fieldname] || "";
	const new_value = value || "";

	if (String(current_value) !== String(new_value)) {
		frm.set_value(fieldname, value);
	}
}
