import reflex as rx
from app.states.investigation_state import InvestigationState


def tree_node(node) -> rx.Component:
    """Tree node visualization with icon and label"""
    icon_map = {
        "domain": "globe",
        "ip": "map-pin",
        "email": "mail",
        "social": "users",
        "phone": "phone",
        "image": "image",
        "person": "user",
        "device": "smartphone",
        "location": "map",
        "breach": "shield-alert",
        "carrier": "radio-tower",
    }
    
    color_map = {
        "domain": "text-blue-500 bg-blue-50 border-blue-200",
        "ip": "text-green-500 bg-green-50 border-green-200",
        "email": "text-purple-500 bg-purple-50 border-purple-200",
        "social": "text-pink-500 bg-pink-50 border-pink-200",
        "phone": "text-indigo-500 bg-indigo-50 border-indigo-200",
        "image": "text-yellow-500 bg-yellow-50 border-yellow-200",
        "person": "text-orange-500 bg-orange-50 border-orange-200",
        "device": "text-gray-500 bg-gray-50 border-gray-200",
        "location": "text-red-500 bg-red-50 border-red-200",
        "breach": "text-red-600 bg-red-100 border-red-300",
        "carrier": "text-teal-500 bg-teal-50 border-teal-200",
    }
    
    return rx.el.div(
        rx.el.div(
            rx.icon(
                icon_map.get(node["type"], "circle"),
                class_name=f"w-5 h-5 {color_map.get(node['type'], 'text-gray-500')}",
            ),
            rx.el.div(
                rx.el.div(
                    node["label"],
                    class_name="text-xs font-semibold text-gray-900 truncate",
                ),
                rx.el.div(
                    node["type"].capitalize(),
                    class_name="text-[10px] text-gray-500 uppercase tracking-wide",
                ),
                class_name="ml-2 flex-1 min-w-0",
            ),
            class_name="flex items-center",
        ),
        class_name=f"px-3 py-2 {color_map.get(node['type'], 'bg-gray-50 border-gray-200')} border rounded-lg hover:shadow-md transition-all cursor-pointer",
    )


def tree_edge_label(edge) -> rx.Component:
    """Edge relationship label"""
    return rx.el.div(
        edge.get("label", "related_to"),
        class_name="px-2 py-1 bg-gray-100 text-[10px] text-gray-600 rounded font-medium border border-gray-200",
    )


def tree_category_section(category_name: str, nodes: list) -> rx.Component:
    """Category section with grouped nodes"""
    icon_map = {
        "domain": "globe",
        "ip": "map-pin", 
        "email": "mail",
        "social": "users",
        "phone": "phone",
        "image": "image",
        "person": "user",
        "device": "smartphone",
        "location": "map",
        "breach": "shield-alert",
        "carrier": "radio-tower",
    }
    
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(
                    icon_map.get(category_name, "folder"),
                    class_name="w-5 h-5 text-orange-500",
                ),
                rx.el.h3(
                    f"{category_name.capitalize()}s",
                    class_name="text-sm font-bold text-gray-900 ml-2",
                ),
                rx.el.span(
                    nodes.length(),
                    class_name="ml-2 px-2 py-0.5 bg-orange-100 text-orange-600 text-xs font-semibold rounded-full",
                ),
                class_name="flex items-center mb-3",
            ),
            rx.el.div(
                rx.foreach(
                    nodes,
                    tree_node,
                ),
                class_name="space-y-2",
            ),
            class_name="p-4 bg-white rounded-xl border border-gray-200",
        ),
    )


def network_tree_view() -> rx.Component:
    """Enhanced tree/network view inspired by Spiderfoot"""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("network", class_name="w-6 h-6 text-orange-500"),
                rx.el.h2(
                    "Investigation Map",
                    class_name="text-xl font-bold text-gray-900 ml-3",
                ),
                rx.el.div(
                    rx.el.button(
                        rx.icon("refresh-cw", class_name="w-4 h-4"),
                        on_click=InvestigationState.clear_graph,
                        class_name="p-2 text-gray-600 hover:text-orange-500 hover:bg-orange-50 rounded-lg transition-colors",
                    ),
                    rx.el.span(
                        InvestigationState.network_nodes.length(),
                        " nodes",
                        class_name="text-sm text-gray-600 ml-2",
                    ),
                    class_name="flex items-center",
                ),
                class_name="flex items-center justify-between mb-6",
            ),
            rx.cond(
                InvestigationState.network_nodes.length() > 0,
                rx.el.div(
                    # Entity Grid
                    rx.el.div(
                        rx.foreach(
                            InvestigationState.network_nodes,
                            tree_node,
                        ),
                        class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3",
                    ),
                ),
                rx.el.div(
                    rx.icon("git-branch", class_name="w-16 h-16 text-gray-300 mb-4"),
                    rx.el.p(
                        "No investigation data yet",
                        class_name="text-lg font-semibold text-gray-900 mb-2",
                    ),
                    rx.el.p(
                        "Start investigating domains, IPs, or emails to build the network map",
                        class_name="text-sm text-gray-500 max-w-md text-center",
                    ),
                    class_name="flex flex-col items-center justify-center py-16 bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200",
                ),
            ),
            class_name="p-6 bg-white rounded-2xl shadow-sm border border-gray-100",
        ),
    )


def connections_list_view() -> rx.Component:
    """List view showing connections between entities"""
    return rx.el.div(
        rx.el.div(
            rx.icon("git-merge", class_name="w-6 h-6 text-orange-500"),
            rx.el.h2(
                "Entity Connections",
                class_name="text-xl font-bold text-gray-900 ml-3",
            ),
            rx.el.span(
                f"{InvestigationState.network_edges.length()} connections",
                class_name="ml-auto text-sm text-gray-600",
            ),
            class_name="flex items-center mb-6",
        ),
        rx.cond(
            InvestigationState.network_edges.length() > 0,
            rx.el.div(
                rx.foreach(
                    InvestigationState.network_edges,
                    lambda edge: rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                edge["source"],
                                class_name="text-xs font-semibold text-gray-900 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg",
                            ),
                            rx.icon("arrow-right", class_name="w-4 h-4 text-gray-400 mx-2"),
                            rx.el.div(
                                edge.get("label", "related"),
                                class_name="text-xs text-gray-600 px-2 py-1 bg-gray-100 rounded",
                            ),
                            rx.icon("arrow-right", class_name="w-4 h-4 text-gray-400 mx-2"),
                            rx.el.div(
                                edge["target"],
                                class_name="text-xs font-semibold text-gray-900 px-3 py-1.5 bg-green-50 border border-green-200 rounded-lg",
                            ),
                            class_name="flex items-center overflow-x-auto",
                        ),
                        class_name="p-3 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow",
                    ),
                ),
                class_name="space-y-2",
            ),
            rx.el.div(
                rx.el.p(
                    "No connections yet",
                    class_name="text-sm text-gray-500",
                ),
                class_name="flex items-center justify-center py-12 bg-gray-50 rounded-xl border border-gray-200",
            ),
        ),
        class_name="p-6 bg-white rounded-2xl shadow-sm border border-gray-100",
    )
