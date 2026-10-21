frappe.ui.form.on("Maktab Payment Schedule", {
	setup(frm) {
		set_account_queries(frm);
	},

	ilaqi_maktab(frm) {
		fetch_maktab_details(frm);
	},

	donation_order(frm) {
		fetch_donation_order_details(frm);
	},
});

function set_account_queries(frm) {
	frm.set_query("custom_debit_account", () => ({
		filters: {
			disabled: 0,
			is_group: 0,
			root_type: "Asset",
		},
	}));
	frm.set_query("custom_credit_account", () => ({
		filters: {
			disabled: 0,
			is_group: 0,
			root_type: "Income",
		},
	}));
}

function set_value_if_changed(frm, fieldname, value) {
	if (frm.doc[fieldname] !== value) {
		frm.set_value(fieldname, value || "");
	}
}

function fetch_maktab_details(frm) {
	const ilaqi_maktab = frm.doc.ilaqi_maktab;
	if (!ilaqi_maktab) {
		set_value_if_changed(frm, "frequency", "");
		set_value_if_changed(frm, "custom_responsible_person", "");
		return;
	}

	frappe.db.get_value("Ilaqi Maktab", ilaqi_maktab, ["frequency", "responsible_person"]).then((response) => {
		if (frm.doc.ilaqi_maktab !== ilaqi_maktab) {
			return;
		}

		const values = response.message || {};
		set_value_if_changed(frm, "frequency", values.frequency || "");

		if (!values.responsible_person) {
			set_value_if_changed(frm, "custom_responsible_person", "");
			return;
		}

		frappe.db.get_value("Employee", values.responsible_person, "employee_name").then((employee) => {
			if (frm.doc.ilaqi_maktab !== ilaqi_maktab) {
				return;
			}

			set_value_if_changed(frm, "custom_responsible_person", employee.message?.employee_name || "");
		});
	});
}

function fetch_donation_order_details(frm) {
	if (!frm.doc.donation_order) {
		return;
	}

	frappe.db
		.get_value("Donation Order", frm.doc.donation_order, [
			"mode_of_payment",
			"mohasil",
			"debit_account",
			"credit_account",
		])
		.then((response) => {
		const values = response.message || {};
		set_value_if_changed(frm, "mode_of_payment", values.mode_of_payment || "");
		set_value_if_changed(frm, "collection_person", values.mohasil || "");
		set_value_if_changed(frm, "custom_debit_account", values.debit_account || "");
		set_value_if_changed(frm, "custom_credit_account", values.credit_account || "");
		});
}
