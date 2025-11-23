import reflex as rx
from app.states.dashboard_state import DashboardState

TOOLTIP_PROPS = {
    "content_style": {
        "background": "rgba(255, 255, 255, 0.95)",
        "borderColor": "#E5E7EB",
        "borderRadius": "0.5rem",
        "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "fontSize": "0.875rem",
        "padding": "0.5rem 0.75rem",
    },
    "item_style": {"color": "#374151", "fontWeight": "500"},
    "separator": "",
    "cursor": {"stroke": "#F97316", "strokeWidth": 1},
}


def threat_trends_chart() -> rx.Component:
    return rx.el.div(
        rx.el.h3(
            "Weekly Threat Trends",
            class_name="text-lg font-semibold text-gray-800 mb-4",
        ),
        rx.el.div(
            rx.recharts.area_chart(
                rx.recharts.cartesian_grid(
                    horizontal=True,
                    vertical=False,
                    class_name="opacity-30 stroke-gray-200",
                ),
                rx.recharts.graphing_tooltip(**TOOLTIP_PROPS),
                rx.recharts.area(
                    data_key="threats",
                    stroke="#F97316",
                    fill="#F97316",
                    fill_opacity=0.2,
                    type_="monotone",
                    stroke_width=2,
                ),
                rx.recharts.area(
                    data_key="investigations",
                    stroke="#6B7280",
                    fill="#6B7280",
                    fill_opacity=0.1,
                    type_="monotone",
                    stroke_width=2,
                ),
                rx.recharts.x_axis(
                    data_key="day",
                    axis_line=False,
                    tick_line=False,
                    tick={"fill": "#6B7280", "fontSize": 12},
                    dy=10,
                ),
                rx.recharts.y_axis(
                    axis_line=False,
                    tick_line=False,
                    tick={"fill": "#6B7280", "fontSize": 12},
                ),
                data=DashboardState.threat_data,
                height=300,
                width="100%",
            ),
            class_name="h-[300px] w-full",
        ),
        class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 w-full",
    )


def investigation_metrics_chart() -> rx.Component:
    return rx.el.div(
        rx.el.h3(
            "Investigation Activity",
            class_name="text-lg font-semibold text-gray-800 mb-4",
        ),
        rx.el.div(
            rx.recharts.composed_chart(
                rx.recharts.cartesian_grid(
                    horizontal=True,
                    vertical=False,
                    class_name="opacity-30 stroke-gray-200",
                ),
                rx.recharts.graphing_tooltip(**TOOLTIP_PROPS),
                rx.recharts.bar(
                    data_key="closed", fill="#F97316", bar_size=20, radius=[4, 4, 0, 0]
                ),
                rx.recharts.bar(
                    data_key="archived",
                    fill="#D1D5DB",
                    bar_size=20,
                    radius=[4, 4, 0, 0],
                ),
                rx.recharts.line(
                    data_key="open",
                    stroke="#374151",
                    stroke_width=2,
                    type_="monotone",
                    dot={"r": 4, "fill": "#374151", "strokeWidth": 0},
                ),
                rx.recharts.x_axis(
                    data_key="name",
                    axis_line=False,
                    tick_line=False,
                    tick={"fill": "#6B7280", "fontSize": 12},
                    dy=10,
                ),
                rx.recharts.y_axis(
                    axis_line=False,
                    tick_line=False,
                    tick={"fill": "#6B7280", "fontSize": 12},
                ),
                data=DashboardState.investigation_metrics,
                height=300,
                width="100%",
            ),
            class_name="h-[300px] w-full",
        ),
        class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 w-full",
    )