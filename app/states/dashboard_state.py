import reflex as rx
from typing import TypedDict


class ActivityItem(TypedDict):
    id: int
    title: str
    type: str
    timestamp: str
    status: str


class ThreatTrend(TypedDict):
    day: str
    threats: int
    investigations: int


class InvestigationMetric(TypedDict):
    name: str
    open: int
    closed: int
    archived: int


class DashboardState(rx.State):
    active_investigations: int = 24
    threats_identified: int = 156
    cases_closed: int = 89
    search_query: str = ""
    activities: list[ActivityItem] = [
        {
            "id": 1,
            "title": "Suspicious Domain Analysis: secure-login-attempt.com",
            "type": "investigation",
            "timestamp": "10 mins ago",
            "status": "High Risk",
        },
        {
            "id": 2,
            "title": "New Threat Intel: APT-29 Activity",
            "type": "alert",
            "timestamp": "45 mins ago",
            "status": "Critical",
        },
        {
            "id": 3,
            "title": "Case #4092: Social Engineering Report",
            "type": "case",
            "timestamp": "2 hours ago",
            "status": "Updated",
        },
        {
            "id": 4,
            "title": "IP Geolocation Scan: 192.168.1.105",
            "type": "investigation",
            "timestamp": "3 hours ago",
            "status": "Clean",
        },
        {
            "id": 5,
            "title": "Weekly Threat Summary Generated",
            "type": "report",
            "timestamp": "5 hours ago",
            "status": "Completed",
        },
        {
            "id": 6,
            "title": "Database Breach Alert: example_corp",
            "type": "alert",
            "timestamp": "Yesterday",
            "status": "Reviewing",
        },
    ]
    threat_data: list[ThreatTrend] = [
        {"day": "Mon", "threats": 12, "investigations": 8},
        {"day": "Tue", "threats": 19, "investigations": 15},
        {"day": "Wed", "threats": 15, "investigations": 22},
        {"day": "Thu", "threats": 28, "investigations": 18},
        {"day": "Fri", "threats": 35, "investigations": 25},
        {"day": "Sat", "threats": 20, "investigations": 12},
        {"day": "Sun", "threats": 18, "investigations": 10},
    ]
    investigation_metrics: list[InvestigationMetric] = [
        {"name": "Phishing", "open": 15, "closed": 25, "archived": 5},
        {"name": "Malware", "open": 28, "closed": 18, "archived": 10},
        {"name": "Fraud", "open": 12, "closed": 30, "archived": 15},
        {"name": "DDoS", "open": 8, "closed": 12, "archived": 2},
        {"name": "Social", "open": 22, "closed": 15, "archived": 8},
    ]

    @rx.event
    def set_search_query(self, query: str):
        self.search_query = query