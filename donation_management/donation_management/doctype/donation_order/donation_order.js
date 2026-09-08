// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

const sponsorship_days_in_month = 30;
const prisoner_program_suffix = " - Prisoner";
const allowed_sponsorship_purposes = [
	"Sponsorship - Prisoner",
	"Sponsorship - Student",
	"Sponsorship - MTC",
	"Sponsorship - Maktab",
];
const bank_draft_mode_of_payment = "Bank Draft";
const mohasil_employee_filters = {
	status: "Active",
	designation: "Mohasil",
};

frappe.ui.form.on("Donation Order", {
	setup(frm) {
		frm.set_query("donor_name", () => {
			return {};
		});

		frm.set_query("mode_of_payment", () => {
			return {
				filters: {
					enabled: 1,
				},
			};
		});

		frm.set_query("mohasil", () => ({
			filters: mohasil_employee_filters,
		}));

		frm.set_query("donation_location", () => ({}));

		frm.set_query("donation_book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.book.book.get_mohasil_donation_book_serials",
			filters: {
				mohasil: frm.doc.mohasil || "",
			},
		}));

		frm.set_query("bank_account", () => {
			const filters = { is_group: 0, account_type: "Bank" };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("debit_account", () => {
			const filters = {
				is_group: 0,
			};

			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}

			if (["Cash", "Bank"].includes(frm.doc.mode_of_payment_type)) {
				filters.account_type = frm.doc.mode_of_payment_type;
			}

			if (is_bank_draft_mode(frm) && frm.doc.donation_type) {
				filters.account_name = ["like", `%${get_receiving_account_donation_type(frm.doc.donation_type)}%`];
			}

			return { filters };
		});

		frm.set_query("credit_account", () => {
			const filters = { is_group: 0, root_type: ["in", ["Income", "Liability", "Equity"]] };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("donation_purpose", () => {
			const filters = {
				is_group: 0,
			};

			if (frm.doc.purpose_of_donation) {
				filters.purpose_group = frm.doc.purpose_of_donation;
			}

			if (frm.doc.purpose_of_donation === "Sponsorship") {
				filters.name = ["in", allowed_sponsorship_purposes];
			}

			return { filters };
		});

		frm.set_query("donation_purpose", "purpose_details", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			const filters = { is_group: 0 };
			if (row.donation_category) {
				filters.purpose_group = row.donation_category;
			}
			if (row.donation_category === "Sponsorship") {
				filters.name = ["in", allowed_sponsorship_purposes];
			}
			return { filters };
		});

		frm.set_query("credit_account", "purpose_details", () => {
			const filters = { is_group: 0, root_type: ["in", ["Income", "Liability", "Equity"]] };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("debit_account", "purpose_details", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			const filters = { is_group: 0 };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			if (["Cash", "Bank"].includes(frm.doc.mode_of_payment_type)) {
				filters.account_type = frm.doc.mode_of_payment_type;
			}
			if (is_bank_draft_mode(frm) && row.donation_type) {
				filters.account_name = ["like", `%${get_receiving_account_donation_type(row.donation_type)}%`];
			}
			return { filters };
		});

		frm.set_query("sponsorship_program", "sponsorship_students", () => {
			const program_modes = get_sponsorship_program_modes(frm);
			if (program_modes.student && !program_modes.prisoner) {
				return { filters: [["Sponsorship Program", "name", "not like", `%${prisoner_program_suffix}`]] };
			}
			if (program_modes.prisoner && !program_modes.student) {
				return { filters: [["Sponsorship Program", "name", "like", `%${prisoner_program_suffix}`]] };
			}
			return {};
		});
	},

	refresh(frm) {
		add_donation_order_action_buttons(frm);
		add_esaal_e_sawab_action(frm);
		hide_legacy_purpose_fields(frm);
		toggle_purpose_grid_debit_account(frm);
		toggle_parent_debit_account(frm);
		update_beneficiary_fields(frm, false);
		render_donor_program_enrollments(frm);
		apply_sponsorship_table_rules(frm);
		toggle_mohasil_details(frm);

		if (frm.doc.docstatus === 1) {
			return;
		}

		update_total_amount_from_purpose_details(frm);
		if (frm.is_new()) {
			set_previous_sponsorship_balance(frm);
			update_accounting_fields(frm);
			auto_allocate_sponsorship_amounts(frm, true);
		} else {
			auto_allocate_sponsorship_amounts(frm, false);
		}
		set_sponsorship_totals(frm);
	},

	company(frm) {
		set_value_if_changed(frm, "debit_account", "");
		set_value_if_changed(frm, "credit_account", "");
		set_value_if_changed(frm, "accounting_cost_center", "");
		refresh_all_purpose_rows(frm);
		update_accounting_fields(frm, true);
	},

	mode_of_payment(frm) {
		set_value_if_changed(frm, "mode_of_payment_type", "");
		set_value_if_changed(frm, "bank_account", "");
		set_value_if_changed(frm, "debit_account", "");
		if (frm.doc.mode_of_payment !== "Cheque") {
			set_value_if_changed(frm, "is_post_dated_cheque", 0);
			set_value_if_changed(frm, "cheque_number", "");
			set_value_if_changed(frm, "cheque_deposit_date", "");
		}
		clear_purpose_row_debit_accounts(frm);
		update_accounting_fields(frm, true);
	},

	bank_account(frm) {
		apply_deposit_account_to_purpose_rows(frm);
		toggle_parent_debit_account(frm);
	},

	debit_account(frm) {
		apply_parent_debit_account_to_purpose_rows(frm);
	},

	donation_type(frm) {
		set_value_if_changed(frm, "credit_account", "");
		set_value_if_changed(frm, "accounting_cost_center", "");
		if (is_bank_draft_mode(frm)) {
			set_value_if_changed(frm, "debit_account", "");
			clear_purpose_row_debit_accounts(frm);
		}
		set_previous_sponsorship_balance(frm);
		update_accounting_fields(frm);
	},

	donor_email(frm) {
		set_donor_from_email(frm);
	},

	donor_phone_number(frm) {
		set_donor_from_phone(frm);
	},

	donor_name(frm) {
		set_donor_details_from_name(frm);
	},

	donation_posting_date(frm) {
		set_effective_donation_location(frm);
	},

	is_mohasil_collection(frm) {
		toggle_mohasil_details(frm);
		if (frm.doc.is_mohasil_collection) {
			set_mohasil_from_selected_donor(frm);
			set_effective_donation_location(frm);
		}
	},

	mohasil(frm) {
		if (frm.doc.donation_book_serial_no) {
			frm.set_value("donation_book_serial_no", "");
		}
		if (frm.doc.donation_book) {
			frm.set_value("donation_book", "");
		}
		set_effective_donation_location(frm);
	},

	donation_book_serial_no(frm) {
		set_donation_book_from_serial(frm);
		check_all_manual_receipt_duplicates(frm);
	},

	cash_denominations_add(frm) {
		update_cash_denomination_rows(frm);
	},

	cash_denominations_remove(frm) {
		update_cash_denomination_rows(frm);
	},

	purpose_of_donation(frm) {
		set_value_if_changed(frm, "donation_purpose", "");
		set_value_if_changed(frm, "purpose_path", "");
		set_value_if_changed(frm, "requires_student", 0);
		set_value_if_changed(frm, "requires_prisoner", 0);
		set_value_if_changed(frm, "student_mode", "");
		update_beneficiary_fields(frm, true);
		set_previous_sponsorship_balance(frm);
		set_sponsorship_totals(frm);
	},

	donation_purpose(frm) {
		if (!frm.doc.donation_purpose) {
			set_value_if_changed(frm, "credit_account", "");
			set_value_if_changed(frm, "accounting_cost_center", "");
			update_beneficiary_fields(frm, true);
			return;
		}

		frappe.db
			.get_value("Donation Purpose", frm.doc.donation_purpose, [
				"purpose_path",
				"requires_student",
				"requires_prisoner",
				"student_mode",
			])
			.then((response) => {
				const purpose = response.message || {};
				set_value_if_changed(frm, "purpose_path", purpose.purpose_path || "");
				set_value_if_changed(frm, "requires_student", purpose.requires_student || 0);
				set_value_if_changed(frm, "requires_prisoner", purpose.requires_prisoner || 0);
				set_value_if_changed(frm, "student_mode", purpose.student_mode || "");
				update_beneficiary_fields(frm, true);
				set_previous_sponsorship_balance(frm);
				set_sponsorship_totals(frm);
				update_accounting_fields(frm);
			});
	},

	student_name(frm) {
		set_student_total_donation(frm);
	},

	donation_amount(frm) {
		set_student_total_donation(frm);
		set_sponsorship_totals(frm);
	},

	purpose_details_add(frm) {
		sync_primary_purpose_fields(frm);
		update_total_amount_from_purpose_details(frm);
	},

	purpose_details_remove(frm) {
		sync_primary_purpose_fields(frm);
		update_total_amount_from_purpose_details(frm);
		set_sponsorship_totals(frm);
	},

	sponsorship_students_add(frm) {
		apply_sponsorship_table_rules(frm);
		auto_allocate_sponsorship_amounts(frm, true);
		set_sponsorship_totals(frm);
	},

	sponsorship_students_remove(frm) {
		set_sponsorship_totals(frm);
	},

});

function add_esaal_e_sawab_action(frm) {
	if (frm.doc.docstatus !== 0 || !frm.doc.donor_name) {
		return;
	}

	frm.add_custom_button(__("Refresh from Donor"), () => {
		if ((frm.doc.esaal_e_sawab || []).length) {
			frappe.confirm(
				__("Existing Esaal e Sawab rows will be replaced from the selected Donor. Continue?"),
				() => load_esaal_e_sawab_from_donor(frm, true)
			);
			return;
		}

		load_esaal_e_sawab_from_donor(frm, true);
	}, __("Esaal e Sawab"));
}

frappe.ui.form.on("Cash Denomination", {
	denomination(frm, cdt, cdn) {
		update_cash_denomination_row(frm, cdt, cdn);
	},

	note_count(frm, cdt, cdn) {
		update_cash_denomination_row(frm, cdt, cdn);
	},
});

frappe.ui.form.on("Donation Order Purpose Detail", {
	donation_type(frm, cdt, cdn) {
		if (!is_deposit_account_mode(frm)) {
			set_child_value_if_changed(cdt, cdn, "debit_account", "");
		}
		if (is_bank_draft_mode(frm)) {
			set_value_if_changed(frm, "debit_account", "");
		}
		update_purpose_row_details(frm, cdt, cdn);
	},

	donation_category(frm, cdt, cdn) {
		set_child_value_if_changed(cdt, cdn, "donation_purpose", "");
		set_child_value_if_changed(cdt, cdn, "purpose_path", "");
		if (!is_deposit_account_mode(frm)) {
			set_child_value_if_changed(cdt, cdn, "debit_account", "");
		}
		set_child_value_if_changed(cdt, cdn, "credit_account", "");
		set_child_value_if_changed(cdt, cdn, "cost_center", "");
		update_purpose_row_details(frm, cdt, cdn);
	},

	donation_purpose(frm, cdt, cdn) {
		update_purpose_row_details(frm, cdt, cdn);
	},

	amount(frm) {
		update_total_amount_from_purpose_details(frm);
		sync_primary_purpose_fields(frm);
		auto_allocate_sponsorship_amounts(frm, true);
		set_sponsorship_totals(frm);
	},

	debit_account(frm) {
		sync_primary_purpose_fields(frm);
	},

	manual_receipt_number(frm, cdt, cdn) {
		check_manual_receipt_duplicate(frm, cdt, cdn);
	},
});

frappe.ui.form.on("Donation Order Sponsorship Allocation", {
	quantity(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		set_sponsorship_row_totals(frm, cdt, cdn, row.parentfield, get_sponsorship_row_quantity(row));
		auto_allocate_sponsorship_amounts(frm, true);
	},

	allocated_amount(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		set_sponsorship_row_totals(frm, cdt, cdn, row.parentfield, get_sponsorship_row_quantity(row));
	},

	sponsorship_program(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frm.__donor_program_prior_paid_key = null;
		set_program_details(frm, cdt, cdn, row.parentfield, get_sponsorship_row_quantity(row));
		set_auto_sponsorship_quantity(frm, cdt, cdn, row);
	},
});

function set_donor_from_email(frm) {
	if (!frm.doc.donor_email) {
		return;
	}

	if (!frm.doc.donor_email.includes("@")) {
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_by_email",
		args: {
			donor_email: frm.doc.donor_email,
		},
		callback(response) {
			const donor = response.message || {};
			if (donor.invalid) {
				return;
			}

			if (!donor.name) {
				show_create_donor_message(frm, {
					donor_email: frm.doc.donor_email,
					donor_phone_number: frm.doc.donor_phone_number,
				});
				set_value_if_changed(frm, "donor_name", "");
				set_value_if_changed(frm, "name_on_donation_slip", "");
				set_previous_sponsorship_balance(frm);
				render_donor_program_enrollments(frm);
				return;
			}

			set_value_if_changed(frm, "donor_email", donor.donor_email || frm.doc.donor_email);
			set_value_if_changed(frm, "donor_name", donor.name);
			set_value_if_changed(frm, "donor_phone_number", donor.donor_phone_number || "");
			set_value_if_changed(frm, "referred_by_trustee", donor.referred_by_trustee || "");
			if (frm.doc.is_mohasil_collection && !frm.doc.mohasil) {
				set_value_if_changed(frm, "mohasil", donor.mohasil || "");
			}
			if (!frm.doc.name_on_donation_slip) {
				set_value_if_changed(frm, "name_on_donation_slip", donor.donor_name || donor.name);
			}
			set_previous_sponsorship_balance(frm);
			render_donor_program_enrollments(frm);
		},
	});
}

function render_donor_program_enrollments(frm) {
	const field = frm.get_field("donor_program_enrollments_html");
	if (!field) {
		return;
	}

	if (!frm.doc.donor_name) {
		field.$wrapper.html("");
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_program_enrollments",
		args: { donor: frm.doc.donor_name },
		callback(response) {
			const enrollments = response.message || [];
			if (!enrollments.length) {
				field.$wrapper.html(
					`<div class="text-muted small">${__("No sponsorship program enrollments found for this donor.")}</div>`
				);
				return;
			}

			const selected_program = frm.__selected_donor_program || "";
			const rows = enrollments
				.map((item) => {
					const program_raw = item.sponsorship_program || "";
					const program = frappe.utils.escape_html(program_raw);
					const purpose = frappe.utils.escape_html(item.donation_purpose || "-");
					const qty = item.student_quantity || 0;
					const total_amount = format_currency_value(item.total_program_amount);
					const paid_amount = format_currency_value(item.total_paid);
					const balance = format_currency_value(item.balance);
					const is_selected = selected_program === program_raw;
					const row_class = is_selected ? "table-primary" : "";

					return (
						`<tr class="${row_class}" data-program="${program}">` +
						`<td>${program}</td>` +
						`<td>${purpose}</td>` +
						`<td class="text-right">${qty}</td>` +
						`<td class="text-right">${total_amount}</td>` +
						`<td class="text-right">${paid_amount}</td>` +
						`<td class="text-right">${balance}</td>` +
						`<td class="text-center">` +
						`<button type="button" class="btn btn-xs ${is_selected ? "btn-primary" : "btn-default"} btn-select-donor-program" data-program="${program}">` +
						`${is_selected ? __("Selected") : __("Select")}</button>` +
						`</td></tr>`
					);
				})
				.join("");

			field.$wrapper.html(`
				<div class="small text-muted">${__("Donor is enrolled in the following programs:")}</div>
				<table class="table table-bordered table-sm donor-program-enrollment-table" style="margin-top: 8px;">
					<thead><tr>
						<th>${__("Program")}</th>
						<th>${__("Purpose")}</th>
						<th class="text-right">${__("Qty")}</th>
						<th class="text-right">${__("Total Amount")}</th>
						<th class="text-right">${__("Paid Amount")}</th>
						<th class="text-right">${__("Balance")}</th>
						<th class="text-center">${__("Action")}</th>
					</tr></thead>
					<tbody>${rows}</tbody>
				</table>
				<div class="text-muted small">${__("Click Select to load purpose details and sponsorship rows for that program.")}</div>
			`);

			field.$wrapper.find(".btn-select-donor-program").off("click").on("click", function () {
				const sponsorship_program = $(this).attr("data-program");
				prompt_apply_donor_program_selection(frm, sponsorship_program);
			});
		},
	});
}

function format_currency_value(value) {
	return frappe.format(value || 0, { fieldtype: "Currency" });
}

function prompt_apply_donor_program_selection(frm, sponsorship_program) {
	const has_existing_lines =
		(frm.doc.purpose_details || []).length > 0 || (frm.doc.sponsorship_students || []).length > 0;

	if (has_existing_lines) {
		frappe.confirm(
			__(
				"Applying program {0} will replace existing Purpose Details and Sponsorship rows. Continue?",
				[sponsorship_program]
			),
			() => apply_donor_program_selection(frm, sponsorship_program)
		);
		return;
	}

	apply_donor_program_selection(frm, sponsorship_program);
}

function apply_donor_program_selection(frm, sponsorship_program) {
	frappe.call({
		method: "donation_management.donation_management.api.get_donor_program_donation_details",
		args: {
			donor: frm.doc.donor_name,
			sponsorship_program,
		},
		callback(response) {
			const details = response.message || {};
			if (!details.purpose_details?.length) {
				frappe.msgprint(__("No purpose details found for this program."));
				return;
			}

			frm.__selected_donor_program = sponsorship_program;
			frm.__applying_donor_program = true;
			frm.__donor_program_prior_paid = frm.__donor_program_prior_paid || {};
			frm.__donor_program_prior_paid[sponsorship_program] = flt(details.total_paid);
			frm.__donor_program_prior_paid_key = null;
			frm.clear_table("purpose_details");
			frm.clear_table("sponsorship_students");

			details.purpose_details.forEach((row) => {
				const child = frm.add_child("purpose_details");
				child.donation_type = row.donation_type || details.donation_type || "";
				child.donation_category = row.donation_category || details.purpose_of_donation || "Sponsorship";
				child.donation_purpose = row.donation_purpose || details.donation_purpose || "";
				child.purpose_path = row.purpose_path || "";
				child.amount = 0;
			});

			(details.sponsorship_students || []).forEach((row) => {
				const child = frm.add_child("sponsorship_students");
				child.sponsorship_program = row.sponsorship_program;
				child.quantity = cint(row.quantity) || 1;
			});

			sync_primary_purpose_fields(frm, true);

			const donation_purpose =
				details.donation_purpose || details.purpose_details[0]?.donation_purpose;

			const finish_program_selection = () => {
				frm.refresh_field("purpose_details");
				frm.refresh_field("sponsorship_students");
				update_beneficiary_fields(frm, false);
				update_accounting_fields(frm);

				(frm.doc.purpose_details || []).forEach((row) => {
					update_purpose_row_details(frm, row.doctype, row.name);
				});

				(frm.doc.sponsorship_students || []).forEach((row) => {
					set_program_details(
						frm,
						row.doctype,
						row.name,
						"sponsorship_students",
						cint(row.quantity)
					);
				});

				set_previous_sponsorship_balance(frm);
				set_sponsorship_totals(frm);
				render_donor_program_enrollments(frm);
				frm.__applying_donor_program = false;

				frappe.show_alert({
					message: __("Program {0} loaded. Enter paid amount in Purpose Details.", [
						sponsorship_program,
					]),
					indicator: "green",
				});
			};

			if (!donation_purpose) {
				finish_program_selection();
				return;
			}

			frappe.db
				.get_value("Donation Purpose", donation_purpose, [
					"requires_student",
					"requires_prisoner",
					"student_mode",
				])
				.then((purpose_response) => {
					const purpose = purpose_response.message || {};
					frm.doc.requires_student = purpose.requires_student || 0;
					frm.doc.requires_prisoner = purpose.requires_prisoner || 0;
					frm.doc.student_mode = purpose.student_mode || "";
					finish_program_selection();
				});
		},
	});
}

function set_auto_sponsorship_quantity(frm, cdt, cdn, row) {
	if (!frm.doc.donor_name || !row.sponsorship_program) {
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_program_quantity",
		args: {
			donor: frm.doc.donor_name,
			sponsorship_program: row.sponsorship_program,
		},
		callback(response) {
			const quantity = cint(response.message);
			if (quantity > 0) {
				set_child_value_if_changed(cdt, cdn, "quantity", quantity);
				set_sponsorship_row_totals(frm, cdt, cdn, row.parentfield, quantity);
				auto_allocate_sponsorship_amounts(frm, true);
			}
		},
	});
}

function update_accounting_fields(frm, overwrite_debit_account = false) {
	const request_key = get_accounting_request_key({
		company: frm.doc.company,
		donation_type: frm.doc.donation_type,
		donation_purpose: frm.doc.donation_purpose,
		mode_of_payment: frm.doc.mode_of_payment,
	});
	frm.__last_accounting_request_key = request_key;

	frappe.call({
		method: "donation_management.donation_management.api.get_donation_order_accounting_details",
		args: {
			company: frm.doc.company,
			donation_type: frm.doc.donation_type,
			donation_purpose: frm.doc.donation_purpose,
			mode_of_payment: frm.doc.mode_of_payment,
		},
		callback(response) {
			if (frm.__last_accounting_request_key !== request_key) {
				return;
			}

			const details = response.message || {};
			if (!frm.doc.company && details.company) {
				set_value_if_changed(frm, "company", details.company);
			}

			if (!frm.doc.currency && details.currency) {
				set_value_if_changed(frm, "currency", details.currency);
			}

			set_value_if_changed(frm, "mode_of_payment_type", details.mode_of_payment_type || "");
			toggle_purpose_grid_debit_account(frm);
			toggle_parent_debit_account(frm);

			if (is_deposit_account_mode(frm)) {
				apply_deposit_account_to_purpose_rows(frm);
			} else {
				set_value_if_changed(frm, "bank_account", "");
				if (overwrite_debit_account || !frm.doc.debit_account) {
					set_value_if_changed(frm, "debit_account", details.debit_account || "");
				}
			}

			set_value_if_changed(frm, "credit_account", details.credit_account || "");
			set_value_if_changed(frm, "accounting_cost_center", details.cost_center || "");
			refresh_all_purpose_rows(frm);
		},
	});
}

function add_donation_order_action_buttons(frm) {
	if (frm.is_new() || !frm.doc.donor_name) {
		return;
	}

	const action_group = __("Action");

	frm.add_custom_button(__("History"), () => {
		frappe.set_route("List", "Donation Order", {
			donor_name: frm.doc.donor_name,
		});
	}, action_group);

	frm.add_custom_button(__("Open Donor"), () => {
		frappe.set_route("Form", "Donor", frm.doc.donor_name);
	}, action_group);

	frm.add_custom_button(__("Donation Statement"), () => {
		frappe.set_route("query-report", "Donor Donation Statement", {
			donor: frm.doc.donor_name,
		});
	}, action_group);

	frm.add_custom_button(__("Donor Last Slip"), () => {
		open_donor_last_slip(frm);
	}, action_group);

	frm.add_custom_button(__("Previous Donor Balance Summary"), () => {
		frappe.set_route("query-report", "Donor Balance Report", {
			donor: frm.doc.donor_name,
		});
	}, action_group);

	if (can_create_pdc_journal_entry(frm)) {
		frm.add_custom_button(__("Create Payment Entry"), () => {
			create_pdc_journal_entry(frm);
		}, action_group);
	}

	if (can_issue_computerized_receipt(frm)) {
		frm.add_custom_button(__("Issue Computerized Receipt"), () => {
			issue_computerized_receipt(frm);
		}, action_group);
	}
}

function can_create_pdc_journal_entry(frm) {
	return (
		!frm.is_new() &&
		frm.doc.docstatus === 1 &&
		frm.doc.mode_of_payment === "Cheque" &&
		frm.doc.is_post_dated_cheque &&
		frm.doc.pdc_status === "Pending Deposit" &&
		!frm.doc.journal_entry
	);
}

function create_pdc_journal_entry(frm) {
	if (frm.doc.cheque_deposit_date && frm.doc.cheque_deposit_date > frappe.datetime.get_today()) {
		frappe.msgprint(
			__("Payment Entry can only be created on or after {0}.", [
				frappe.datetime.str_to_user(frm.doc.cheque_deposit_date),
			])
		);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.doctype.donation_order.donation_order.create_pdc_journal_entry",
		args: {
			donation_order: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Creating Payment Entry..."),
		callback(response) {
			const result = response.message || {};
			frappe.msgprint(
				__("Payment Entry created. Journal Entry {0} posted.", [
					result.journal_entry || "",
				])
			);
			frm.reload_doc();
		},
	});
}

function can_issue_computerized_receipt(frm) {
	return (
		!frm.is_new() &&
		frm.doc.docstatus === 1 &&
		!frm.doc.computerized_receipt
	);
}

function issue_computerized_receipt(frm) {
	frappe.call({
		method: "donation_management.donation_management.doctype.donation_order.donation_order.issue_computerized_receipt",
		args: {
			donation_order: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Issuing computerized receipt..."),
		callback(response) {
			const result = response.message || {};
			frappe.msgprint(__("Computerized receipt issued: {0}", [result.computerized_receipt || frm.doc.name]));
			frm.reload_doc();
		},
	});
}

function open_donor_last_slip(frm) {
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Donation Order",
			fields: ["name"],
			filters: [
				["donor_name", "=", frm.doc.donor_name],
				["name", "!=", frm.doc.name || ""],
				["docstatus", "!=", 2],
			],
			order_by: "donation_posting_date desc, creation desc",
			limit_page_length: 1,
		},
		callback(response) {
			const last_slip = (response.message || [])[0];
			if (!last_slip) {
				frappe.msgprint(__("No previous donation slip found for this donor."));
				return;
			}

			frappe.set_route("Form", "Donation Order", last_slip.name);
		},
	});
}

function hide_legacy_purpose_fields(frm) {
	["donation_type", "purpose_of_donation", "donation_purpose", "purpose_path"].forEach((fieldname) => {
		frm.toggle_display(fieldname, false);
	});
}

function toggle_purpose_grid_debit_account(frm) {
	const show_row_debit_account = Boolean(frm.doc.mode_of_payment_type) || is_deposit_account_mode(frm);
	const cash_mode = frm.doc.mode_of_payment_type === "Cash";
	const manual_bank_mode = is_manual_bank_mode(frm);
	const bank_draft_mode = is_bank_draft_mode(frm);
	const deposit_account_mode = is_deposit_account_mode(frm);
	const grid = frm.fields_dict.purpose_details && frm.fields_dict.purpose_details.grid;
	if (!grid) {
		return;
	}

	grid.update_docfield_property("debit_account", "hidden", show_row_debit_account ? 0 : 1);
	grid.update_docfield_property("debit_account", "reqd", show_row_debit_account ? 1 : 0);
	grid.update_docfield_property("debit_account", "read_only", cash_mode || (manual_bank_mode && !bank_draft_mode) || deposit_account_mode ? 1 : 0);
	frm.refresh_field("purpose_details");
}

function toggle_parent_debit_account(frm) {
	const cash_mode = frm.doc.mode_of_payment_type === "Cash";
	const manual_bank_mode = is_manual_bank_mode(frm);
	const bank_draft_mode = is_bank_draft_mode(frm);
	const deposit_account_mode = is_deposit_account_mode(frm);

	frm.toggle_display("debit_account", cash_mode || (manual_bank_mode && !bank_draft_mode) || deposit_account_mode);
	frm.set_df_property("debit_account", "read_only", cash_mode || deposit_account_mode ? 1 : 0);
	frm.toggle_reqd("debit_account", cash_mode || (manual_bank_mode && !bank_draft_mode));
}

function clear_purpose_row_debit_accounts(frm) {
	(frm.doc.purpose_details || []).forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, "debit_account", "");
	});
}

function apply_parent_debit_account_to_purpose_rows(frm) {
	if (frm.doc.mode_of_payment_type !== "Cash" && (!is_manual_bank_mode(frm) || is_bank_draft_mode(frm))) {
		return;
	}

	(frm.doc.purpose_details || []).forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, "debit_account", frm.doc.debit_account || "");
	});
}

function refresh_all_purpose_rows(frm) {
	(frm.doc.purpose_details || []).forEach((row) => {
		update_purpose_row_details(frm, row.doctype, row.name);
	});
}

function apply_deposit_account_to_purpose_rows(frm) {
	if (!is_deposit_account_mode(frm)) {
		return;
	}

	set_value_if_changed(frm, "debit_account", frm.doc.bank_account || "");
	(frm.doc.purpose_details || []).forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, "debit_account", frm.doc.bank_account || "");
	});
}

function update_purpose_row_details(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row) {
		return;
	}

	if (!row.donation_type || !row.donation_purpose || !frm.doc.company) {
		sync_primary_purpose_fields(frm);
		return;
	}

	const purpose_request_key = get_purpose_row_request_key(frm, row);
	row.__last_purpose_request_key = purpose_request_key;

	frappe.db
		.get_value("Donation Purpose", row.donation_purpose, [
			"purpose_path",
			"purpose_group",
			"requires_student",
			"requires_prisoner",
			"student_mode",
		])
		.then((purpose_response) => {
			const current_row = locals[cdt]?.[cdn];
			if (!current_row || current_row.__last_purpose_request_key !== purpose_request_key) {
				return;
			}

			const purpose = purpose_response.message || {};
			if (purpose.purpose_group && row.donation_category && purpose.purpose_group !== row.donation_category) {
				frappe.msgprint(
					__("Donation Purpose {0} belongs to {1}, not {2}.", [
						row.donation_purpose,
						purpose.purpose_group,
						row.donation_category,
					])
				);
				set_child_value_if_changed(cdt, cdn, "donation_purpose", "");
				return;
			}

			if (purpose.purpose_group && !row.donation_category) {
				set_child_value_if_changed(cdt, cdn, "donation_category", purpose.purpose_group);
			}
			set_child_value_if_changed(cdt, cdn, "purpose_path", purpose.purpose_path || "");
			frm.doc.requires_student = purpose.requires_student || 0;
			frm.doc.requires_prisoner = purpose.requires_prisoner || 0;
			frm.doc.student_mode = purpose.student_mode || "";

			frappe.call({
				method: "donation_management.donation_management.api.get_donation_order_accounting_details",
				args: {
					company: frm.doc.company,
					donation_type: row.donation_type,
					donation_purpose: row.donation_purpose,
					mode_of_payment: frm.doc.mode_of_payment,
				},
				callback(response) {
					const latest_row = locals[cdt]?.[cdn];
					if (!latest_row || latest_row.__last_purpose_request_key !== purpose_request_key) {
						return;
					}

					const details = response.message || {};
					if (details.mode_of_payment_type === "Cash") {
						set_child_value_if_changed(cdt, cdn, "debit_account", details.debit_account || "");
					} else if (is_deposit_account_mode(frm)) {
						set_child_value_if_changed(cdt, cdn, "debit_account", frm.doc.bank_account || "");
					} else if (details.mode_of_payment_type === "Bank") {
						set_child_value_if_changed(cdt, cdn, "debit_account", frm.doc.debit_account || details.debit_account || "");
					} else if (details.mode_of_payment_type) {
						if (!row.debit_account) {
							set_child_value_if_changed(cdt, cdn, "debit_account", details.debit_account || "");
						}
					} else {
						set_child_value_if_changed(cdt, cdn, "debit_account", "");
					}
					set_child_value_if_changed(cdt, cdn, "credit_account", details.credit_account || "");
					set_child_value_if_changed(cdt, cdn, "cost_center", details.cost_center || "");
					sync_primary_purpose_fields(frm, true);
					update_beneficiary_fields(frm, false);
				},
			});
		});
}

function sync_primary_purpose_fields(frm, sync_to_doc = false) {
	const rows = frm.doc.purpose_details || [];
	const primary_row = rows.find((row) => row.donation_category === "Sponsorship") || rows[0] || {};
	const updates = {
		donation_type: primary_row.donation_type || "",
		purpose_of_donation: primary_row.donation_category || "",
		donation_purpose: primary_row.donation_purpose || "",
		purpose_path: primary_row.purpose_path || "",
		credit_account: primary_row.credit_account || "",
		accounting_cost_center: primary_row.cost_center || "",
	};

	if (sync_to_doc) {
		Object.assign(frm.doc, updates);
	} else {
		Object.entries(updates).forEach(([fieldname, value]) => {
			set_value_if_changed(frm, fieldname, value);
		});
	}

	set_previous_sponsorship_balance(frm);
}

function update_total_amount_from_purpose_details(frm) {
	const total_amount = (frm.doc.purpose_details || []).reduce((total, row) => total + flt(row.amount), 0);
	set_value_if_changed(frm, "donation_amount", total_amount);
}

function set_donor_from_phone(frm) {
	if (!frm.doc.donor_phone_number) {
		clear_donor_details(frm);
		return;
	}

	const phone_digits = get_phone_digits(frm.doc.donor_phone_number);
	if (phone_digits.length < 10) {
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_by_phone",
		args: {
			donor_phone_number: frm.doc.donor_phone_number,
		},
		callback(response) {
			const donor = response.message || {};
			if (donor.invalid) {
				return;
			}

			if (!donor.name) {
				show_create_donor_message(frm, {
					donor_email: frm.doc.donor_email,
					donor_phone_number: frm.doc.donor_phone_number,
				});
				set_value_if_changed(frm, "donor_name", "");
				set_value_if_changed(frm, "donor_email", "");
				set_value_if_changed(frm, "name_on_donation_slip", "");
				set_value_if_changed(frm, "referred_by_trustee", "");
				set_previous_sponsorship_balance(frm);
				render_donor_program_enrollments(frm);
				return;
			}

			set_value_if_changed(frm, "donor_email", donor.donor_email || "");
			set_value_if_changed(frm, "donor_name", donor.name);
			set_value_if_changed(frm, "donor_phone_number", donor.donor_phone_number || frm.doc.donor_phone_number);
			set_value_if_changed(frm, "referred_by_trustee", donor.referred_by_trustee || "");
			if (frm.doc.is_mohasil_collection && !frm.doc.mohasil) {
				set_value_if_changed(frm, "mohasil", donor.mohasil || "");
			}
			if (!frm.doc.name_on_donation_slip) {
				set_value_if_changed(frm, "name_on_donation_slip", donor.donor_name || donor.name);
			}
			set_previous_sponsorship_balance(frm);
			render_donor_program_enrollments(frm);
		},
	});
}

function clear_donor_details(frm) {
	frm.__selected_donor_program = "";
	frm.__donor_program_prior_paid = {};
	frm.__donor_program_prior_paid_key = null;
	set_value_if_changed(frm, "donor_name", "");
	set_value_if_changed(frm, "donor_email", "");
	set_value_if_changed(frm, "name_on_donation_slip", "");
	set_value_if_changed(frm, "referred_by_trustee", "");
	set_value_if_changed(frm, "is_mohasil_collection", 0);
	set_value_if_changed(frm, "mohasil", "");
	set_value_if_changed(frm, "donation_book_serial_no", "");
	set_value_if_changed(frm, "donation_book", "");
	set_value_if_changed(frm, "manual_receipt_number", "");
	set_value_if_changed(frm, "manual_receipt_date", "");
	clear_purpose_receipt_numbers(frm);
	set_previous_sponsorship_balance(frm);
	render_donor_program_enrollments(frm);
}

function show_create_donor_message(frm, donor_details) {
	const donor_email = donor_details.donor_email || "";
	const donor_phone_number = donor_details.donor_phone_number || "";
	const identifier = donor_email || donor_phone_number;

	frappe.msgprint({
		title: __("Donor Not Found"),
		message: __("No Donor found for {0}. You can create a new Donor.", [identifier]),
		primary_action: {
			label: __("Create Donor"),
			action() {
				frappe.hide_msgprint();
				frappe.new_doc("Donor", {
					customer_type: "Walk-in",
					customer_name: frm.doc.name_on_donation_slip || "",
					donor_phone_number,
					donor_email,
					mohasil: frm.doc.is_mohasil_collection ? frm.doc.mohasil || "" : "",
				});
			},
		},
	});
}

function get_phone_digits(phone_number) {
	return String(phone_number || "").replace(/\D/g, "");
}

function set_donor_details_from_name(frm) {
	if (!frm.doc.donor_name) {
		set_value_if_changed(frm, "referred_by_trustee", "");
		set_previous_sponsorship_balance(frm);
		render_donor_program_enrollments(frm);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_details",
		args: {
			donor: frm.doc.donor_name,
		},
		callback(response) {
			const donor = response.message || {};
			set_value_if_changed(frm, "donor_email", donor.donor_email || "");
			set_value_if_changed(frm, "donor_phone_number", donor.donor_phone_number || "");
			set_value_if_changed(frm, "referred_by_trustee", donor.referred_by_trustee || "");
			set_value_if_changed(frm, "donor_pos_id", donor.donor_pos_id || "");
			set_value_if_changed(frm, "party", donor.party || "");
			set_value_if_changed(frm, "confidential_ref_co", donor.confidential_ref_co || "");
			load_esaal_e_sawab_from_donor(frm, false);
			if (frm.doc.is_mohasil_collection && !frm.doc.mohasil) {
				set_value_if_changed(frm, "mohasil", donor.mohasil || "");
			}
			if (!frm.doc.name_on_donation_slip && donor.donor_name) {
				set_value_if_changed(frm, "name_on_donation_slip", donor.donor_name);
			}
			set_previous_sponsorship_balance(frm);
			render_donor_program_enrollments(frm);
		}
	});
}

function toggle_mohasil_details(frm) {
	const show_mohasil_details = cint(frm.doc.is_mohasil_collection);
	frm.toggle_display("mohasil_section", show_mohasil_details);
	frm.toggle_reqd("mohasil", show_mohasil_details);
	frm.toggle_reqd("donation_book_serial_no", show_mohasil_details);
	frm.toggle_reqd("cash_denominations", false);
	toggle_purpose_receipt_number_column(frm, show_mohasil_details);

	if (!show_mohasil_details) {
		set_value_if_changed(frm, "mohasil", "");
		set_value_if_changed(frm, "donation_book_serial_no", "");
		set_value_if_changed(frm, "donation_book", "");
		set_value_if_changed(frm, "manual_receipt_number", "");
		set_value_if_changed(frm, "manual_receipt_date", "");
		set_value_if_changed(frm, "location_assignment", "");
		clear_purpose_receipt_numbers(frm);
		frm.clear_table("cash_denominations");
		frm.refresh_field("cash_denominations");
	}
}

function set_donation_book_from_serial(frm) {
	if (!frm.doc.donation_book_serial_no) {
		set_value_if_changed(frm, "donation_book", "");
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.doctype.book.book.get_donation_book_for_serial",
		args: {
			book_serial_no: frm.doc.donation_book_serial_no,
			mohasil: frm.doc.mohasil,
		},
		callback(response) {
			const book = response.message || {};
			set_value_if_changed(frm, "donation_book", book.name || "");
			check_all_manual_receipt_duplicates(frm);
		},
	});
}

function check_all_manual_receipt_duplicates(frm) {
	(frm.doc.purpose_details || []).forEach((row) => {
		if (row.manual_receipt_number) {
			check_manual_receipt_duplicate(frm, row.doctype, row.name);
		}
	});
}

function check_manual_receipt_duplicate(frm, cdt, cdn) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row || !frm.doc.is_mohasil_collection || !frm.doc.donation_book_serial_no) {
		return;
	}

	const receipt_number = String(row.manual_receipt_number || "").trim();
	if (!receipt_number) {
		return;
	}

	const duplicate_in_grid = (frm.doc.purpose_details || []).find(
		(purpose_row) =>
			purpose_row.name !== row.name
			&& String(purpose_row.manual_receipt_number || "").trim() === receipt_number
	);
	if (duplicate_in_grid) {
		frappe.msgprint({
			title: __("Duplicate Manual Receipt Number"),
			indicator: "red",
			message: __("Manual Receipt Number {0} is already entered in another Purpose row.", [
				receipt_number,
			]),
		});
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.doctype.donation_order.donation_order.check_manual_receipt_duplicate",
		args: {
			donation_book: frm.doc.donation_book,
			donation_book_serial_no: frm.doc.donation_book_serial_no,
			manual_receipt_number: receipt_number,
			current_order: frm.doc.name,
		},
		callback(response) {
			const duplicate = response.message || {};
			if (!duplicate.exists) {
				return;
			}

			frappe.msgprint({
				title: __("Duplicate Manual Receipt Number"),
				indicator: "red",
				message: __(
					"Manual Receipt Number {0} is already used for Donation Book Serial No {1} in Donation Order {2}.",
					[
						receipt_number,
						frm.doc.donation_book_serial_no,
						duplicate.donation_order,
					]
				),
			});
		},
	});
}

function toggle_purpose_receipt_number_column(frm, show) {
	const grid = frm.fields_dict.purpose_details && frm.fields_dict.purpose_details.grid;
	if (!grid) {
		return;
	}

	grid.update_docfield_property("manual_receipt_number", "hidden", show ? 0 : 1);
	grid.update_docfield_property("manual_receipt_number", "reqd", show ? 1 : 0);
	grid.refresh();
}

function clear_purpose_receipt_numbers(frm) {
	(frm.doc.purpose_details || []).forEach((row) => {
		row.manual_receipt_number = "";
	});
	frm.refresh_field("purpose_details");
}

function set_mohasil_from_selected_donor(frm) {
	if (!frm.doc.donor_name || frm.doc.mohasil) {
		return;
	}

	frappe.db.get_value("Donor", frm.doc.donor_name, "mohasil").then((response) => {
		const mohasil = response && response.message && response.message.mohasil;
		if (frm.doc.is_mohasil_collection && !frm.doc.mohasil && mohasil) {
			set_value_if_changed(frm, "mohasil", mohasil);
			set_effective_donation_location(frm);
		}
	});
}

function set_effective_donation_location(frm) {
	if (!cint(frm.doc.is_mohasil_collection) || !frm.doc.mohasil || !frm.doc.donation_posting_date) {
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_effective_donation_location",
		args: {
			employee: frm.doc.mohasil,
			donation_date: frm.doc.donation_posting_date,
		},
		callback(response) {
			const assignment = response.message || {};
			set_value_if_changed(frm, "donation_location", assignment.donation_location || "");
			set_value_if_changed(frm, "location_assignment", assignment.assignment || "");
		},
	});
}

function load_esaal_e_sawab_from_donor(frm, force) {
	if (!frm.doc.donor_name || frm.doc.docstatus !== 0) {
		return;
	}

	if (!force && (frm.doc.esaal_e_sawab || []).length) {
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_esaal_e_sawab",
		args: {
			donor: frm.doc.donor_name,
		},
		callback(response) {
			const rows = response.message || [];
			frm.clear_table("esaal_e_sawab");
			rows.forEach((row) => {
				const child = frm.add_child("esaal_e_sawab");
				child.person_name = row.person_name;
				child.relationship = row.relationship;
				child.remarks = row.remarks;
			});
			frm.refresh_field("esaal_e_sawab");
		},
	});
}

function update_cash_denomination_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", cint(row.denomination) * cint(row.note_count));
	update_cash_denomination_rows(frm);
}

function update_cash_denomination_rows(frm) {
	(frm.doc.cash_denominations || []).forEach((row) => {
		row.amount = cint(row.denomination) * cint(row.note_count);
	});
	frm.refresh_field("cash_denominations");
}

function update_beneficiary_fields(frm, clear_hidden_values) {
	const requires_student = cint(frm.doc.requires_student);
	const requires_prisoner = cint(frm.doc.requires_prisoner);
	const sponsorship_purpose_rows = (frm.doc.purpose_details || []).filter(
		(row) => row.donation_category === "Sponsorship" && row.donation_purpose
	);
	const has_sponsorship_in_grid = sponsorship_purpose_rows.length > 0;
	const is_sponsorship =
		frm.doc.purpose_of_donation === "Sponsorship" || has_sponsorship_in_grid;
	const has_donation_purpose =
		Boolean(frm.doc.donation_purpose) || has_sponsorship_in_grid;
	const show_sponsorship_allocation = is_sponsorship && has_donation_purpose;
	const has_sponsorship_rows = (frm.doc.sponsorship_students || []).length > 0;

	frm.toggle_display("beneficiary_section", requires_student || requires_prisoner);
	frm.toggle_display("student_name", requires_student && !is_sponsorship);
	frm.toggle_reqd("student_name", requires_student && !is_sponsorship);
	frm.toggle_display("student_mode", requires_student && frm.doc.student_mode && !is_sponsorship);
	frm.toggle_display("prisoner_name", requires_prisoner && !is_sponsorship);
	frm.toggle_reqd("prisoner_name", requires_prisoner && !is_sponsorship);
	frm.toggle_display("sponsorship_section", show_sponsorship_allocation);
	frm.toggle_display("sponsorship_students", show_sponsorship_allocation);
	apply_sponsorship_table_rules(frm);

	if (clear_hidden_values && (!requires_student || is_sponsorship)) {
		set_value_if_changed(frm, "student_name", "");
		set_value_if_changed(frm, "total_donation", 0);
	}

	if (clear_hidden_values && (!requires_prisoner || is_sponsorship)) {
		set_value_if_changed(frm, "prisoner_name", "");
	}

	if (
		clear_hidden_values &&
		!show_sponsorship_allocation &&
		!has_sponsorship_rows &&
		!frm.__applying_donor_program
	) {
		frm.clear_table("sponsorship_students");
		frm.refresh_field("sponsorship_students");
	}

	set_sponsorship_totals(frm);
}

function apply_sponsorship_table_rules(frm) {
	const has_sponsorship_in_grid = (frm.doc.purpose_details || []).some(
		(row) => row.donation_category === "Sponsorship" && row.donation_purpose
	);
	const show_sponsorship_allocation =
		(frm.doc.purpose_of_donation === "Sponsorship" || has_sponsorship_in_grid) &&
		(Boolean(frm.doc.donation_purpose) || has_sponsorship_in_grid);

	if (show_sponsorship_allocation) {
		configure_sponsorship_grid(frm, "sponsorship_students", {
			quantity: { visible: true, reqd: true, read_only: false },
		});
	}
}

function configure_sponsorship_grid(frm, table_fieldname, field_rules) {
	const grid = frm.fields_dict[table_fieldname]?.grid;
	if (!grid) {
		return;
	}

	["quantity"].forEach((fieldname) => {
		set_grid_field_property(grid, fieldname, "hidden", 0);
		set_grid_field_property(grid, fieldname, "read_only", 0);
		set_grid_field_property(grid, fieldname, "reqd", 0);
		grid.set_column_disp(fieldname, true);
	});

	Object.keys(field_rules).forEach((fieldname) => {
		const rule = field_rules[fieldname];
		set_grid_field_property(grid, fieldname, "hidden", rule.visible ? 0 : 1);
		set_grid_field_property(grid, fieldname, "read_only", rule.read_only ? 1 : 0);
		set_grid_field_property(grid, fieldname, "reqd", rule.reqd ? 1 : 0);
		grid.set_column_disp(fieldname, Boolean(rule.visible));
	});

	grid.refresh();
	frm.refresh_field(table_fieldname);
}

function set_grid_field_property(grid, fieldname, property, value) {
	if (grid.update_docfield_property) {
		grid.update_docfield_property(fieldname, property, value);
	}

	const docfield = (grid.docfields || []).find((field) => field.fieldname === fieldname);
	if (docfield) {
		docfield[property] = value;
	}
}

function set_previous_sponsorship_balance(frm) {
	if (!is_sponsorship_order(frm) || !frm.doc.donor_name || !frm.doc.donation_type) {
		set_value_if_changed(frm, "previous_sponsorship_balance", 0);
		set_value_if_changed(frm, "previous_balance_used", 0);
		set_sponsorship_totals(frm);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_previous_sponsorship_balance",
		args: {
			donor: frm.doc.donor_name,
			donation_type: frm.doc.donation_type,
			exclude_donation_order: frm.doc.name,
		},
		callback(response) {
			const previous_balance = flt(response.message);
			set_value_if_changed(frm, "previous_sponsorship_balance", previous_balance);
			set_value_if_changed(frm, "previous_balance_used", previous_balance);
			set_sponsorship_totals(frm);
		},
	});
}

function set_student_total_donation(frm) {
	if (frm.doc.purpose_of_donation === "Sponsorship" || !frm.doc.student_name) {
		set_value_if_changed(frm, "total_donation", 0);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_student_total_donation",
		args: {
			student_name: frm.doc.student_name,
			exclude_donation_order: frm.doc.name,
		},
		callback(response) {
			const previous_total = flt(response.message);
			set_value_if_changed(frm, "total_donation", previous_total + flt(frm.doc.donation_amount));
		},
	});
}

function set_program_details(frm, cdt, cdn, table_fieldname, quantity) {
	const row = locals[cdt][cdn];
	if (!row.sponsorship_program) {
		set_child_value_if_changed(cdt, cdn, "monthly_donation", 0);
		set_child_value_if_changed(cdt, cdn, "duration_months", 0);
		set_child_value_if_changed(cdt, cdn, "total_program_donation", 0);
		set_sponsorship_row_totals(frm, cdt, cdn, table_fieldname, quantity);
		return;
	}

	frappe.db
		.get_value("Sponsorship Program", row.sponsorship_program, [
			"monthly_donation",
			"duration_months",
			"total_program_donation",
		])
		.then((response) => {
			const program = response.message || {};
			set_child_value_if_changed(cdt, cdn, "monthly_donation", program.monthly_donation || 0);
			set_child_value_if_changed(cdt, cdn, "duration_months", program.duration_months || 0);
			set_child_value_if_changed(
				cdt,
				cdn,
				"total_program_donation",
				program.total_program_donation || 0
			);
			set_sponsorship_row_totals(frm, cdt, cdn, table_fieldname, quantity);
			auto_allocate_sponsorship_amounts(frm, true);
		});
}

function auto_allocate_sponsorship_amounts(frm) {
	const rows = frm.doc.sponsorship_students || [];
	if (!rows.length || !get_sponsorship_purpose_amount(frm)) {
		return;
	}

	const available = get_sponsorship_purpose_amount(frm) + flt(frm.doc.previous_balance_used);

	if (rows.length === 1) {
		const row = rows[0];
		if (!row.sponsorship_program || !cint(row.quantity)) {
			return;
		}

		const total_program =
			flt(row.total_program_donation) ||
			flt(row.monthly_donation) * flt(row.duration_months) * cint(row.quantity);
		const allocated = Math.min(available, total_program || available);

		if (flt(row.allocated_amount) === 0) {
			set_child_value_if_changed(row.doctype, row.name, "allocated_amount", allocated);
			set_sponsorship_row_totals(
				frm,
				row.doctype,
				row.name,
				"sponsorship_students",
				cint(row.quantity)
			);
		}
		return;
	}

	let remaining = available;
	rows.forEach((row) => {
		if (flt(row.allocated_amount) > 0) {
			remaining -= flt(row.allocated_amount);
			return;
		}

		if (!row.sponsorship_program || !cint(row.quantity)) {
			return;
		}

		const total_program =
			flt(row.total_program_donation) ||
			flt(row.monthly_donation) * flt(row.duration_months) * cint(row.quantity);
		const allocated = Math.min(Math.max(remaining, 0), total_program);

		if (allocated > 0) {
			set_child_value_if_changed(row.doctype, row.name, "allocated_amount", allocated);
			set_sponsorship_row_totals(
				frm,
				row.doctype,
				row.name,
				"sponsorship_students",
				cint(row.quantity)
			);
			remaining -= allocated;
		}
	});
}

function set_sponsorship_row_totals(frm, cdt, cdn, table_fieldname, quantity) {
	const row = locals[cdt][cdn];
	if (!row) {
		return;
	}

	quantity = cint(quantity) || 0;
	const monthly_donation = flt(row.monthly_donation);
	const duration_months = flt(row.duration_months);
	const allocated_amount = flt(row.allocated_amount);
	const total_program_donation = monthly_donation * duration_months * quantity;
	const monthly_total = monthly_donation * quantity;
	const total_days = Math.round(duration_months * sponsorship_days_in_month);
	const covered_days = monthly_total
		? Math.min(Math.round((allocated_amount / monthly_total) * sponsorship_days_in_month), total_days)
		: 0;
	const remaining_days = Math.max(total_days - covered_days, 0);
	const covered_months = covered_days / sponsorship_days_in_month;
	const remaining_months = remaining_days / sponsorship_days_in_month;

	set_child_value_if_changed(cdt, cdn, "total_program_donation", total_program_donation);
	set_child_value_if_changed(cdt, cdn, "covered_months", covered_months);
	set_child_value_if_changed(cdt, cdn, "covered_duration", format_sponsorship_duration(covered_days));
	set_child_value_if_changed(cdt, cdn, "remaining_months", remaining_months);
	set_child_value_if_changed(cdt, cdn, "remaining_duration", format_sponsorship_duration(remaining_days));
	const prior_allocated = get_row_prior_allocated(frm, row.sponsorship_program);
	set_child_value_if_changed(
		cdt,
		cdn,
		"remaining_amount",
		Math.max(total_program_donation - prior_allocated - allocated_amount, 0)
	);

	frm.refresh_field(table_fieldname);
	set_sponsorship_totals(frm);
}

function get_sponsorship_row_quantity(row) {
	return cint(row.quantity);
}

function is_sponsorship_order(frm) {
	if (frm.doc.purpose_of_donation === "Sponsorship") {
		return true;
	}

	return (frm.doc.purpose_details || []).some(
		(row) => row.donation_category === "Sponsorship" && row.donation_purpose
	);
}

function refresh_donor_program_prior_allocated(frm, callback) {
	const programs = [
		...new Set(
			(frm.doc.sponsorship_students || [])
				.map((row) => row.sponsorship_program)
				.filter(Boolean)
		),
	];

	if (!frm.doc.donor_name || !programs.length) {
		frm.__donor_program_prior_paid = {};
		frm.__donor_program_prior_paid_key = null;
		callback?.();
		return;
	}

	const cache_key = `${frm.doc.donor_name}|${programs.sort().join("|")}|${frm.doc.name || ""}`;
	if (frm.__donor_program_prior_paid_key === cache_key && frm.__donor_program_prior_paid) {
		callback?.();
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_program_prior_allocated",
		args: {
			donor: frm.doc.donor_name,
			sponsorship_programs: programs,
			exclude_donation_order: frm.doc.name,
		},
		callback(response) {
			frm.__donor_program_prior_paid = response.message || {};
			frm.__donor_program_prior_paid_key = cache_key;
			callback?.();
		},
	});
}

function get_row_prior_allocated(frm, sponsorship_program) {
	return flt((frm.__donor_program_prior_paid || {})[sponsorship_program]);
}

function get_donor_program_prior_allocated_total(frm) {
	const programs = [
		...new Set(
			(frm.doc.sponsorship_students || [])
				.map((row) => row.sponsorship_program)
				.filter(Boolean)
		),
	];

	return programs.reduce(
		(total, program) => total + get_row_prior_allocated(frm, program),
		0
	);
}

function set_sponsorship_totals(frm) {
	if (!is_sponsorship_order(frm)) {
		set_value_if_changed(frm, "previous_sponsorship_balance", 0);
		set_value_if_changed(frm, "previous_balance_used", 0);
		set_value_if_changed(frm, "sponsorship_amount", 0);
		set_value_if_changed(frm, "available_allocation_amount", 0);
		set_value_if_changed(frm, "allocated_amount", 0);
		set_value_if_changed(frm, "unallocated_amount", 0);
		set_value_if_changed(frm, "total_program_amount", 0);
		set_value_if_changed(frm, "remaining_program_cost", 0);
		set_value_if_changed(frm, "allocation_status", "");
		set_value_if_changed(frm, "sponsored_student_count", 0);
		set_value_if_changed(frm, "total_sponsored_beneficiaries", 0);
		set_value_if_changed(frm, "total_covered_months", 0);
		return;
	}

	refresh_donor_program_prior_allocated(frm, () => update_sponsorship_totals(frm));
}

function update_sponsorship_totals(frm) {
	const allocation_rows = frm.doc.sponsorship_students || [];
	const allocated_amount = allocation_rows.reduce(
		(total, row) => total + flt(row.allocated_amount),
		0
	);
	const total_program_amount = allocation_rows.reduce(
		(total, row) => total + flt(row.total_program_donation),
		0
	);
	const total_sponsored_beneficiaries = allocation_rows.reduce(
		(total, row) => total + cint(row.quantity),
		0
	);
	const total_covered_months = allocation_rows.reduce(
		(total, row) => total + flt(row.covered_months),
		0
	);
	const prior_program_allocated = get_donor_program_prior_allocated_total(frm);
	const sponsorship_amount = get_sponsorship_purpose_amount(frm);
	const available_allocation_amount = sponsorship_amount + flt(frm.doc.previous_balance_used);

	allocation_rows.forEach((row) => {
		const total_program = flt(row.total_program_donation);
		const prior_allocated = get_row_prior_allocated(frm, row.sponsorship_program);
		set_child_value_if_changed(
			row.doctype,
			row.name,
			"remaining_amount",
			Math.max(total_program - prior_allocated - flt(row.allocated_amount), 0)
		);
	});

	set_value_if_changed(frm, "total_donation", flt(frm.doc.donation_amount));
	set_value_if_changed(frm, "sponsorship_amount", sponsorship_amount);
	set_value_if_changed(frm, "available_allocation_amount", available_allocation_amount);
	set_value_if_changed(frm, "allocated_amount", allocated_amount);
	set_value_if_changed(frm, "unallocated_amount", available_allocation_amount - allocated_amount);
	set_value_if_changed(frm, "total_program_amount", total_program_amount);
	set_value_if_changed(
		frm,
		"remaining_program_cost",
		Math.max(total_program_amount - prior_program_allocated - allocated_amount, 0)
	);
	set_value_if_changed(frm, "allocation_status", get_allocation_status(frm, allocated_amount));
	set_value_if_changed(frm, "sponsored_student_count", total_sponsored_beneficiaries);
	set_value_if_changed(frm, "total_sponsored_beneficiaries", total_sponsored_beneficiaries);
	set_value_if_changed(frm, "total_covered_months", total_covered_months);
	frm.refresh_field("sponsorship_students");
}

function is_prisoner_sponsorship_program(program_name) {
	return Boolean(program_name && program_name.endsWith(prisoner_program_suffix));
}

function get_sponsorship_program_modes(frm) {
	const modes = {
		student: false,
		prisoner: false,
	};

	(frm.doc.purpose_details || []).forEach((row) => {
		if (row.donation_category !== "Sponsorship") {
			return;
		}

		if (row.donation_purpose === "Sponsorship - Prisoner") {
			modes.prisoner = true;
		} else {
			modes.student = true;
		}
	});

	return modes;
}

function format_sponsorship_duration(total_days) {
	total_days = Math.max(cint(total_days), 0);
	const months = Math.floor(total_days / sponsorship_days_in_month);
	const days = total_days % sponsorship_days_in_month;
	const parts = [];
	if (months) {
		parts.push(__("{0} month{1}", [months, months === 1 ? "" : "s"]));
	}
	if (days) {
		parts.push(__("{0} day{1}", [days, days === 1 ? "" : "s"]));
	}
	return parts.join(" ") || __("0 days");
}

function get_receiving_account_donation_type(donation_type) {
	return donation_type === "Zakat" ? "Zakat" : "Atiya";
}

function get_accounting_request_key(args) {
	return [
		args.company || "",
		args.donation_type || "",
		args.donation_purpose || "",
		args.mode_of_payment || "",
	].join("::");
}

function get_purpose_row_request_key(frm, row) {
	return get_accounting_request_key({
		company: frm.doc.company,
		donation_type: row.donation_type,
		donation_purpose: row.donation_purpose,
		mode_of_payment: frm.doc.mode_of_payment,
	}) + `::${row.donation_category || ""}::${row.name || ""}`;
}

function is_deposit_account_mode(frm) {
	return ["Cheque", "Card Payment"].includes(frm.doc.mode_of_payment);
}

function is_bank_draft_mode(frm) {
	return frm.doc.mode_of_payment === bank_draft_mode_of_payment;
}

function is_manual_bank_mode(frm) {
	return frm.doc.mode_of_payment_type === "Bank" && !is_deposit_account_mode(frm);
}

function get_allocation_status(frm, allocated_amount) {
	const available_allocation_amount = get_sponsorship_purpose_amount(frm) + flt(frm.doc.previous_balance_used);
	const unallocated_amount = available_allocation_amount - flt(allocated_amount);
	if (flt(allocated_amount) <= 0) {
		return "Unallocated";
	}

	if (unallocated_amount > 0) {
		return "Partially Allocated";
	}

	return "Fully Allocated";
}

function get_sponsorship_purpose_amount(frm) {
	return (frm.doc.purpose_details || [])
		.filter((row) => row.donation_category === "Sponsorship")
		.reduce((total, row) => total + flt(row.amount), 0);
}

function set_value_if_changed(frm, fieldname, value) {
	const current_value = frm.doc[fieldname] || "";
	const new_value = value || "";

	if (String(current_value) !== String(new_value)) {
		frm.set_value(fieldname, value);
	}
}

function set_child_value_if_changed(cdt, cdn, fieldname, value) {
	const row = locals[cdt][cdn];
	const current_value = row[fieldname] || "";
	const new_value = value || "";

	if (String(current_value) !== String(new_value)) {
		frappe.model.set_value(cdt, cdn, fieldname, value);
	}
}
