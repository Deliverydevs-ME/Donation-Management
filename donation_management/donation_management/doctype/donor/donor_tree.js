frappe.treeview_settings["Donor"] = {
	breadcrumb: "Donation Management",
	title: __("Donors"),
	root_label: "Donors",
	get_tree_root: false,
	disable_add_node: true,
	get_tree_nodes:
		"donation_management.donation_management.doctype.donor.donor.get_referral_tree_children",
	onload(treeview) {
		frappe.treeview_settings["Donor"].treeview = treeview;
		treeview.make_tree();
	},
	post_render(treeview) {
		frappe.treeview_settings["Donor"].treeview = treeview;
	},
	get_label(node) {
		return __(node.title || node.label);
	},
	toolbar: [
		{
			label: __("Open"),
			condition(node) {
				return (
					!node.is_root &&
					!node.data.hide_open &&
					node.data.reference_doctype &&
					node.data.reference_name
				);
			},
			click(node) {
				frappe.set_route("Form", node.data.reference_doctype, node.data.reference_name);
			},
		},
	],
};
