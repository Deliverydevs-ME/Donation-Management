frappe.ui.form.on("Ilaqi Maktab", {
	refresh(frm) {
		render_assigned_employees(frm);
	},
});

function render_assigned_employees(frm) {
	if (!frm.fields_dict.assigned_employees_html) {
		return;
	}

	if (frm.is_new()) {
		frm.fields_dict.assigned_employees_html.$wrapper.html(
			`<div class="text-muted">${__("Save the Ilaqi Maktab to view assigned employees.")}</div>`
		);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.doctype.ilaqi_maktab.ilaqi_maktab.get_assigned_employees",
		args: {
			ilaqi_maktab: frm.doc.name,
		},
		callback(response) {
			const rows = response.message || [];
			frm.fields_dict.assigned_employees_html.$wrapper.html(build_assigned_employees_html(rows));
		},
	});
}

function build_assigned_employees_html(rows) {
	if (!rows.length) {
		return `<div class="text-muted">${__("No employees assigned yet.")}</div>`;
	}

	const body = rows
		.map((row) => {
			const assignment_url = `/app/maktab-employee-assignment/${encodeURIComponent(row.name)}`;
			const employee_url = `/app/employee/${encodeURIComponent(row.employee)}`;
			return `
				<tr>
					<td><a href="${assignment_url}">${frappe.utils.escape_html(row.name || "")}</a></td>
					<td><a href="${employee_url}">${frappe.utils.escape_html(row.employee || "")}</a></td>
					<td>${frappe.utils.escape_html(row.employee_name || "")}</td>
					<td>${frappe.utils.escape_html(row.start_date || "")}</td>
					<td>${frappe.utils.escape_html(row.end_date || "")}</td>
					<td>${frappe.utils.escape_html(row.status || "")}</td>
				</tr>
			`;
		})
		.join("");

	return `
		<div class="table-responsive">
			<table class="table table-bordered table-condensed">
				<thead>
					<tr>
						<th>${__("Assignment")}</th>
						<th>${__("Employee")}</th>
						<th>${__("Employee Name")}</th>
						<th>${__("Start Date")}</th>
						<th>${__("End Date")}</th>
						<th>${__("Status")}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		</div>
	`;
}
