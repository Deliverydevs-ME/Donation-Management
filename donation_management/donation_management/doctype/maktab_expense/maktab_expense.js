frappe.ui.form.on("Maktab Expense", {
	setup(frm) {
		frm.set_query("employee", () => {
			return {
				filters: {
					status: "Active",
				},
			};
		});
	},

	expense_category(frm) {
		toggle_employee_field(frm);
	},

	refresh(frm) {
		toggle_employee_field(frm);
	},
});

function toggle_employee_field(frm) {
	const employee_related_categories = ["Salary", "Allowances", "Employee Expenses"];
	const is_employee_related = employee_related_categories.includes(frm.doc.expense_category);

	frm.toggle_display("employee", is_employee_related);
	frm.toggle_reqd("employee", is_employee_related);

	if (!is_employee_related && frm.doc.employee) {
		frm.set_value("employee", "");
	}
}
