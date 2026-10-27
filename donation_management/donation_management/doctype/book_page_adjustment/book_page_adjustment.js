// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Book Page Adjustment", {
	setup(frm) {
		frm.set_query("book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.book_page_adjustment.book_page_adjustment.get_coupon_book_serials",
			filters: {
				book: frm.doc.book || "",
			},
		}));
	},

	book(frm) {
		if (!frm.doc.book) {
			frm.set_value("book_serial_no", "");
		}
		frm.set_query("book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.book_page_adjustment.book_page_adjustment.get_coupon_book_serials",
			filters: {
				book: frm.doc.book || "",
			},
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 0) {
			return;
		}
		frm.add_custom_button(__("Add Pages"), () => show_page_range_dialog(frm), __("Actions"));
	},
});

frappe.ui.form.on("Book Page Adjustment Page", {
	page_no(frm) {
		set_affected_page_count(frm);
	},
	affected_page_details_remove(frm) {
		set_affected_page_count(frm);
	},
});

function show_page_range_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Affected Pages"),
		fields: [
			{
				fieldname: "pages",
				fieldtype: "Data",
				label: __("Pages"),
				description: __("Examples: 9,10,11 or 9-15"),
				reqd: 1,
			},
		],
		primary_action_label: __("Add"),
		primary_action(values) {
			let pages;
			try {
				pages = parse_page_selection(values.pages);
			} catch (error) {
				frappe.msgprint(error.message);
				return;
			}

			const existing_pages = new Set((frm.doc.affected_page_details || []).map((row) => Number(row.page_no)));
			pages.forEach((page_no) => {
				if (!existing_pages.has(page_no)) {
					frm.add_child("affected_page_details", { page_no });
				}
			});
			frm.refresh_field("affected_page_details");
			set_affected_page_count(frm);
			dialog.hide();
		},
	});
	dialog.show();
}

function parse_page_selection(value) {
	const pages = new Set();
	for (const entry of String(value).split(",")) {
		const part = entry.trim();
		const range = part.match(/^(\d+)\s*-\s*(\d+)$/);
		if (range) {
			const start = Number(range[1]);
			const end = Number(range[2]);
			if (!start || start > end) {
				throw new Error(__("Each page range must begin with a positive page number and end at the same or a later page."));
			}
			for (let page_no = start; page_no <= end; page_no += 1) {
				pages.add(page_no);
			}
			continue;
		}

		if (!/^\d+$/.test(part) || !Number(part)) {
			throw new Error(__("Enter page numbers as 9,10,11 or a range such as 9-15."));
		}
		pages.add(Number(part));
	}
	return [...pages].sort((first, second) => first - second);
}

function set_affected_page_count(frm) {
	frm.set_value("affected_pages", (frm.doc.affected_page_details || []).length);
}
