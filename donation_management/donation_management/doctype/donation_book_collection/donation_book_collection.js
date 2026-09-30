frappe.ui.form.on("Donation Book Collection", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status !== "Submitted" || !frm.has_perm("write")) {
			return;
		}

		frm.add_custom_button(__("Reopen"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Reopen Donation Book Collection"),
				fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }],
				primary_action_label: __("Reopen"),
				primary_action(values) {
					frm.call("donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.reopen_collection", {
						collection: frm.doc.name,
						reason: values.reason,
						freeze: true,
					}).then(() => {
						dialog.hide();
						frm.reload_doc();
					});
				},
			});
			dialog.show();
		});
	},
});
