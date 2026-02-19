let frappeCloudBaseEndpoint = "https://frappecloud.com";
let isFCUser = true;

$(document).ready(function () {
	const response = frappe.boot.site_info;
	const trial_end_date = new Date(response.trial_end_date);
	frappeCloudBaseEndpoint = response.base_url;
	isFCUser = response.is_fc_user;

	const today = new Date();
	const diffTime = trial_end_date - today;
	const trial_end_days = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
	const trial_end_string =
		trial_end_days > 1 ? `${trial_end_days} days` : `${trial_end_days} day`;

	const banner_message = isFCUser
		? "Please upgrade for uninterrupted services"
		: "Please contact your system administrator to upgrade your plan.";
	let card_args = {
		title: `Your trial ends in ${trial_end_string}`,
		message: banner_message,
		outline: true,
		close_button: true,
		popper: true,
		primary_button_alignment: "right",
	};
	isFCUser = true;
	if (isFCUser) {
		card_args.primary_action_label = "Upgrade";
		card_args.primary_action_suffix_icon = "square-arrow-out-up-right";
		card_args.styles = {
			"sidebar-card-button-bg-color": "var(--surface-gray-2)",
			"sidebar-card-button-color": "var(--ink-gray-7)",
			"sidebar-card-button-outline": "var(--ink-gray-7)",
		};
	}
	$(document).on("desktop_screen", function (event, data) {
		if (
			frappe.boot.is_fc_site &&
			!!frappe.boot.setup_complete &&
			!frappe.is_mobile() &&
			frappe.user.has_role("System Manager")
		) {
			if (response.trial_end_date && trial_end_date > new Date()) {
				card_args.parent = $(".icons-container").first();
				let banner_card = new frappe.ui.SidebarCard(card_args);
			}
			addManageBillingDropdown(data.desktop);

			$(".login-to-fc, .upgrade-plan-button").on("click", function () {
				openFrappeCloudDashboard();
			});
		}
	});
	$(document).on("sidebar_setup", function (event, data) {
		let sidebar = data.sidebar;
		// card_args.close_button = null;
		sidebar.add_card({
			title: card_args.title,
			icon: "info",
			message: card_args.message,
			// primary_action_icon: "zap",
			// primary_action_label: "Upgrade",
			// primary_button_width: "full",
			// primary_action: () => {},
		});
	});
});

function setErrorMessage(message) {
	$("#fc-login-error").text(message);
}

function addManageBillingDropdown(desktop) {
	desktop.add_menu_item({
		label: __("Manage Billing"),
		icon: "receipt-text",
		condition: function () {
			return frappe.boot.is_fc_site;
		},
		onClick: function () {
			return openFrappeCloudDashboard();
		},
	});
}
function openFrappeCloudDashboard() {
	window.open(
		`${frappeCloudBaseEndpoint}/dashboard/sites/${frappe.boot.site_info.name}`,
		"_blank"
	);
}
