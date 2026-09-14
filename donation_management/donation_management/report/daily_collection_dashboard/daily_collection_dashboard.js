frappe.query_reports["Daily Collection Dashboard"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "donation_location",
			label: __("Donation Location"),
			fieldtype: "Link",
			options: "Donation Location",
		},
		{
			fieldname: "collector",
			label: __("Cashier/Collector"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "donor_classification",
			label: __("Donor Classification"),
			fieldtype: "Select",
			options: "\nR\nNR\nWalk-in\nRefered by Trustee\nKey Donor\nSub General Donor\nGeneral Donor\nSub Key Donor",
		},
		{
			fieldname: "program_fund",
			label: __("Program/Fund"),
			fieldtype: "Link",
			options: "Donation Purpose",
		},
		{
			fieldname: "mode_of_payment",
			label: __("Mode of Payment"),
			fieldtype: "Link",
			options: "Mode of Payment",
		},
	],
};
