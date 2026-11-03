frappe.ui.form.on("Donation Book Collection", {
	setup(frm) {
		frm.set_query("book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.get_donation_book_serials",
		}));
	},

	book_serial_no(frm) {
		clear_book_assignment_details(frm);
		if (!frm.doc.book_serial_no) {
			frm.set_value("book", "");
			return;
		}

		const serial_no = frm.doc.book_serial_no;
		frappe.call({
			method: "donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.get_donation_book_assignment_for_serial",
			args: { book_serial_no: serial_no },
			callback(response) {
				if (frm.doc.book_serial_no === serial_no) {
					frm.set_value("book", response.message?.book || "");
				}
			},
		});
	},
});

function clear_book_assignment_details(frm) {
	if (frm.doc.book_assignment_details && frm.doc.book_assignment_details.length) {
		frm.clear_table("book_assignment_details");
		frm.refresh_field("book_assignment_details");
	}
}
