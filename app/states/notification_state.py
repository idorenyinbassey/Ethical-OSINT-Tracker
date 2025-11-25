"""Notification system state."""
import reflex as rx
from typing import TypedDict
import datetime


class Notification(TypedDict):
    id: int
    title: str
    message: str
    type: str  # 'info', 'success', 'warning', 'error'
    timestamp: str
    read: bool


class NotificationState(rx.State):
    notifications: list[Notification] = []
    is_drawer_open: bool = False
    unread_count: int = 0

    @rx.event
    def toggle_drawer(self):
        self.is_drawer_open = not self.is_drawer_open

    @rx.event
    def close_drawer(self):
        self.is_drawer_open = False

    @rx.event
    def add_notification(self, title: str, message: str, notif_type: str = "info"):
        """Add a new notification."""
        notif_id = len(self.notifications) + 1
        self.notifications.insert(
            0,
            {
                "id": notif_id,
                "title": title,
                "message": message,
                "type": notif_type,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "read": False,
            },
        )
        self.unread_count += 1

    @rx.event
    def mark_as_read(self, notif_id: int):
        """Mark a notification as read."""
        for notif in self.notifications:
            if notif["id"] == notif_id and not notif["read"]:
                notif["read"] = True
                self.unread_count = max(0, self.unread_count - 1)
                break

    @rx.event
    def mark_all_read(self):
        """Mark all notifications as read."""
        for notif in self.notifications:
            notif["read"] = True
        self.unread_count = 0

    @rx.event
    def clear_notifications(self):
        """Clear all notifications."""
        self.notifications = []
        self.unread_count = 0

    @rx.var
    def has_notifications(self) -> bool:
        return len(self.notifications) > 0
