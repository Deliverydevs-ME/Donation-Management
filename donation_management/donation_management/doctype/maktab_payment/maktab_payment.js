frappe.ui.form.on("Maktab Payment", {
	setup(frm) {
		set_account_queries(frm);
	},

	payment_schedule(frm) {
		fetch_schedule_details(frm);
	},

	donation_order(frm) {
		fetch_donation_order_details(frm);
	},

	ilaqi_maktab(frm) {
		if (!frm.doc.frequency) {
			fetch_maktab_frequency(frm);
		}
	},
});

function set_account_queries(frm) {
	["debit_account", "credit_account"].forEach((fieldname) => {
		frm.set_query(fieldname, () => ({
			filters: {
				is_group: 0,
			},
		}));
	});
}

function set_value_if_changed(frm, fieldname, value) {
	if (frm.doc[fieldname] !== value) {
		frm.set_value(fieldname, value || "");
	}
}

function fetch_maktab_frequency(frm) {
	if (!frm.doc.ilaqi_maktab) {
		return;
	}

	frappe.db.get_value("Ilaqi Maktab", frm.doc.ilaqi_maktab, "frequency").then((response) => {
		const values = response.message || {};
		set_value_if_changed(frm, "frequency", values.frequency || "");
	});
}

function fetch_schedule_details(frm) {
	if (!frm.doc.payment_schedule) {
		return;
	}

	frappe.db
		.get_value("Maktab Payment Schedule", frm.doc.payment_schedule, [
			"ilaqi_maktab",
			"frequency",
			"outstanding_amount",
			"mode_of_payment",
			"donation_order",
			"collection_person",
		])
		.then((response) => {
			const values = response.message || {};
			set_value_if_changed(frm, "ilaqi_maktab", values.ilaqi_maktab || "");
			set_value_if_changed(frm, "frequency", values.frequency || "");
			set_value_if_changed(frm, "outstanding_amount", values.outstanding_amount || 0);
			set_value_if_changed(frm, "mode_of_payment", values.mode_of_payment || "");
			set_value_if_changed(frm, "donation_order", values.donation_order || "");
			set_value_if_changed(frm, "collection_person", values.collection_person || "");
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
			"donation_amount",
		])
		.then((response) => {
			const values = response.message || {};
			set_value_if_changed(frm, "mode_of_payment", values.mode_of_payment || "");
			set_value_if_changed(frm, "collection_person", values.mohasil || "");
			set_value_if_changed(frm, "debit_account", values.debit_account || "");
			set_value_if_changed(frm, "credit_account", values.credit_account || "");
			if (!frm.doc.amount) {
				set_value_if_changed(frm, "amount", values.donation_amount || 0);
			}
		});
}
