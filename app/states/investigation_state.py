import reflex as rx
from typing import TypedDict, Optional
import asyncio
import re


class DomainResult(TypedDict):
    domain: str
    registrar: str
    creation_date: str
    expiration_date: str
    name_servers: list[str]
    status: str
    dns_records: int


class IPResult(TypedDict):
    ip: str
    city: str
    country: str
    isp: str
    asn: str
    threat_score: int
    is_proxy: bool


class EmailResult(TypedDict):
    email: str
    valid_format: bool
    disposable: bool
    breaches: int
    domain_reputation: str
    last_breach: Optional[str]


class SocialResult(TypedDict):
    platform: str
    username: str
    exists: bool
    url: str


class PhoneResult(TypedDict):
    number: str
    valid: bool
    type: str
    carrier: str
    location: str
    country_code: str
    time_zone: str
    fraud_score: int
    risk_level: str
    risk_factors: list[str]


class SocialLink(TypedDict):
    platform: str
    url: str


class MediaItem(TypedDict):
    source: str
    title: str
    date: str


class PostItem(TypedDict):
    platform: str
    content: str
    date: str
    engagement: str


class ImageResult(TypedDict):
    identified_person: str
    confidence: str
    emails: list[str]
    social_profiles: list[SocialLink]
    media_mentions: list[MediaItem]
    recent_posts: list[PostItem]
    exif: dict[str, str]


class InvestigationState(rx.State):
    active_tab: str = "domain"
    domain_query: str = ""
    domain_result: Optional[DomainResult] = None
    is_loading_domain: bool = False
    ip_query: str = ""
    ip_result: Optional[IPResult] = None
    is_loading_ip: bool = False
    email_query: str = ""
    email_result: Optional[EmailResult] = None
    is_loading_email: bool = False
    social_query: str = ""
    social_results: list[SocialResult] = []
    is_loading_social: bool = False
    phone_query: str = ""
    phone_result: Optional[PhoneResult] = None
    is_loading_phone: bool = False
    uploaded_image_name: str = ""
    image_result: Optional[ImageResult] = None
    is_loading_image: bool = False

    @rx.event
    def set_active_tab(self, tab: str):
        self.active_tab = tab

    @rx.event
    async def search_domain(self):
        if not self.domain_query:
            return
        self.is_loading_domain = True
        self.domain_result = None
        yield
        await asyncio.sleep(1.5)
        self.domain_result = {
            "domain": self.domain_query,
            "registrar": "SafeNames Ltd.",
            "creation_date": "2019-04-12",
            "expiration_date": "2025-04-12",
            "name_servers": ["ns1.secure-dns.com", "ns2.secure-dns.com"],
            "status": "Active (ClientTransferProhibited)",
            "dns_records": 12,
        }
        self.is_loading_domain = False

    @rx.event
    async def search_ip(self):
        if not self.ip_query:
            return
        self.is_loading_ip = True
        self.ip_result = None
        yield
        await asyncio.sleep(1.2)
        self.ip_result = {
            "ip": self.ip_query,
            "city": "Amsterdam",
            "country": "Netherlands",
            "isp": "DigitalOcean, LLC",
            "asn": "AS14061",
            "threat_score": 85 if "1.1" in self.ip_query else 12,
            "is_proxy": True,
        }
        self.is_loading_ip = False

    @rx.event
    async def search_email(self):
        if not self.email_query:
            return
        self.is_loading_email = True
        self.email_result = None
        yield
        await asyncio.sleep(1.0)
        self.email_result = {
            "email": self.email_query,
            "valid_format": True,
            "disposable": False,
            "breaches": 3,
            "domain_reputation": "High",
            "last_breach": "2021-08-15 (Collection #1)",
        }
        self.is_loading_email = False

    @rx.event
    async def search_social(self):
        if not self.social_query:
            return
        self.is_loading_social = True
        self.social_results = []
        yield
        await asyncio.sleep(2.0)
        username = self.social_query
        self.social_results = [
            {
                "platform": "Twitter",
                "username": username,
                "exists": True,
                "url": f"twitter.com/{username}",
            },
            {
                "platform": "GitHub",
                "username": username,
                "exists": True,
                "url": f"github.com/{username}",
            },
            {"platform": "Instagram", "username": username, "exists": False, "url": ""},
            {
                "platform": "Reddit",
                "username": username,
                "exists": True,
                "url": f"reddit.com/user/{username}",
            },
            {"platform": "LinkedIn", "username": username, "exists": False, "url": ""},
        ]
        self.is_loading_social = False

    @rx.event
    async def search_phone(self):
        if not self.phone_query:
            return
        self.is_loading_phone = True
        self.phone_result = None
        yield
        await asyncio.sleep(1.8)
        is_nigerian = (
            self.phone_query.startswith("+234")
            or self.phone_query.startswith("08")
            or self.phone_query.startswith("07")
            or self.phone_query.startswith("09")
        )
        risk_factors = []
        if is_nigerian:
            carrier_map = {
                "0803": "MTN",
                "0806": "MTN",
                "0813": "MTN",
                "0816": "MTN",
                "0810": "MTN",
                "0814": "MTN",
                "0903": "MTN",
                "0906": "MTN",
                "0805": "Glo",
                "0807": "Glo",
                "0811": "Glo",
                "0815": "Glo",
                "0905": "Glo",
                "0802": "Airtel",
                "0808": "Airtel",
                "0812": "Airtel",
                "0902": "Airtel",
                "0907": "Airtel",
                "0809": "9mobile",
                "0817": "9mobile",
                "0818": "9mobile",
                "0909": "9mobile",
            }
            clean_number = self.phone_query.replace("+234", "0")
            prefix = clean_number[:4]
            carrier = carrier_map.get(prefix, "Unknown Nigerian Carrier")
            location = "Lagos, Nigeria"
            tz = "Africa/Lagos (GMT+1)"
        else:
            carrier = "T-Mobile US"
            location = "New York, USA"
            tz = "America/New_York (GMT-5)"
        fraud_score = 12
        if "99" in self.phone_query:
            fraud_score = 78
            risk_factors.append("High Volume of Spam Reports")
            risk_factors.append("Associated with Phishing Campaigns")
        elif is_nigerian and carrier == "Unknown Nigerian Carrier":
            fraud_score = 45
            risk_factors.append("Unregistered Carrier Prefix")
        else:
            risk_factors.append("No Recent Abuse Reports")
            risk_factors.append("Active Service Line")
        self.phone_result = {
            "number": self.phone_query,
            "valid": bool(
                re.match("^\\+?[0-9]{10,14}$", self.phone_query.replace(" ", ""))
            ),
            "type": "Mobile",
            "carrier": carrier,
            "location": location,
            "country_code": "NG" if is_nigerian else "US",
            "time_zone": tz,
            "fraud_score": fraud_score,
            "risk_level": "High"
            if fraud_score > 70
            else "Medium"
            if fraud_score > 40
            else "Low",
            "risk_factors": risk_factors,
        }
        self.is_loading_phone = False

    @rx.event
    async def handle_image_upload(self, files: list[rx.UploadFile]):
        for file in files:
            upload_data = await file.read()
            upload_dir = rx.get_upload_dir()
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = file.name
            file_path = upload_dir / filename
            with file_path.open("wb") as f:
                f.write(upload_data)
            self.uploaded_image_name = filename

    @rx.event
    async def analyze_image(self):
        if not self.uploaded_image_name:
            return
        self.is_loading_image = True
        self.image_result = None
        yield
        await asyncio.sleep(2.5)
        self.image_result = {
            "identified_person": "Jonathan Doe (Potential Match)",
            "confidence": "94.2%",
            "emails": ["j.doe@example.com", "jonathan.d@protonmail.com"],
            "social_profiles": [
                {"platform": "Facebook", "url": "facebook.com/jondoe88"},
                {"platform": "LinkedIn", "url": "linkedin.com/in/jondoe-pro"},
                {"platform": "Twitter", "url": "twitter.com/jonny_d"},
            ],
            "media_mentions": [
                {
                    "source": "TechDaily",
                    "title": "Local Developer wins Hackathon",
                    "date": "2023-11-12",
                },
                {
                    "source": "City News",
                    "title": "Community Cleanup Volunteers",
                    "date": "2024-01-05",
                },
            ],
            "recent_posts": [
                {
                    "platform": "Twitter",
                    "content": "Just landed in Abuja for the cybersecurity conference! #TechLife",
                    "date": "2 days ago",
                    "engagement": "15 Reposts, 42 Likes",
                },
                {
                    "platform": "Instagram",
                    "content": "[Photo] Weekend vibes at the beach.",
                    "date": "1 week ago",
                    "engagement": "128 Likes",
                },
            ],
            "exif": {
                "Device": "iPhone 13 Pro",
                "Date Taken": "2024-02-28 14:32:11",
                "Location": "Lat: 6.5244, Long: 3.3792 (Lagos)",
                "Lens": "26mm f/1.5",
                "ISO": "80",
                "Shutter": "1/1200",
            },
        }
        self.is_loading_image = False