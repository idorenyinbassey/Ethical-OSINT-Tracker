import reflex as rx
from typing import TypedDict, Optional
import asyncio
import json
import datetime
from app.states.auth_state import AuthState
from app.repositories.intelligence_report_repository import list_reports, create_report, delete_report
from app.repositories.investigation_repository import list_recent
from app.services.rdap_client import fetch_domain
from app.services.ip_client import fetch_ip
from app.services.hibp_client import check_breaches


class ReportItem(TypedDict):
    id: int
    title: str
    summary: str
    indicators: str
    created_at: str
    related_case_id: Optional[int]


class EnrichedIndicator(TypedDict):
    type: str
    value: str
    threat_level: str
    details: dict


class ReportState(rx.State):
    # Report management
    reports: list[ReportItem] = []
    selected_report_id: Optional[int] = None
    is_loading_reports: bool = False
    
    # Report creation
    form_title: str = ""
    form_summary: str = ""
    form_indicators_raw: str = ""  # Comma-separated list
    form_related_case_id: str = ""
    show_create_form: bool = False
    is_creating: bool = False
    
    # Auto-enrichment from recent investigations
    enriched_indicators: list[EnrichedIndicator] = []
    is_enriching: bool = False
    
    # Export
    export_result: Optional[str] = None
    is_exporting: bool = False

    def set_form_title(self, value: str):
        self.form_title = value

    def set_form_summary(self, value: str):
        self.form_summary = value

    def set_form_indicators_raw(self, value: str):
        self.form_indicators_raw = value

    def set_form_related_case_id(self, value: str):
        self.form_related_case_id = value

    def set_export_result(self, value: Optional[str]):
        self.export_result = value

    @rx.event
    def load_reports(self):
        """Load all intelligence reports"""
        self.is_loading_reports = True
        yield
        try:
            rpts = list_reports()
            self.reports = [
                {
                    "id": r.id,
                    "title": r.title,
                    "summary": r.summary,
                    "indicators": r.indicators,
                    "created_at": str(r.created_at),
                    "related_case_id": r.related_case_id,
                }
                for r in rpts
            ]
        except Exception:
            self.reports = []
        self.is_loading_reports = False

    @rx.event
    def show_create_report_form(self):
        """Show the create report form"""
        self.show_create_form = True
        self.form_title = ""
        self.form_summary = ""
        self.form_indicators_raw = ""
        self.form_related_case_id = ""

    @rx.event
    def cancel_create_form(self):
        """Cancel report creation"""
        self.show_create_form = False

    @rx.event
    async def create_new_report(self):
        """Create a new intelligence report"""
        if not self.form_title:
            yield rx.toast.error("Title is required")
            return
        
        self.is_creating = True
        yield
        await asyncio.sleep(0.3)
        
        try:
            case_id = None
            if self.form_related_case_id and self.form_related_case_id.isdigit():
                case_id = int(self.form_related_case_id)
            
            create_report(
                title=self.form_title,
                summary=self.form_summary,
                indicators=self.form_indicators_raw,
                author_user_id=self.get_state(AuthState).current_user_id,
                related_case_id=case_id,
            )
            self.show_create_form = False
            self.load_reports()
            yield rx.toast.success("Report created successfully")
        except Exception as e:
            yield rx.toast.error(f"Failed to create report: {str(e)}")
        finally:
            self.is_creating = False

    @rx.event
    async def delete_report_action(self, report_id: int):
        """Delete an intelligence report"""
        try:
            delete_report(report_id)
            self.load_reports()
            yield rx.toast.success("Report deleted")
        except Exception:
            yield rx.toast.error("Failed to delete report")

    @rx.event
    async def enrich_from_investigations(self):
        """Auto-enrich indicators from recent investigations using live services"""
        self.is_enriching = True
        self.enriched_indicators = []
        yield
        
        # Get recent investigations
        investigations = list_recent(50)
        enriched: list[EnrichedIndicator] = []
        
        # Process up to 10 unique high-value targets
        seen = set()
        count = 0
        
        for inv in investigations:
            if count >= 10:
                break
            
            query = inv.query
            kind = inv.kind
            
            if query in seen:
                continue
            seen.add(query)
            
            try:
                if kind == "domain":
                    rdap_data = await fetch_domain(query)
                    if rdap_data:
                        threat_level = "medium" if rdap_data.get("status") == "clientTransferProhibited" else "low"
                        enriched.append({
                            "type": "domain",
                            "value": query,
                            "threat_level": threat_level,
                            "details": {
                                "registrar": rdap_data.get("registrar", "Unknown"),
                                "created": rdap_data.get("created", "")[:10],
                                "ns_count": len(rdap_data.get("ns", [])),
                            }
                        })
                        count += 1
                
                elif kind == "ip":
                    ip_data = await fetch_ip(query)
                    if ip_data:
                        # Parse threat score from result_json if available
                        threat_level = "low"
                        try:
                            result = json.loads(inv.result_json or "{}")
                            score = result.get("threat_score", 0)
                            threat_level = "high" if score >= 70 else ("medium" if score >= 40 else "low")
                        except Exception:
                            pass
                        
                        enriched.append({
                            "type": "ip",
                            "value": query,
                            "threat_level": threat_level,
                            "details": {
                                "country": ip_data.get("country", ""),
                                "asn": ip_data.get("asn", ""),
                                "org": ip_data.get("org", ""),
                            }
                        })
                        count += 1
                
                elif kind == "email":
                    breaches = await check_breaches(query)
                    if breaches is not None:
                        threat_level = "high" if len(breaches) >= 3 else ("medium" if len(breaches) > 0 else "low")
                        enriched.append({
                            "type": "email",
                            "value": query,
                            "threat_level": threat_level,
                            "details": {
                                "breaches": len(breaches),
                                "latest": breaches[0].get("name", "") if breaches else "None",
                            }
                        })
                        count += 1
                
            except Exception:
                continue
            
            await asyncio.sleep(0.1)
        
        self.enriched_indicators = enriched
        self.is_enriching = False
        yield rx.toast.success(f"Enriched {len(enriched)} indicators from investigations")

    @rx.event
    async def export_reports(self, format: str = "json"):
        """Export all reports as JSON or CSV"""
        self.is_exporting = True
        self.export_result = None
        yield
        await asyncio.sleep(0.3)
        
        if format == "json":
            self.export_result = json.dumps(self.reports, indent=2)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            if self.reports:
                writer = csv.DictWriter(output, fieldnames=["id", "title", "summary", "indicators", "created_at", "related_case_id"])
                writer.writeheader()
                for rpt in self.reports:
                    writer.writerow(rpt)
                self.export_result = output.getvalue()
            else:
                self.export_result = "id,title,summary,indicators,created_at,related_case_id\n"
        else:
            self.export_result = "Unsupported format"
        
        self.is_exporting = False
        yield rx.toast.success(f"Exported {len(self.reports)} reports as {format.upper()}")
