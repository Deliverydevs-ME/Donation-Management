frappe.ui.form.on("Maktab Payment Schedule", {
	ilaqi_maktab(frm) {
		fetch_maktab_frequency(frm);
	},

	donation_order(frm) {
		fetch_donation_order_details(frm);
	},
});

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

function fetch_donation_order_details(frm) {
	if (!frm.doc.donation_order) {
		return;
	}

	frappe.db.get_value("Donation Order", frm.doc.donation_order, ["mode_of_payment", "mohasil"]).then((response) => {
		const values = response.message || {};
		set_value_if_changed(frm, "mode_of_payment", values.mode_of_payment || "");
		set_value_if_changed(frm, "collection_person", values.mohasil || "");
	});
}
