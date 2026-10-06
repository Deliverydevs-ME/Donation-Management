frappe.listview_settings["Donation Instrument Event"] = {
	add_fields: ["event_status"],

	get_indicator(doc) {
		const status = doc.event_status || "Received";
		const colors = {
			Received: "blue",
			"Pending Encashment": "orange",
			Encashed: "green",
			"Bounced/Rejected": "red",
			Cancelled: "red",
		};

		return [__(status), colors[status] || "gray", `event_status,=,${status}`];
	},
};
