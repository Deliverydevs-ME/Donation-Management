frappe.listview_settings["Donation Confidential Access Log"] = {
	onload(listview) {
		hide_confidential_log_create_button(listview);
	},

	refresh(listview) {
		hide_confidential_log_create_button(listview);
	},
};

function hide_confidential_log_create_button(listview) {
	if (listview.page?.clear_primary_action) {
		listview.page.clear_primary_action();
	}

	setTimeout(() => {
		listview.page?.btn_primary?.hide();
		listview.$page.find(".primary-action").hide();
		listview.$page.find("button:contains('Add Donation Confidential Access Log')").hide();
		listview.$page.find("[data-label='Add Donation Confidential Access Log']").hide();
	}, 100);
}
