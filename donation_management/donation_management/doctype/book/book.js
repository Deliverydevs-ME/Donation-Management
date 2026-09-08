// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

const coupon_colors = {
	Zakat: "Green",
	Atiya: "Blue",
	Fitra: "Purple",
	Fidya: "Orange",
};
const denominations = [10, 20, 50, 100, 500, 1000, 5000];
const book_type_coupon = "Coupon Book";
const book_type_donation = "Donation Book";
const mohasil_employee_filters = {
	status: "Active",
	designation: "Mohasil",
};

frappe.ui.form.on("Book", {
	setup(frm) {
		frm.set_query("item", () => ({
			query: "donation_management.donation_management.doctype.book.book.get_book_items",
			filters: {
				book_type: frm.doc.book_type,
			},
		}));

		frm.set_query("book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.book.book.get_available_book_serial_nos",
			filters: {
				item: frm.doc.item,
				warehouse: frm.doc.warehouse,
				book: frm.doc.name,
			},
		}));

		frm.set_query("mohasil", () => ({
			filters: mohasil_employee_filters,
		}));

		frm.set_query("issued_to_employee", () => {
			if (frm.doc.book_type === book_type_donation) {
				return {
					filters: mohasil_employee_filters,
				};
			}

			return {
				filters: {
					status: "Active",
				},
			};
		});

		frm.set_query("book_serial_no", "assigned_books", (doc, cdt, cdn) => ({
			query: "donation_management.donation_management.doctype.book.book.get_available_book_serial_nos",
			filters: {
				item: frm.doc.item,
				warehouse: frm.doc.warehouse,
				book: frm.doc.name,
				selected_serials: get_selected_assigned_serials(frm, cdn),
			},
		}));

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
	},

	refresh(frm) {
		set_book_type_visibility(frm);
		set_collection_visibility(frm);
		add_action_buttons(frm);
	},

	book_type(frm) {
		set_book_type_visibility(frm);
		set_coupon_color(frm);
		frm.set_value("item", "");
		frm.set_value("book_serial_no", "");
		frm.set_value("issued_to_employee", "");
		frm.clear_table("assigned_books");
		frm.refresh_field("assigned_books");
		check_available_stock(frm);
	},

	item(frm) {
		frm.set_value("book_serial_no", "");
		clear_assigned_books(frm);
		set_coupon_type_from_item(frm);
		check_available_stock(frm);
	},

	volunteer_name(frm) {
		set_volunteer_area(frm);
	},

	coupon_type(frm) {
		set_coupon_color(frm);
		check_available_stock(frm);
	},

	warehouse(frm) {
		frm.set_value("book_serial_no", "");
		clear_assigned_books(frm);
		check_available_stock(frm);
	},

	issued_to_employee(frm) {
		frm.clear_table("assigned_books");
		frm.refresh_field("assigned_books");
	},

	status(frm) {
		set_collection_visibility(frm);
	},

	total_pages(frm) {
		set_remaining_pages(frm);
	},

	used_pages(frm) {
		set_remaining_pages(frm);
	},

	cash_denominations_add(frm) {
		update_denomination_rows(frm);
	},

	cash_denominations_remove(frm) {
		update_denomination_rows(frm);
	},
});

frappe.ui.form.on("Book Assignment Detail", {
	book_serial_no(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.book_serial_no) {
			clear_assigned_book_row(cdt, cdn);
			return;
		}

		frappe.db.get_value(
			"Serial No",
			row.book_serial_no,
			["item_code", "warehouse"],
		).then((response) => {
			const values = response.message || {};
			frappe.model.set_value(cdt, cdn, "item", values.item_code || "");
			frappe.model.set_value(cdt, cdn, "warehouse", values.warehouse || "");
			frappe.model.set_value(cdt, cdn, "status", frm.doc.status || "");
		});
	},
});

frappe.ui.form.on("Cash Denomination", {
	denomination(frm, cdt, cdn) {
		update_denomination_row(frm, cdt, cdn);
	},

	note_count(frm, cdt, cdn) {
		update_denomination_row(frm, cdt, cdn);
	},
});

function set_coupon_color(frm) {
	if (frm.doc.book_type !== book_type_coupon) {
		frm.set_value("coupon_color", "");
		return;
	}
	frm.set_value("coupon_color", coupon_colors[frm.doc.coupon_type] || "");
}

function clear_assigned_book_row(cdt, cdn) {
	frappe.model.set_value(cdt, cdn, "item", "");
	frappe.model.set_value(cdt, cdn, "warehouse", "");
	frappe.model.set_value(cdt, cdn, "status", "");
}

function clear_assigned_books(frm) {
	frm.clear_table("assigned_books");
	frm.refresh_field("assigned_books");
}

function get_selected_assigned_serials(frm, current_row_name) {
	return (frm.doc.assigned_books || [])
		.filter((row) => row.name !== current_row_name && row.book_serial_no)
		.map((row) => row.book_serial_no);
}

function check_available_stock(frm) {
	if (![book_type_coupon, book_type_donation].includes(frm.doc.book_type) || !frm.doc.item || !frm.doc.warehouse || frm.doc.status) {
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.doctype.book.book.get_book_stock_qty",
		args: {
			item: frm.doc.item,
			warehouse: frm.doc.warehouse,
		},
		callback(response) {
			const available_stock = cint(response.message);
			if (available_stock <= 0) {
				frappe.msgprint(
					__("No stock is available for Item {0} in Warehouse {1}.", [
						frm.doc.item,
						frm.doc.warehouse,
					])
				);
				return;
			}

			frappe.show_alert({
				message: __("Available stock: {0}", [available_stock]),
				indicator: "green",
			});
		},
	});
}

function set_remaining_pages(frm) {
	const remaining_pages = cint(frm.doc.total_pages) - cint(frm.doc.used_pages);
	frm.set_value("remaining_pages", remaining_pages);
}

function set_coupon_type_from_item(frm) {
	if (frm.doc.book_type !== book_type_coupon || !frm.doc.item) {
		frm.set_value("coupon_type", "");
		set_coupon_color(frm);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.doctype.book.book.get_coupon_type_for_item",
		args: {
			item: frm.doc.item,
		},
		callback(response) {
			frm.set_value("coupon_type", response.message || "");
			set_coupon_color(frm);
			check_available_stock(frm);
		},
	});
}

function update_denomination_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", cint(row.denomination) * cint(row.note_count));
	update_denomination_rows(frm);
}

function update_denomination_rows(frm) {
	(frm.doc.cash_denominations || []).forEach((row) => {
		row.amount = cint(row.denomination) * cint(row.note_count);
	});
	frm.refresh_field("cash_denominations");
}

function set_collection_visibility(frm) {
	const show_collection =
		[book_type_coupon, book_type_donation].includes(frm.doc.book_type)
		&& ["Returned", "Closed"].includes(frm.doc.status);
	frm.toggle_display("collection_section", show_collection);
	frm.toggle_reqd("collected_amount", show_collection);
	frm.toggle_reqd("cash_denominations", show_collection);
	frm.set_df_property("collected_amount", "read_only", 1);
	frm.set_df_property("status", "read_only", 1);
}

function set_book_type_visibility(frm) {
	const is_coupon_book = frm.doc.book_type === book_type_coupon;
	const is_donation_book = frm.doc.book_type === book_type_donation;

	frm.toggle_reqd("item", is_coupon_book || is_donation_book);
	frm.toggle_reqd("book_serial_no", is_coupon_book);
	frm.toggle_reqd("issued_to_employee", is_coupon_book || is_donation_book);
	frm.toggle_reqd("coupon_value", is_coupon_book);
	frm.toggle_reqd("warehouse", is_coupon_book || is_donation_book);
	frm.toggle_reqd("total_pages", is_coupon_book);
	frm.toggle_reqd("assigned_books", is_donation_book);
	frm.toggle_display("book_serial_no", is_coupon_book);

	frm.toggle_reqd("from_receipt_no", false);
	frm.toggle_reqd("to_receipt_no", false);
}

function add_action_buttons(frm) {
	if (frm.is_new()) {
		return;
	}

	if (!frm.doc.status && frappe.user.has_role("Finance Manager")) {
		frm.add_custom_button(__("Issue"), () => issue_book(frm), __("Actions"));
	} else if (frm.doc.status === "Issued" && frm.doc.book_type === book_type_coupon) {
		frm.add_custom_button(__("Return"), () => show_return_dialog(frm), __("Actions"));
		frm.add_custom_button(__("Request Page Adjustment"), () => create_page_adjustment(frm), __("Actions"));
	} else if (frm.doc.status === "Issued" && frm.doc.book_type === book_type_donation) {
		frm.add_custom_button(__("Return"), () => show_donation_book_return_dialog(frm), __("Actions"));
	} else if (frm.doc.status === "Returned") {
		frm.add_custom_button(__("Close"), () => close_book(frm), __("Actions"));
		if (frm.doc.book_type === book_type_coupon) {
			frm.add_custom_button(__("Request Page Adjustment"), () => create_page_adjustment(frm), __("Actions"));
		}
	} else if (frm.doc.status === "Closed" && frappe.user.has_role("Finance Manager")) {
		frm.add_custom_button(__("Reopen"), () => show_reopen_dialog(frm), __("Actions"));
	}
}

function show_reopen_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Reopen Book"),
		fields: [
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason"),
				reqd: 1,
			},
		],
		primary_action_label: __("Reopen"),
		primary_action(values) {
			frappe.call({
				method: "donation_management.donation_management.doctype.book.book.reopen_book",
				args: {
					book: frm.doc.name,
					reason: values.reason,
				},
				freeze: true,
				callback() {
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
	});
	dialog.show();
}

function create_page_adjustment(frm) {
	frappe.new_doc("Book Page Adjustment", {
		book: frm.doc.name,
	});
}

function issue_book(frm) {
	frappe.call({
		method: "donation_management.donation_management.doctype.book.book.issue_book",
		args: {
			book: frm.doc.name,
		},
		freeze: true,
		callback() {
			frm.reload_doc();
		},
	});
}

function show_donation_book_return_dialog(frm) {
	const assigned_books = get_donation_book_return_rows(frm);
	if (!assigned_books.length) {
		frappe.msgprint(__("No assigned books were found for this Donation Book."));
		return;
	}

	const fields = [
		{
			fieldname: "collected_amount",
			fieldtype: "Currency",
			label: __("Total Amount Collected"),
			default: 0,
			read_only: 1,
		},
	];

	assigned_books.forEach((book_row, index) => {
		fields.push({
			fieldname: `book_section_${index}`,
			fieldtype: "Section Break",
			label: __("Cash Denominations for {0}", [book_row.book_serial_no]),
		});
		fields.push({
			fieldname: `book_serial_no_${index}`,
			fieldtype: "Data",
			label: __("Book Serial No"),
			default: book_row.book_serial_no,
			read_only: 1,
		});
		fields.push({
			fieldname: `book_column_${index}`,
			fieldtype: "Column Break",
		});
		fields.push({
			fieldname: `collected_amount_${index}`,
			fieldtype: "Currency",
			label: __("Collected Amount"),
			reqd: 1,
			non_negative: 1,
			onchange: () => update_donation_book_return_totals(dialog, assigned_books),
		});
		fields.push({
			fieldname: `denomination_section_${index}`,
			fieldtype: "Section Break",
			label: __("Denominations"),
		});
		denominations.forEach((denomination) => {
			fields.push({
				fieldname: `denomination_${index}_${denomination}`,
				fieldtype: "Int",
				label: __("{0} Rs Notes", [denomination]),
				default: 0,
				non_negative: 1,
				onchange: () => update_donation_book_return_totals(dialog, assigned_books),
			});
		});
		fields.push({
			fieldname: `denomination_total_${index}`,
			fieldtype: "Currency",
			label: __("Denomination Total"),
			read_only: 1,
		});
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Return Donation Book"),
		fields,
		primary_action_label: __("Return"),
		primary_action(values) {
			update_donation_book_return_totals(dialog, assigned_books);
			if (!validate_donation_book_return_collections(dialog, assigned_books)) {
				return;
			}

			const book_collections = get_donation_book_return_collections(values, assigned_books);

			frappe.call({
				method: "donation_management.donation_management.doctype.book.book.return_donation_book",
				args: {
					book: frm.doc.name,
					book_collections,
				},
				freeze: true,
				callback() {
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
	});

	dialog.show();
	update_donation_book_return_totals(dialog, assigned_books);
}

function set_volunteer_area(frm) {
	if (!frm.doc.volunteer_name) {
		frm.set_value("volunteer_area", "");
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.doctype.book.book.get_volunteer_area",
		args: {
			volunteer_name: frm.doc.volunteer_name,
		},
		callback(response) {
			frm.set_value("volunteer_area", response.message || "");
		},
	});
}

function show_return_dialog(frm) {
	frappe.call({
		method: "donation_management.donation_management.api.get_collection_cash_accounting_defaults",
		args: {
			source_type: "Book",
			donation_type: frm.doc.coupon_type,
		},
		callback(response) {
			build_return_dialog(frm, response.message || {});
		},
	});
}

function build_return_dialog(frm, accounting_defaults) {
	const fields = [
		{
			fieldname: "used_pages",
			fieldtype: "Int",
			label: __("Used Pages"),
			reqd: 1,
			non_negative: 1,
			onchange: () => {
				update_return_collected_amount(dialog, frm);
				update_return_denomination_total(dialog);
			},
		},
		{
			fieldname: "coupon_value",
			fieldtype: "Currency",
			label: __("Coupon Value"),
			default: frm.doc.coupon_value,
			read_only: 1,
		},
		{
			fieldname: "collected_amount",
			fieldtype: "Currency",
			label: __("Total Amount Collected"),
			default: 0,
			read_only: 1,
			reqd: 1,
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
			onchange: () => update_return_denomination_total(dialog),
		});
	});

	fields.push({
		fieldname: "denomination_total",
		fieldtype: "Currency",
		label: __("Denomination Total"),
		read_only: 1,
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Return Book"),
		fields,
		primary_action_label: __("Return"),
		primary_action(values) {
			if (!validate_return_denomination_total(dialog, frm)) {
				return;
			}

			const denomination_rows = denominations.map((denomination) => ({
				denomination,
				note_count: cint(values[`denomination_${denomination}`]),
			}));

			frappe.call({
				method: "donation_management.donation_management.doctype.book.book.return_book",
			args: {
				book: frm.doc.name,
				collected_amount: values.collected_amount,
				used_pages: values.used_pages,
				denominations: denomination_rows,
				mode_of_payment: values.mode_of_payment,
					debit_account: values.debit_account,
					credit_account: values.credit_account,
				},
				freeze: true,
				callback() {
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
	});

	dialog.show();
	update_return_collected_amount(dialog, frm);
	update_return_denomination_total(dialog);
}

function update_return_collected_amount(dialog, frm) {
	const used_pages = cint(dialog.get_value("used_pages"));
	const coupon_value = cint(frm.doc.coupon_value);
	dialog.set_value("collected_amount", used_pages * coupon_value);
}

function update_return_denomination_total(dialog) {
	let total = 0;
	denominations.forEach((denomination) => {
		total += denomination * flt(dialog.get_value(`denomination_${denomination}`));
	});
	dialog.set_value("denomination_total", total);
}

function validate_return_denomination_total(dialog, frm) {
	const used_pages = cint(dialog.get_value("used_pages"));
	const collected_amount = flt(dialog.get_value("collected_amount"));
	const denomination_total = flt(dialog.get_value("denomination_total"));

	if (used_pages <= 0 || collected_amount <= 0) {
		frappe.msgprint(__("Used Pages must be greater than zero."));
		return false;
	}

	if (used_pages > cint(frm.doc.total_pages)) {
		frappe.msgprint(__("Used Pages cannot exceed Total Pages."));
		return false;
	}

	const expected_amount = cint(dialog.get_value("used_pages")) * cint(frm.doc.coupon_value);
	if (collected_amount !== expected_amount) {
		frappe.msgprint(
			__("Total Amount Collected must be {0} because Used Pages x Coupon Value is {1} x {2}.", [
				format_currency(expected_amount),
				cint(dialog.get_value("used_pages")),
				cint(frm.doc.coupon_value),
			])
		);
		return false;
	}

	if (collected_amount !== denomination_total) {
		frappe.msgprint(
			__("Denomination total {0} must match Total Amount Collected {1}.", [
				format_currency(denomination_total),
				format_currency(collected_amount),
			])
		);
		return false;
	}

	return true;
}

function get_donation_book_return_rows(frm) {
	return (frm.doc.assigned_books || []).filter((row) => row.book_serial_no);
}

function update_donation_book_return_totals(dialog, assigned_books) {
	let total_collected_amount = 0;
	assigned_books.forEach((_book_row, index) => {
		const collected_amount = flt(dialog.get_value(`collected_amount_${index}`));
		const denomination_total = get_donation_book_row_denomination_total(dialog, index);
		total_collected_amount += collected_amount;
		dialog.set_value(`denomination_total_${index}`, denomination_total);
	});
	dialog.set_value("collected_amount", total_collected_amount);
}

function get_donation_book_row_denomination_total(dialog, index) {
	let total = 0;
	denominations.forEach((denomination) => {
		total += denomination * cint(dialog.get_value(`denomination_${index}_${denomination}`));
	});
	return total;
}

function validate_donation_book_return_collections(dialog, assigned_books) {
	let grand_total = 0;
	for (let index = 0; index < assigned_books.length; index += 1) {
		const book_serial_no = assigned_books[index].book_serial_no;
		const collected_amount = flt(dialog.get_value(`collected_amount_${index}`));
		const denomination_total = flt(dialog.get_value(`denomination_total_${index}`));

		if (collected_amount <= 0) {
			frappe.msgprint(__("Collected Amount must be greater than zero for Book Serial No {0}.", [book_serial_no]));
			return false;
		}

		if (collected_amount !== denomination_total) {
			frappe.msgprint(
				__("Denomination total {0} must match Collected Amount {1} for Book Serial No {2}.", [
					format_currency(denomination_total),
					format_currency(collected_amount),
					book_serial_no,
				])
			);
			return false;
		}

		grand_total += collected_amount;
	}

	if (grand_total <= 0) {
		frappe.msgprint(__("Total Amount Collected must be greater than zero."));
		return false;
	}
	return true;
}

function get_donation_book_return_collections(values, assigned_books) {
	return assigned_books.map((book_row, index) => {
		const collection = {
			book_serial_no: book_row.book_serial_no,
			collected_amount: flt(values[`collected_amount_${index}`]),
		};
		denominations.forEach((denomination) => {
			collection[`denomination_${denomination}`] = cint(values[`denomination_${index}_${denomination}`]);
		});
		return collection;
	});
}

function close_book(frm) {
	frappe.call({
		method: "donation_management.donation_management.doctype.book.book.close_book",
		args: {
			book: frm.doc.name,
		},
		freeze: true,
		callback() {
			frm.reload_doc();
		},
	});
}
