import reflex as rx
from app.states.investigation_state import InvestigationState, SocialResult


def tab_button(label: str, value: str, icon: str) -> rx.Component:
    return rx.el.button(
        rx.icon(icon, class_name="w-4 h-4 mr-2"),
        rx.el.span(label),
        on_click=lambda: InvestigationState.set_active_tab(value),
        class_name=rx.cond(
            InvestigationState.active_tab == value,
            "flex items-center px-3 md:px-6 py-3 text-sm font-medium text-orange-600 border-b-2 border-orange-500 bg-orange-50/50 whitespace-nowrap shrink-0 transition-colors duration-200",
            "flex items-center px-3 md:px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-50 border-b-2 border-transparent whitespace-nowrap shrink-0 transition-colors duration-200",
        ),
    )


def ethical_reminder_card(title: str, message: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("shield-check", class_name="w-5 h-5 text-emerald-600 mr-3"),
            rx.el.h4(
                "Ethical Use Guideline", class_name="text-sm font-bold text-emerald-800"
            ),
            class_name="flex items-center mb-2",
        ),
        rx.el.p(message, class_name="text-sm text-emerald-700 leading-relaxed"),
        class_name="bg-emerald-50 border border-emerald-100 rounded-xl p-4 mb-6",
    )


def result_row(label: str, value: str, is_highlight: bool = False) -> rx.Component:
    return rx.el.div(
        rx.el.span(label, class_name="text-sm text-gray-500 font-medium"),
        rx.el.span(
            value,
            class_name=f"text-sm font-semibold {rx.cond(is_highlight, 'text-orange-600', 'text-gray-900')}",
        ),
        class_name="flex justify-between items-center py-3 border-b border-gray-50 last:border-0",
    )


def network_node_card(node: dict) -> rx.Component:
    return rx.el.div(
        rx.icon(node["icon"], class_name="w-6 h-6 text-orange-500 mb-2"),
        rx.el.h4(
            node["label"],
            class_name="text-sm font-bold text-gray-800 truncate w-full text-center",
        ),
        rx.el.span(
            node["type"],
            class_name="text-xs text-gray-400 uppercase tracking-wider mt-1",
        ),
        class_name="flex flex-col items-center p-4 bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all min-w-[120px] max-w-[150px]",
    )


def category_section(
    title: str, nodes: list[dict], icon: str, color: str
) -> rx.Component:
    return rx.cond(
        nodes.length() > 0,
        rx.el.div(
            rx.el.div(
                rx.icon(icon, class_name=f"w-5 h-5 {color} mr-2"),
                rx.el.h4(title, class_name="text-md font-bold text-gray-800"),
                class_name="flex items-center mb-4 pb-2 border-b border-gray-100",
            ),
            rx.el.div(
                rx.foreach(nodes, network_node_card),
                class_name="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8",
            ),
        ),
    )


def network_map_tool() -> rx.Component:
    return rx.el.div(
        ethical_reminder_card(
            "Investigation Map",
            "Visualizing connections helps identify patterns. Use this data to build a case, not to draw premature conclusions without verification.",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        "Target Network Graph",
                        class_name="text-lg font-semibold text-gray-800",
                    ),
                    rx.el.p(
                        "Correlated entities from your investigation",
                        class_name="text-xs text-gray-500",
                    ),
                    class_name="flex flex-col",
                ),
                rx.cond(
                    InvestigationState.network_nodes.length() > 0,
                    rx.el.div(
                        rx.el.button(
                            rx.icon("download", class_name="w-4 h-4 mr-2"),
                            "Export",
                            on_click=rx.toast("Graph data exported to JSON"),
                            class_name="text-sm text-gray-600 hover:text-gray-900 font-medium flex items-center px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors",
                        ),
                        rx.el.button(
                            rx.icon("trash-2", class_name="w-4 h-4 mr-2"),
                            "Clear Graph",
                            on_click=InvestigationState.clear_graph,
                            class_name="text-sm text-red-600 hover:text-red-700 font-medium flex items-center px-3 py-2 rounded-lg hover:bg-red-50 transition-colors",
                        ),
                        class_name="flex gap-2",
                    ),
                ),
                class_name="flex justify-between items-start mb-6",
            ),
            rx.cond(
                InvestigationState.network_nodes.length() > 0,
                rx.el.div(
                    rx.el.div(
                        category_section(
                            "Identity Entities",
                            InvestigationState.nodes_by_category["Identity"],
                            "fingerprint",
                            "text-blue-500",
                        ),
                        category_section(
                            "Infrastructure & Network",
                            InvestigationState.nodes_by_category["Infrastructure"],
                            "server",
                            "text-orange-500",
                        ),
                        category_section(
                            "Evidence & Alerts",
                            InvestigationState.nodes_by_category["Evidence"],
                            "file-warning",
                            "text-red-500",
                        ),
                        category_section(
                            "Other Entities",
                            InvestigationState.nodes_by_category["Other"],
                            "circle_plus",
                            "text-gray-500",
                        ),
                        class_name="animate-in fade-in slide-in-from-bottom-4 duration-500",
                    ),
                    rx.el.div(
                        rx.el.h4(
                            "Connection Log",
                            class_name="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3",
                        ),
                        rx.el.div(
                            rx.foreach(
                                InvestigationState.network_edges,
                                lambda edge: rx.el.div(
                                    rx.icon(
                                        "link", class_name="w-3 h-3 text-gray-300 mr-2"
                                    ),
                                    rx.el.span(
                                        edge["source"],
                                        class_name="font-medium text-gray-700 truncate max-w-[120px] md:max-w-xs",
                                    ),
                                    rx.icon(
                                        "arrow-right",
                                        class_name="w-3 h-3 text-orange-500 mx-2 flex-shrink-0",
                                    ),
                                    rx.el.span(
                                        edge["target"],
                                        class_name="font-medium text-gray-700 truncate max-w-[120px] md:max-w-xs",
                                    ),
                                    rx.el.span(
                                        f"({edge['label']})",
                                        class_name="text-xs text-gray-400 ml-auto italic whitespace-nowrap pl-2",
                                    ),
                                    class_name="flex items-center p-2 bg-gray-50 rounded-lg mb-2 text-sm hover:bg-orange-50 transition-colors border border-transparent hover:border-orange-100",
                                ),
                            ),
                            class_name="max-h-64 overflow-y-auto custom-scrollbar pr-2",
                        ),
                        class_name="bg-white border border-gray-200 rounded-xl p-4 mt-8",
                    ),
                ),
                rx.el.div(
                    rx.icon("share-2", class_name="w-12 h-12 text-gray-200 mb-3"),
                    rx.el.p(
                        "No entities mapped yet.",
                        class_name="text-gray-600 font-medium mb-1",
                    ),
                    rx.el.p(
                        "Start an investigation (Domain, Phone, Email, etc.) to see connections appearing here automatically.",
                        class_name="text-gray-400 text-sm max-w-md text-center",
                    ),
                    class_name="flex flex-col items-center justify-center py-16 border-2 border-dashed border-gray-100 rounded-xl bg-gray-50/50",
                ),
            ),
            class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        ),
        class_name="max-w-5xl mx-auto",
    )


def domain_tool() -> rx.Component:
    return rx.el.div(
        ethical_reminder_card(
            "Domain Investigation",
            "Only scan domains for legitimate security research. Respect terms of service and do not use automated tools to harass site owners.",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.input(
                    placeholder="Enter domain (e.g., example.com)",
                    on_change=InvestigationState.set_domain_query,
                    class_name="flex-1 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-300 outline-none transition-all",
                    default_value=InvestigationState.domain_query,
                ),
                rx.el.button(
                    rx.cond(
                        InvestigationState.is_loading_domain,
                        rx.spinner(size="1"),
                        "Analyze Domain",
                    ),
                    on_click=InvestigationState.search_domain,
                    disabled=InvestigationState.is_loading_domain,
                    class_name="bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70 flex items-center gap-2",
                ),
                class_name="flex gap-3 mb-6",
            ),
            rx.cond(
                InvestigationState.domain_result,
                rx.el.div(
                    rx.el.h3(
                        "WHOIS & DNS Data",
                        class_name="text-lg font-semibold text-gray-800 mb-4",
                    ),
                    rx.el.div(
                        result_row(
                            "Domain Name", InvestigationState.domain_result["domain"]
                        ),
                        result_row(
                            "Registrar", InvestigationState.domain_result["registrar"]
                        ),
                        result_row(
                            "Creation Date",
                            InvestigationState.domain_result["creation_date"],
                        ),
                        result_row(
                            "Expiration Date",
                            InvestigationState.domain_result["expiration_date"],
                            is_highlight=True,
                        ),
                        result_row(
                            "Status", InvestigationState.domain_result["status"]
                        ),
                        result_row(
                            "DNS Records Found",
                            InvestigationState.domain_result["dns_records"].to_string(),
                        ),
                        class_name="bg-gray-50 rounded-xl p-5 border border-gray-100",
                    ),
                    class_name="animate-in fade-in slide-in-from-bottom-4 duration-500",
                ),
            ),
            class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        ),
        class_name="max-w-3xl mx-auto",
    )


def ip_tool() -> rx.Component:
    return rx.el.div(
        ethical_reminder_card(
            "IP Geolocation & Threat Analysis",
            "IP data should be used to identify threats, not to physically locate individuals. Geolocation data is approximate.",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.input(
                    placeholder="Enter IP Address (e.g., 192.168.1.1)",
                    on_change=InvestigationState.set_ip_query,
                    class_name="flex-1 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-300 outline-none transition-all",
                    default_value=InvestigationState.ip_query,
                ),
                rx.el.button(
                    rx.cond(
                        InvestigationState.is_loading_ip,
                        rx.spinner(size="1"),
                        "Scan IP",
                    ),
                    on_click=InvestigationState.search_ip,
                    disabled=InvestigationState.is_loading_ip,
                    class_name="bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70 flex items-center gap-2",
                ),
                class_name="flex gap-3 mb-6",
            ),
            rx.cond(
                InvestigationState.ip_result,
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.span(
                                "Threat Score",
                                class_name="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1 block",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    InvestigationState.ip_result["threat_score"],
                                    class_name="text-4xl font-bold text-orange-500",
                                ),
                                rx.el.span(
                                    "/100", class_name="text-lg text-gray-400 ml-1"
                                ),
                            ),
                            class_name="bg-orange-50 rounded-xl p-4 border border-orange-100 text-center w-32",
                        ),
                        rx.el.div(
                            result_row(
                                "IP Address", InvestigationState.ip_result["ip"]
                            ),
                            result_row(
                                "Location",
                                InvestigationState.ip_result["city"]
                                + ", "
                                + InvestigationState.ip_result["country"],
                            ),
                            result_row(
                                "ISP / Organization",
                                InvestigationState.ip_result["isp"],
                            ),
                            result_row("ASN", InvestigationState.ip_result["asn"]),
                            result_row(
                                "Proxy Detected",
                                rx.cond(
                                    InvestigationState.ip_result["is_proxy"],
                                    "Yes",
                                    "No",
                                ),
                                is_highlight=True,
                            ),
                            class_name="flex-1 bg-gray-50 rounded-xl p-5 border border-gray-100",
                        ),
                        class_name="flex flex-col md:flex-row gap-6",
                    ),
                    class_name="animate-in fade-in slide-in-from-bottom-4 duration-500",
                ),
            ),
            class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        ),
        class_name="max-w-3xl mx-auto",
    )


def email_tool() -> rx.Component:
    return rx.el.div(
        ethical_reminder_card(
            "Email Breach Analysis",
            "Use this tool to check if an email has been compromised. Do not use obtained credentials for unauthorized access.",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.input(
                    placeholder="Enter email address",
                    on_change=InvestigationState.set_email_query,
                    class_name="flex-1 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-300 outline-none transition-all",
                    default_value=InvestigationState.email_query,
                ),
                rx.el.button(
                    rx.cond(
                        InvestigationState.is_loading_email,
                        rx.spinner(size="1"),
                        "Check Email",
                    ),
                    on_click=InvestigationState.search_email,
                    disabled=InvestigationState.is_loading_email,
                    class_name="bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70 flex items-center gap-2",
                ),
                class_name="flex gap-3 mb-6",
            ),
            rx.cond(
                InvestigationState.email_result,
                rx.el.div(
                    rx.el.h3(
                        "Reputation & Breach Report",
                        class_name="text-lg font-semibold text-gray-800 mb-4",
                    ),
                    rx.el.div(
                        result_row(
                            "Email Address", InvestigationState.email_result["email"]
                        ),
                        result_row(
                            "Format Valid",
                            rx.cond(
                                InvestigationState.email_result["valid_format"],
                                "Yes",
                                "No",
                            ),
                        ),
                        result_row(
                            "Disposable Address",
                            rx.cond(
                                InvestigationState.email_result["disposable"],
                                "Yes",
                                "No",
                            ),
                            is_highlight=InvestigationState.email_result["disposable"],
                        ),
                        result_row(
                            "Known Breaches",
                            InvestigationState.email_result["breaches"].to_string(),
                            is_highlight=True,
                        ),
                        result_row(
                            "Domain Reputation",
                            InvestigationState.email_result["domain_reputation"],
                        ),
                        result_row(
                            "Latest Breach Event",
                            InvestigationState.email_result["last_breach"],
                        ),
                        class_name="bg-gray-50 rounded-xl p-5 border border-gray-100",
                    ),
                    class_name="animate-in fade-in slide-in-from-bottom-4 duration-500",
                ),
            ),
            class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        ),
        class_name="max-w-3xl mx-auto",
    )


def social_card(result: SocialResult) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(
                rx.cond(result["exists"], "check-circle", "x-circle"),
                class_name=rx.cond(result["exists"], "text-green-500", "text-gray-300")
                + " w-5 h-5 mr-3",
            ),
            rx.el.span(result["platform"], class_name="font-semibold text-gray-700"),
            class_name="flex items-center",
        ),
        rx.cond(
            result["exists"],
            rx.el.a(
                "View Profile",
                rx.icon("external-link", class_name="w-3 h-3 ml-1"),
                href="#",
                class_name="text-xs text-orange-600 hover:text-orange-700 font-medium flex items-center",
            ),
            rx.el.span("Not Found", class_name="text-xs text-gray-400 italic"),
        ),
        class_name="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100",
    )


def social_tool() -> rx.Component:
    return rx.el.div(
        ethical_reminder_card(
            "Social Media Reconnaissance",
            "Information gathered from social media must be publicly available. Do not attempt to bypass privacy settings or friend/follow targets falsely.",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.input(
                    placeholder="Enter username (e.g., unknown_suspect)",
                    on_change=InvestigationState.set_social_query,
                    class_name="flex-1 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-300 outline-none transition-all",
                    default_value=InvestigationState.social_query,
                ),
                rx.el.button(
                    rx.cond(
                        InvestigationState.is_loading_social,
                        rx.spinner(size="1"),
                        "Search Platforms",
                    ),
                    on_click=InvestigationState.search_social,
                    disabled=InvestigationState.is_loading_social,
                    class_name="bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70 flex items-center gap-2",
                ),
                class_name="flex gap-3 mb-6",
            ),
            rx.cond(
                InvestigationState.social_results.length() > 0,
                rx.el.div(
                    rx.el.h3(
                        "Platform Analysis",
                        class_name="text-lg font-semibold text-gray-800 mb-4",
                    ),
                    rx.el.div(
                        rx.foreach(InvestigationState.social_results, social_card),
                        class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
                    ),
                    class_name="animate-in fade-in slide-in-from-bottom-4 duration-500",
                ),
            ),
            class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        ),
        class_name="max-w-3xl mx-auto",
    )


def phone_tool() -> rx.Component:
    return rx.el.div(
        ethical_reminder_card(
            "Phone Number Tracking",
            "Phone tracking data is for identification of carrier and approximate location only. Do not use for harassment or stalking. Adhere to local telecom regulations.",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.input(
                    placeholder="Enter Phone Number (e.g., +2348030000000)",
                    on_change=InvestigationState.set_phone_query,
                    class_name="flex-1 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-300 outline-none transition-all",
                    default_value=InvestigationState.phone_query,
                ),
                rx.el.button(
                    rx.cond(
                        InvestigationState.is_loading_phone,
                        rx.spinner(size="1"),
                        "Trace Number",
                    ),
                    on_click=InvestigationState.search_phone,
                    disabled=InvestigationState.is_loading_phone,
                    class_name="bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70 flex items-center gap-2",
                ),
                class_name="flex gap-3 mb-6",
            ),
            rx.cond(
                InvestigationState.phone_result,
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.span(
                                "Fraud Risk Score",
                                class_name="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1 block",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    InvestigationState.phone_result["fraud_score"],
                                    class_name=rx.cond(
                                        InvestigationState.phone_result["fraud_score"]
                                        > 70,
                                        "text-4xl font-bold text-red-500",
                                        "text-4xl font-bold text-green-500",
                                    ),
                                ),
                                rx.el.span(
                                    "/100", class_name="text-lg text-gray-400 ml-1"
                                ),
                            ),
                            rx.el.div(
                                rx.el.span(
                                    InvestigationState.phone_result["risk_level"],
                                    class_name="text-sm font-semibold uppercase mt-1 block "
                                    + rx.cond(
                                        InvestigationState.phone_result["risk_level"]
                                        == "High",
                                        "text-red-600",
                                        "text-green-600",
                                    ),
                                )
                            ),
                            class_name="bg-gray-50 rounded-xl p-4 border border-gray-100 text-center w-full md:w-40 flex flex-col justify-center",
                        ),
                        rx.el.div(
                            result_row(
                                "Number Format",
                                rx.cond(
                                    InvestigationState.phone_result["valid"],
                                    "Valid",
                                    "Invalid",
                                ),
                            ),
                            result_row(
                                "Line Type", InvestigationState.phone_result["type"]
                            ),
                            result_row(
                                "Carrier / Operator",
                                InvestigationState.phone_result["carrier"],
                                is_highlight=True,
                            ),
                            result_row(
                                "Location", InvestigationState.phone_result["location"]
                            ),
                            result_row(
                                "Time Zone",
                                InvestigationState.phone_result["time_zone"],
                            ),
                            rx.el.div(
                                rx.el.h5(
                                    "Risk Factors",
                                    class_name="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2 mt-4 pt-4 border-t border-gray-200",
                                ),
                                rx.foreach(
                                    InvestigationState.phone_result["risk_factors"],
                                    lambda factor: rx.el.div(
                                        rx.icon(
                                            "flag_triangle_right",
                                            class_name="w-3 h-3 text-orange-500 mr-2",
                                        ),
                                        rx.el.span(
                                            factor, class_name="text-sm text-gray-600"
                                        ),
                                        class_name="flex items-center mb-1",
                                    ),
                                ),
                            ),
                            class_name="flex-1 bg-gray-50 rounded-xl p-5 border border-gray-100",
                        ),
                        class_name="flex flex-col md:flex-row gap-6",
                    ),
                    class_name="animate-in fade-in slide-in-from-bottom-4 duration-500",
                ),
            ),
            class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        ),
        class_name="max-w-3xl mx-auto",
    )


def image_tool() -> rx.Component:
    return rx.el.div(
        ethical_reminder_card(
            "Image Intelligence & Facial Recognition",
            "Facial recognition technology must be used responsibly. Do not use this tool to infringe on personal privacy or for unlawful surveillance. Ensure you have legitimate grounds for investigation.",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label(
                    rx.el.div(
                        rx.icon(
                            "cloud_upload",
                            class_name="w-10 h-10 text-gray-300 mb-3 group-hover:text-orange-500 transition-colors",
                        ),
                        rx.el.p(
                            rx.cond(
                                InvestigationState.uploaded_image_name != "",
                                InvestigationState.uploaded_image_name,
                                "Click or drag image to upload",
                            ),
                            class_name="text-sm font-medium text-gray-600",
                        ),
                        rx.el.p(
                            "Supports JPG, PNG, WEBP",
                            class_name="text-xs text-gray-400 mt-1",
                        ),
                        class_name="flex flex-col items-center justify-center py-12 cursor-pointer",
                    ),
                    rx.upload.root(
                        rx.el.div("Select File"),
                        id="upload_image",
                        accept={"image/*": [".png", ".jpg", ".jpeg", ".webp"]},
                        border="0px solid",
                        padding="0px",
                        class_name="hidden",
                    ),
                    class_name="block w-full border-2 border-dashed border-gray-200 rounded-xl hover:border-orange-400 hover:bg-orange-50/30 transition-all group mb-4 bg-gray-50 overflow-hidden relative",
                ),
                rx.el.div(
                    rx.el.button(
                        "Upload Selected",
                        on_click=InvestigationState.handle_image_upload(
                            rx.upload_files(upload_id="upload_image")
                        ),
                        class_name="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors",
                    ),
                    rx.el.button(
                        rx.cond(
                            InvestigationState.is_loading_image,
                            rx.spinner(size="1"),
                            "Start Recognition Analysis",
                        ),
                        on_click=InvestigationState.analyze_image,
                        disabled=(InvestigationState.uploaded_image_name == "")
                        | InvestigationState.is_loading_image,
                        class_name="bg-gray-900 hover:bg-gray-800 text-white px-6 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ml-auto",
                    ),
                    class_name="flex items-center justify-between mb-6",
                ),
            ),
            rx.cond(
                InvestigationState.image_result,
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.h4(
                                "Identity Match",
                                class_name="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3",
                            ),
                            rx.el.div(
                                rx.icon(
                                    "user-check",
                                    class_name="w-8 h-8 text-orange-500 mb-2",
                                ),
                                rx.el.h3(
                                    InvestigationState.image_result[
                                        "identified_person"
                                    ],
                                    class_name="text-xl font-bold text-gray-900",
                                ),
                                rx.el.div(
                                    rx.el.span(
                                        "Confidence: ",
                                        class_name="text-sm text-gray-500",
                                    ),
                                    rx.el.span(
                                        InvestigationState.image_result["confidence"],
                                        class_name="text-sm font-bold text-green-600",
                                    ),
                                    class_name="mt-1",
                                ),
                                class_name="bg-orange-50 rounded-xl p-5 border border-orange-100 mb-4",
                            ),
                            rx.el.div(
                                rx.el.h5(
                                    "Contact Discovery",
                                    class_name="text-xs font-bold text-gray-700 mb-2",
                                ),
                                rx.foreach(
                                    InvestigationState.image_result["emails"],
                                    lambda email: rx.el.div(
                                        rx.icon(
                                            "mail",
                                            class_name="w-3 h-3 text-gray-400 mr-2",
                                        ),
                                        rx.el.span(
                                            email, class_name="text-sm text-gray-600"
                                        ),
                                        class_name="flex items-center mb-1",
                                    ),
                                ),
                                class_name="mb-6",
                            ),
                            rx.el.div(
                                rx.el.h5(
                                    "Social Footprint",
                                    class_name="text-xs font-bold text-gray-700 mb-2",
                                ),
                                rx.foreach(
                                    InvestigationState.image_result["social_profiles"],
                                    lambda profile: rx.el.a(
                                        rx.icon("link", class_name="w-3 h-3 mr-2"),
                                        rx.el.span(
                                            profile["platform"],
                                            class_name="text-sm font-medium",
                                        ),
                                        rx.icon(
                                            "external-link",
                                            class_name="w-3 h-3 ml-auto opacity-50",
                                        ),
                                        href=profile["url"],
                                        class_name="flex items-center p-2 bg-gray-50 rounded-lg text-gray-700 hover:bg-gray-100 mb-2 transition-colors",
                                    ),
                                ),
                            ),
                            class_name="md:col-span-4",
                        ),
                        rx.el.div(
                            rx.el.h4(
                                "Intelligence Report",
                                class_name="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3",
                            ),
                            rx.el.div(
                                rx.el.h5(
                                    "EXIF Metadata",
                                    class_name="text-xs font-bold text-gray-700 mb-3",
                                ),
                                rx.el.div(
                                    rx.el.div(
                                        rx.el.span(
                                            "Device",
                                            class_name="text-xs text-gray-400 block",
                                        ),
                                        rx.el.span(
                                            InvestigationState.image_result["exif"][
                                                "Device"
                                            ],
                                            class_name="text-sm font-medium text-gray-800",
                                        ),
                                        class_name="p-3 bg-gray-50 rounded-lg",
                                    ),
                                    rx.el.div(
                                        rx.el.span(
                                            "Date Taken",
                                            class_name="text-xs text-gray-400 block",
                                        ),
                                        rx.el.span(
                                            InvestigationState.image_result["exif"][
                                                "Date Taken"
                                            ],
                                            class_name="text-sm font-medium text-gray-800",
                                        ),
                                        class_name="p-3 bg-gray-50 rounded-lg",
                                    ),
                                    rx.el.div(
                                        rx.el.span(
                                            "Location Data",
                                            class_name="text-xs text-gray-400 block",
                                        ),
                                        rx.el.span(
                                            InvestigationState.image_result["exif"][
                                                "Location"
                                            ],
                                            class_name="text-sm font-medium text-gray-800",
                                        ),
                                        class_name="p-3 bg-gray-50 rounded-lg col-span-2",
                                    ),
                                    class_name="grid grid-cols-2 gap-3 mb-6",
                                ),
                            ),
                            rx.el.div(
                                rx.el.h5(
                                    "Media Mentions & News",
                                    class_name="text-xs font-bold text-gray-700 mb-3",
                                ),
                                rx.foreach(
                                    InvestigationState.image_result["media_mentions"],
                                    lambda media: rx.el.div(
                                        rx.el.div(
                                            rx.el.span(
                                                media["source"],
                                                class_name="text-xs font-bold text-orange-600 mb-1 block",
                                            ),
                                            rx.el.h6(
                                                media["title"],
                                                class_name="text-sm font-medium text-gray-900 mb-1",
                                            ),
                                            rx.el.span(
                                                media["date"],
                                                class_name="text-xs text-gray-400",
                                            ),
                                        ),
                                        class_name="border-l-2 border-gray-200 pl-4 py-1 mb-4 hover:border-orange-400 transition-colors",
                                    ),
                                ),
                                rx.el.h5(
                                    "Recent Public Activity",
                                    class_name="text-xs font-bold text-gray-700 mb-3 mt-6 pt-6 border-t border-gray-100",
                                ),
                                rx.foreach(
                                    InvestigationState.image_result["recent_posts"],
                                    lambda post: rx.el.div(
                                        rx.el.div(
                                            rx.icon(
                                                "message-circle",
                                                class_name="w-3 h-3 text-blue-500 mr-2",
                                            ),
                                            rx.el.span(
                                                post["platform"],
                                                class_name="text-xs font-bold text-gray-500",
                                            ),
                                            rx.el.span(
                                                "• " + post["date"],
                                                class_name="text-xs text-gray-400 ml-2",
                                            ),
                                            class_name="flex items-center mb-1",
                                        ),
                                        rx.el.p(
                                            post["content"],
                                            class_name="text-sm text-gray-800 italic mb-1",
                                        ),
                                        rx.el.span(
                                            post["engagement"],
                                            class_name="text-xs text-gray-400 font-medium",
                                        ),
                                        class_name="p-3 bg-gray-50 rounded-lg border border-gray-100 mb-2",
                                    ),
                                ),
                            ),
                            class_name="md:col-span-8 bg-white",
                        ),
                        class_name="grid grid-cols-1 md:grid-cols-12 gap-8",
                    ),
                    class_name="animate-in fade-in slide-in-from-bottom-4 duration-500 mt-8 pt-8 border-t border-gray-100",
                ),
            ),
            class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        ),
        class_name="max-w-3xl mx-auto",
    )


def imei_tool() -> rx.Component:
    return rx.el.div(
        ethical_reminder_card(
            "IMEI Device Tracking",
            "IMEI lookup should only be used for verifying device status for theft recovery, loss prevention, or legitimate ownership verification. Do not use for unauthorized tracking.",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.input(
                    placeholder="Enter IMEI (15 digits, e.g. 3548...)",
                    on_change=InvestigationState.set_imei_query,
                    class_name="flex-1 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-300 outline-none transition-all",
                    default_value=InvestigationState.imei_query,
                ),
                rx.el.button(
                    rx.cond(
                        InvestigationState.is_loading_imei,
                        rx.spinner(size="1"),
                        "Check Device",
                    ),
                    on_click=InvestigationState.search_imei,
                    disabled=InvestigationState.is_loading_imei,
                    class_name="bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-70 flex items-center gap-2",
                ),
                class_name="flex gap-3 mb-6",
            ),
            rx.cond(
                InvestigationState.imei_result,
                rx.el.div(
                    rx.el.div(
                        rx.cond(
                            InvestigationState.imei_result["valid"],
                            rx.el.div(
                                rx.el.div(
                                    rx.el.div(
                                        rx.el.span(
                                            "Status",
                                            class_name="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1 block",
                                        ),
                                        rx.el.div(
                                            rx.icon(
                                                rx.cond(
                                                    InvestigationState.imei_result[
                                                        "theft_record"
                                                    ],
                                                    "alert-triangle",
                                                    "check-circle",
                                                ),
                                                class_name=rx.cond(
                                                    InvestigationState.imei_result[
                                                        "theft_record"
                                                    ],
                                                    "text-red-500",
                                                    "text-green-500",
                                                )
                                                + " w-8 h-8 mb-2",
                                            ),
                                            rx.el.h3(
                                                InvestigationState.imei_result[
                                                    "blacklist_status"
                                                ],
                                                class_name=rx.cond(
                                                    InvestigationState.imei_result[
                                                        "theft_record"
                                                    ],
                                                    "text-xl font-bold text-red-600",
                                                    "text-xl font-bold text-green-600",
                                                ),
                                            ),
                                            rx.el.div(
                                                rx.el.span(
                                                    "Source: ",
                                                    class_name="text-xs text-gray-400",
                                                ),
                                                rx.el.span(
                                                    InvestigationState.imei_result[
                                                        "db_source"
                                                    ],
                                                    class_name="text-xs font-semibold text-gray-600",
                                                ),
                                                class_name="mt-1 px-2 py-1 bg-white rounded border border-gray-200 inline-block",
                                            ),
                                        ),
                                        rx.el.div(
                                            rx.el.span(
                                                "Risk Score",
                                                class_name="text-xs font-medium text-gray-400 mt-4 block",
                                            ),
                                            rx.el.div(
                                                rx.el.span(
                                                    InvestigationState.imei_result[
                                                        "risk_score"
                                                    ],
                                                    class_name="text-2xl font-bold text-gray-800",
                                                ),
                                                rx.el.span(
                                                    "/100",
                                                    class_name="text-sm text-gray-400",
                                                ),
                                                class_name="flex items-baseline gap-1",
                                            ),
                                        ),
                                        class_name="bg-gray-50 rounded-xl p-4 border border-gray-100 text-center w-full md:w-48 flex flex-col",
                                    ),
                                    rx.el.div(
                                        rx.el.h4(
                                            "Device Specifications",
                                            class_name="text-sm font-bold text-gray-900 mb-4",
                                        ),
                                        rx.el.div(
                                            result_row(
                                                "Manufacturer",
                                                InvestigationState.imei_result["brand"],
                                            ),
                                            result_row(
                                                "Model",
                                                InvestigationState.imei_result["model"],
                                                is_highlight=True,
                                            ),
                                            result_row(
                                                "Configuration",
                                                InvestigationState.imei_result["specs"],
                                            ),
                                            result_row(
                                                "Purchase Date",
                                                InvestigationState.imei_result[
                                                    "purchase_date"
                                                ],
                                            ),
                                            result_row(
                                                "Warranty",
                                                InvestigationState.imei_result[
                                                    "warranty_status"
                                                ],
                                            ),
                                            result_row(
                                                "Country of Sale",
                                                InvestigationState.imei_result[
                                                    "country_sold"
                                                ],
                                            ),
                                            result_row(
                                                "Carrier Lock",
                                                InvestigationState.imei_result[
                                                    "carrier_lock"
                                                ],
                                                is_highlight=True,
                                            ),
                                            rx.el.div(
                                                rx.el.h5(
                                                    "Risk Analysis",
                                                    class_name="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3 mt-6 pt-6 border-t border-gray-100",
                                                ),
                                                rx.foreach(
                                                    InvestigationState.imei_result[
                                                        "risk_factors"
                                                    ],
                                                    lambda factor: rx.el.div(
                                                        rx.icon(
                                                            "shield-alert",
                                                            class_name="w-3 h-3 text-orange-500 mr-2",
                                                        ),
                                                        rx.el.span(
                                                            factor,
                                                            class_name="text-sm text-gray-600",
                                                        ),
                                                        class_name="flex items-center mb-2",
                                                    ),
                                                ),
                                                class_name="w-full",
                                            ),
                                            class_name="flex-1",
                                        ),
                                        class_name="flex-1 bg-white rounded-xl p-6 border border-gray-100 shadow-sm",
                                    ),
                                    class_name="col-span-12 flex flex-col md:flex-row gap-6",
                                )
                            ),
                            rx.el.div(
                                rx.el.div(
                                    rx.icon(
                                        "ban", class_name="w-12 h-12 text-red-400 mb-3"
                                    ),
                                    rx.el.h3(
                                        "Invalid IMEI Format",
                                        class_name="text-lg font-bold text-gray-900",
                                    ),
                                    rx.el.p(
                                        "The IMEI provided does not match the standard 15-digit format. Please check the number and try again.",
                                        class_name="text-sm text-gray-500 mt-1 max-w-xs mx-auto",
                                    ),
                                ),
                                class_name="md:col-span-8 bg-white",
                            ),
                        ),
                        class_name="grid grid-cols-1 md:grid-cols-12 gap-8",
                    ),
                    class_name="animate-in fade-in slide-in-from-bottom-4 duration-500 mt-8 pt-8 border-t border-gray-100",
                ),
            ),
            class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        ),
        class_name="max-w-3xl mx-auto",
    )


def tools_tabs() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            tab_button("Domain", "domain", "globe"),
            tab_button("IP", "ip", "map-pin"),
            tab_button("Email", "email", "mail"),
            tab_button("Social", "social", "users"),
            tab_button("Phone", "phone", "phone"),
            tab_button("Image", "image", "scan-face"),
            tab_button("IMEI", "imei", "smartphone"),
            tab_button("Map", "map", "network"),
            class_name="flex flex-nowrap border-b border-gray-200 mb-8 overflow-x-auto w-full pb-px gap-1",
        ),
        rx.match(
            InvestigationState.active_tab,
            ("domain", domain_tool()),
            ("ip", ip_tool()),
            ("email", email_tool()),
            ("social", social_tool()),
            ("phone", phone_tool()),
            ("image", image_tool()),
            ("imei", imei_tool()),
            ("map", network_map_tool()),
            domain_tool(),
        ),
        class_name="w-full",
    )