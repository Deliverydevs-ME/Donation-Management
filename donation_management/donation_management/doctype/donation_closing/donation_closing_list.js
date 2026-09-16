frappe.listview_settings["Donation Closing"] = {
	onload(listview) {
		remove_donation_closing_create_buttons(listview);
	},

	before_render() {
		remove_donation_closing_create_buttons(typeof cur_list !== "undefined" ? cur_list : null);
	},

	refresh(listview) {
		remove_donation_closing_create_buttons(listview);
	},
};

function remove_donation_closing_create_buttons(listview) {
	if (!listview?.page) {
		return;
	}

	const remove_buttons = () => {
		listview.page.clear_primary_action();
		listview.page.btn_primary?.hide();

		const labels = [
			"Add Donation Closing",
			"Create your first Donation Closing",
			"Create a new Donation Closing",
			"Create New",
		].map((label) => __(label));

		$(listview.page.wrapper)
			.find("button, a")
			.filter(function () {
				const text = ($(this).text() || "").trim();
				const data_label = ($(this).attr("data-label") || "").replace(/%20/g, " ").trim();
				return labels.some((label) => text === label || data_label === label);
			})
			.hide();

		listview.$page?.find(".primary-action").hide();
		listview.$page?.find(".btn-new-doc").hide();
	};

	remove_buttons();
	setTimeout(remove_buttons, 100);
	setTimeout(remove_buttons, 500);
	setTimeout(remove_buttons, 1000);
}
