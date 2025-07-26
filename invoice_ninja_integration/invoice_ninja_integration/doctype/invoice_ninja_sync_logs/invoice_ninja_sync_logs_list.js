// Copyright (c) 2025, Novizna and contributors
// For license information, please see license.txt

frappe.listview_settings['Invoice Ninja Sync Logs'] = {
	add_fields: ["status", "sync_type", "record_type", "sync_timestamp"],
	get_indicator: function(doc) {
		if (doc.status === "Success") {
			return [__("Success"), "green", "status,=,Success"];
		} else if (doc.status === "Failed") {
			return [__("Failed"), "red", "status,=,Failed"];
		} else if (doc.status === "In Progress") {
			return [__("In Progress"), "blue", "status,=,In Progress"];
		} else if (doc.status === "Partial") {
			return [__("Partial"), "orange", "status,=,Partial"];
		} else if (doc.status === "Skipped") {
			return [__("Skipped"), "gray", "status,=,Skipped"];
		}
	},

	filters: [
		["status", "=", "Failed"]
	],

	onload: function(listview) {
		// Add custom filter buttons
		listview.page.add_menu_item(__("Show Only Failed"), function() {
			listview.filter_area.add([["Invoice Ninja Sync Logs", "status", "=", "Failed"]]);
		});

		listview.page.add_menu_item(__("Show Only Success"), function() {
			listview.filter_area.add([["Invoice Ninja Sync Logs", "status", "=", "Success"]]);
		});

		listview.page.add_menu_item(__("Show Today's Logs"), function() {
			listview.filter_area.add([["Invoice Ninja Sync Logs", "sync_timestamp", ">=", frappe.datetime.get_today()]]);
		});
	}
};
