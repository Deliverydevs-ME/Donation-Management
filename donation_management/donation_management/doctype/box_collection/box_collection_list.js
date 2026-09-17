// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.listview_settings["Box Collection"] = {
	get_indicator(doc) {
		const status = doc.status || (doc.docstatus === 2 ? "Cancelled" : "Draft");
		const colors = {
			Available: "gray",
			Occupied: "orange",
			Issued: "blue",
			"Pending Receipt": "orange",
			"Under Collection": "orange",
			Collected: "purple",
			Received: "green",
			Returned: "gray",
			Closed: "green",
			Cancelled: "red",
		};

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},

	onload(listview) {
		hide_box_collection_create_button(listview);
	},

	refresh(listview) {
		hide_box_collection_create_button(listview);
	},
};

function hide_box_collection_create_button(listview) {
	if (listview.page?.clear_primary_action) {
		listview.page.clear_primary_action();
	}

	setTimeout(() => {
		listview.page?.btn_primary?.hide();
		listview.$page.find(".primary-action").hide();
		listview.$page.find("button:contains('Add Box Collection')").hide();
		listview.$page.find("[data-label='Add Box Collection']").hide();
	}, 100);
}
