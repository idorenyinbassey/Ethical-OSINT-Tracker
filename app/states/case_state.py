import reflex as rx
from typing import TypedDict
import asyncio
from app.repositories.case_repository import list_cases, create_case, delete_case, update_case
from app.states.auth_state import AuthState


class CaseItem(TypedDict):
    id: int
    title: str
    description: str
    status: str
    priority: str


class CaseState(rx.State):
    cases: list[CaseItem] = []
    form_title: str = ""
    form_description: str = ""
    form_priority: str = "medium"
    form_error: str = ""
    is_loading: bool = False
    export_result: str = ""
    is_exporting: bool = False
    is_generating: bool = False

    @rx.var
    def case_options(self) -> list[str]:
        """Generate list of case options for select dropdown."""
        return [f"{c['id']}: {c['title']}" for c in self.cases]

    def set_form_title(self, value: str):
        self.form_title = value

    def set_form_description(self, value: str):
        self.form_description = value

    def set_form_priority(self, value: str):
        self.form_priority = value

    @rx.event
    async def export_cases(self, format: str = "json"):
        """Export cases as JSON or CSV."""
        from app.repositories.case_repository import list_cases
        self.is_exporting = True
        self.export_result = ""
        yield
        await asyncio.sleep(0.5)
        cases = list_cases()
        if format == "json":
            import json
            data = [
                {
                    "id": c.id,
                    "title": c.title,
                    "description": c.description,
                    "status": c.status,
                    "priority": c.priority,
                    "created_at": str(getattr(c, "created_at", "")),
                }
                for c in cases
            ]
            self.export_result = json.dumps(data, indent=2)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "title", "description", "status", "priority", "created_at"])
            writer.writeheader()
            for c in cases:
                writer.writerow({
                    "id": c.id,
                    "title": c.title,
                    "description": c.description,
                    "status": c.status,
                    "priority": c.priority,
                    "created_at": str(getattr(c, "created_at", "")),
                })
            self.export_result = output.getvalue()
        else:
            self.export_result = "Unsupported format"
        self.is_exporting = False
        yield rx.toast.success(f"Exported {len(cases)} cases as {format.upper()}")

    @rx.event
    async def generate_sample_cases(self, count: int = 10):
        """Generate sample cases for demo/testing."""
        from app.repositories.case_repository import create_case
        import random
        self.is_generating = True
        yield
        priorities = ["low", "medium", "high", "critical"]
        for i in range(count):
            title = f"Sample Case {random.randint(1000,9999)}"
            description = f"Demo case generated for testing ({i+1})"
            priority = random.choice(priorities)
            create_case(
                title=title,
                description=description,
                owner_user_id=1,
                priority=priority,
            )
            await asyncio.sleep(0.05)
        self.is_generating = False
        yield rx.toast.success(f"Generated {count} sample cases")

    @rx.event
    def load_cases(self):
        try:
            data = list_cases()
            self.cases = [
                {
                    "id": c.id,
                    "title": c.title,
                    "description": c.description,
                    "status": c.status,
                    "priority": c.priority,
                }
                for c in data
            ]
        except Exception:
            self.cases = []

    @rx.event
    async def create_case_action(self):
        if not self.form_title:
            self.form_error = "Title is required"
            yield
            return
        self.is_loading = True
        self.form_error = ""
        yield
        try:
            auth_state = await self.get_state(AuthState)
            create_case(
                title=self.form_title,
                description=self.form_description,
                owner_user_id=auth_state.current_user_id,
                priority=self.form_priority,
            )
            self.form_title = ""
            self.form_description = ""
            self.form_priority = "medium"
            self.load_cases()
            yield rx.toast.success("Case created")
            yield
        except Exception:
            import traceback, sys
            etype, e, tb = sys.exc_info()
            msg = str(e) if e else "Unknown error"
            self.form_error = f"Failed to create case: {msg}"
            yield rx.toast.error(f"Error creating case: {msg}")
        finally:
            self.is_loading = False

    @rx.event
    def delete_case_action(self, case_id: int):
        try:
            if delete_case(case_id):
                self.load_cases()
                yield rx.toast.success("Case deleted")
            else:
                yield rx.toast.error("Case not found")
        except Exception:
            yield rx.toast.error("Failed to delete case")
