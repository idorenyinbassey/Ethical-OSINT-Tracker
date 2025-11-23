import reflex as rx
from typing import TypedDict, Optional
import asyncio
import re
import random
import hashlib
import datetime

TAC_DB = {
    "35278811": ("Apple", "iPhone 13 Pro", "128GB"),
    "35486809": ("Apple", "iPhone 11", "64GB"),
    "35655310": ("Samsung", "Galaxy S21", "256GB"),
    "35845309": ("Samsung", "Galaxy Note 20 Ultra", "512GB"),
    "35297811": ("Google", "Pixel 6 Pro", "128GB"),
    "35782311": ("Google", "Pixel 7", "256GB"),
    "35912308": ("OnePlus", "9 Pro", "256GB"),
    "86912305": ("Xiaomi", "Mi 11 Ultra", "512GB"),
    "01591200": ("Samsung", "Galaxy Tab S8", "Wi-Fi"),
    "35320010": ("Apple", "iPad Pro 11", "Cellular"),
    "35693809": ("Apple", "iPhone 12", "128GB"),
    "35462411": ("Samsung", "Galaxy A53", "128GB"),
    "35186611": ("Samsung", "Galaxy S22 Ultra", "512GB"),
    "35572809": ("Apple", "iPhone XR", "64GB"),
    "35224011": ("Google", "Pixel 6a", "128GB"),
}
KNOWN_DOMAINS = {
    "google.com": {
        "registrar": "MarkMonitor Inc.",
        "status": "clientDeleteProhibited",
        "ns_count": 4,
    },
    "reflex.dev": {
        "registrar": "NameCheap, Inc.",
        "status": "clientTransferProhibited",
        "ns_count": 2,
    },
    "example.com": {
        "registrar": "RESERVED-Internet Assigned Numbers Authority",
        "status": "Active",
        "ns_count": 2,
    },
}
KNOWN_IPS = {
    "8.8.8.8": ("Mountain View", "United States", "Google LLC", "AS15169"),
    "1.1.1.1": ("Los Angeles", "United States", "Cloudflare, Inc.", "AS13335"),
    "127.0.0.1": ("Localhost", "Loopback", "IANA", "-"),
}


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


class IMEIResult(TypedDict):
    imei: str
    valid: bool
    brand: str
    model: str
    specs: str
    blacklist_status: str
    theft_record: bool
    warranty_status: str
    purchase_date: str
    carrier_lock: str
    country_sold: str
    risk_score: int
    db_source: str
    risk_factors: list[str]


class NetworkNode(TypedDict):
    id: str
    type: str
    label: str
    icon: str


class NetworkEdge(TypedDict):
    source: str
    target: str
    label: str


class InvestigationState(rx.State):
    active_tab: str = "domain"
    network_nodes: list[NetworkNode] = []
    network_edges: list[NetworkEdge] = []
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
    imei_query: str = ""
    imei_result: Optional[IMEIResult] = None
    is_loading_imei: bool = False

    def _get_seed(self, input_str: str) -> int:
        """Generate a consistent integer seed from an input string."""
        return int(hashlib.sha256(input_str.encode()).hexdigest(), 16) % 10**8

    def _add_to_graph(
        self,
        node: NetworkNode,
        connected_to_id: Optional[str] = None,
        edge_label: str = "",
    ):
        """Helper to add nodes and edges to the graph."""
        if not any((n["id"] == node["id"] for n in self.network_nodes)):
            self.network_nodes.append(node)
        if connected_to_id:
            edge = {
                "source": connected_to_id,
                "target": node["id"],
                "label": edge_label,
            }
            if not any(
                (
                    e["source"] == edge["source"] and e["target"] == edge["target"]
                    for e in self.network_edges
                )
            ):
                self.network_edges.append(edge)

    @rx.event
    def set_active_tab(self, tab: str):
        self.active_tab = tab

    @rx.event
    async def search_domain(self):
        if not self.domain_query:
            return
        domain_regex = (
            "^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,}$"
        )
        if not re.match(domain_regex, self.domain_query):
            self.domain_result = None
            yield
            return
        self.is_loading_domain = True
        self.domain_result = None
        yield
        await asyncio.sleep(1.0)
        if self.domain_query.lower() in KNOWN_DOMAINS:
            data = KNOWN_DOMAINS[self.domain_query.lower()]
            registrar = data["registrar"]
            status = data["status"]
            ns_count = data["ns_count"]
            seed = 12345
        else:
            seed = self._get_seed(self.domain_query)
            rng = random.Random(seed)
            registrars = [
                "GoDaddy.com, LLC",
                "NameCheap, Inc.",
                "MarkMonitor Inc.",
                "SafeNames Ltd.",
                "Tucows Domains Inc.",
            ]
            statuses = [
                "Active",
                "ClientTransferProhibited",
                "RedemptionPeriod",
                "PendingDelete",
            ]
            registrar = rng.choice(registrars)
            status = rng.choice(statuses)
            ns_count = rng.randint(2, 5)
        rng = random.Random(seed)
        creation_year = rng.randint(2015, 2023)
        creation_date = (
            f"{creation_year}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        )
        expiration_date = f"{creation_year + rng.randint(1, 5)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        self.domain_result = {
            "domain": self.domain_query,
            "registrar": registrar,
            "creation_date": creation_date,
            "expiration_date": expiration_date,
            "name_servers": [
                f"ns{i}.{self.domain_query}" for i in range(1, ns_count + 1)
            ],
            "status": status,
            "dns_records": rng.randint(5, 25),
        }
        self._add_to_graph(
            {
                "id": self.domain_query,
                "type": "domain",
                "label": self.domain_query,
                "icon": "globe",
            }
        )
        self.is_loading_domain = False

    @rx.event
    async def search_ip(self):
        if not self.ip_query:
            return
        ip_regex = "^((25[0-5]|(2[0-4]|1\\d|[1-9]|)\\d)\\.?\\b){4}$"
        if not re.match(ip_regex, self.ip_query):
            self.ip_result = None
            yield
            return
        self.is_loading_ip = True
        self.ip_result = None
        yield
        await asyncio.sleep(0.8)
        if self.ip_query in KNOWN_IPS:
            k_city, k_country, k_isp, k_asn = KNOWN_IPS[self.ip_query]
            seed = self._get_seed(self.ip_query)
            rng = random.Random(seed)
            loc = (k_city, k_country, k_asn, k_isp)
        else:
            seed = self._get_seed(self.ip_query)
            rng = random.Random(seed)
            locations = [
                ("Amsterdam", "Netherlands", "AS14061", "DigitalOcean, LLC"),
                ("Ashburn", "United States", "AS14618", "Amazon.com, Inc."),
                ("Lagos", "Nigeria", "AS29465", "MTN Nigeria"),
                ("London", "United Kingdom", "AS5089", "Virgin Media"),
                ("Singapore", "Singapore", "AS13335", "Cloudflare, Inc."),
            ]
            loc = rng.choice(locations)
        self.ip_result = {
            "ip": self.ip_query,
            "city": loc[0],
            "country": loc[1],
            "isp": loc[3],
            "asn": loc[2],
            "threat_score": rng.randint(0, 100),
            "is_proxy": rng.choice([True, False])
            if rng.randint(0, 100) > 70
            else False,
        }
        self._add_to_graph(
            {
                "id": self.ip_query,
                "type": "ip",
                "label": self.ip_query,
                "icon": "map-pin",
            }
        )
        self.is_loading_ip = False

    @rx.event
    async def search_email(self):
        if not self.email_query:
            return
        email_regex = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, self.email_query):
            self.email_result = None
            yield
            return
        self.is_loading_email = True
        self.email_result = None
        yield
        await asyncio.sleep(1.0)
        seed = self._get_seed(self.email_query)
        rng = random.Random(seed)
        breaches_list = [
            "Collection #1",
            "Verifications.io",
            "ExploitIn",
            "Anti Public Combo",
            "Canva",
        ]
        is_clean = self.email_query.lower().startswith(("sec", "admin", "support"))
        has_breach = False if is_clean else rng.random() > 0.3
        breach_count = rng.randint(1, 15) if has_breach else 0
        self.email_result = {
            "email": self.email_query,
            "valid_format": True,
            "disposable": rng.random() > 0.9 if not is_clean else False,
            "breaches": breach_count,
            "domain_reputation": "High"
            if is_clean
            else rng.choice(["High", "Medium", "Low"]),
            "last_breach": f"{rng.randint(2018, 2023)}-{rng.randint(1, 12):02d} ({rng.choice(breaches_list)})"
            if has_breach
            else None,
        }
        self._add_to_graph(
            {
                "id": self.email_query,
                "type": "email",
                "label": self.email_query,
                "icon": "mail",
            }
        )
        if has_breach:
            self._add_to_graph(
                {
                    "id": f"Breach_{seed}",
                    "type": "breach",
                    "label": f"{breach_count} Breaches",
                    "icon": "alert-triangle",
                },
                connected_to_id=self.email_query,
                edge_label="found_in",
            )
        self.is_loading_email = False

    @rx.event
    async def search_social(self):
        if not self.social_query:
            return
        self.is_loading_social = True
        self.social_results = []
        yield
        await asyncio.sleep(1.5)
        seed = self._get_seed(self.social_query)
        rng = random.Random(seed)
        username = self.social_query
        platforms = [
            "Twitter",
            "GitHub",
            "Instagram",
            "Reddit",
            "LinkedIn",
            "Pinterest",
            "TikTok",
            "Telegram",
        ]
        results = []
        found_platforms = []
        for platform in platforms:
            exists = rng.random() > 0.4
            if exists:
                url = f"{platform.lower()}.com/{username}"
                if platform == "Reddit":
                    url = f"reddit.com/user/{username}"
                if platform == "LinkedIn":
                    url = f"linkedin.com/in/{username}"
                results.append(
                    {
                        "platform": platform,
                        "username": username,
                        "exists": True,
                        "url": url,
                    }
                )
                found_platforms.append(platform)
            else:
                results.append(
                    {
                        "platform": platform,
                        "username": username,
                        "exists": False,
                        "url": "",
                    }
                )
        self.social_results = results
        user_node_id = f"user_{username}"
        self._add_to_graph(
            {"id": user_node_id, "type": "username", "label": username, "icon": "user"}
        )
        for p in found_platforms:
            self._add_to_graph(
                {"id": f"{p}_{username}", "type": "social", "label": p, "icon": "link"},
                connected_to_id=user_node_id,
                edge_label="account",
            )
        self.is_loading_social = False

    @rx.event
    async def search_phone(self):
        if not self.phone_query:
            return
        self.is_loading_phone = True
        self.phone_result = None
        yield
        await asyncio.sleep(1.5)
        is_nigerian = (
            self.phone_query.startswith("+234")
            or self.phone_query.startswith("08")
            or self.phone_query.startswith("07")
            or self.phone_query.startswith("09")
        )
        seed = self._get_seed(self.phone_query)
        rng = random.Random(seed)
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
        fraud_base = rng.randint(0, 50)
        if "99" in self.phone_query or rng.random() > 0.8:
            fraud_base += 40
            risk_factors.append("High Volume of Spam Reports")
            risk_factors.append("Associated with Phishing Campaigns")
        elif is_nigerian and carrier == "Unknown Nigerian Carrier":
            fraud_base += 20
            risk_factors.append("Unregistered Carrier Prefix")
        else:
            risk_factors.append("No Recent Abuse Reports")
            risk_factors.append("Active Service Line")
        fraud_score = min(fraud_base, 99)
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
        self._add_to_graph(
            {
                "id": self.phone_query,
                "type": "phone",
                "label": self.phone_query,
                "icon": "phone",
            }
        )
        self._add_to_graph(
            {"id": f"loc_{seed}", "type": "location", "label": location, "icon": "map"},
            connected_to_id=self.phone_query,
            edge_label="located_in",
        )
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
        seed = self._get_seed(self.uploaded_image_name)
        rng = random.Random(seed)
        names = [
            "Jonathan Doe",
            "Sarah Connor",
            "Mike Ross",
            "Jessica Pearson",
            "Harvey Specter",
        ]
        name = rng.choice(names)
        self.image_result = {
            "identified_person": f"{name} (Potential Match)",
            "confidence": f"{rng.randint(85, 99)}.{rng.randint(0, 9)}%",
            "emails": [
                f"{name.split(' ')[0].lower()}@example.com",
                f"{name.replace(' ', '.').lower()}@protonmail.com",
            ],
            "social_profiles": [
                {
                    "platform": "Facebook",
                    "url": f"facebook.com/{name.replace(' ', '')}",
                },
                {
                    "platform": "LinkedIn",
                    "url": f"linkedin.com/in/{name.replace(' ', '-').lower()}",
                },
                {
                    "platform": "Twitter",
                    "url": f"twitter.com/{name.split(' ')[0].lower()}_real",
                },
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
        person_id = f"person_{seed}"
        self._add_to_graph(
            {"id": person_id, "type": "person", "label": name, "icon": "user-check"}
        )
        self._add_to_graph(
            {
                "id": f"img_{seed}",
                "type": "image",
                "label": "Uploaded Image",
                "icon": "image",
            },
            connected_to_id=person_id,
            edge_label="matched_to",
        )
        self.is_loading_image = False

    @rx.event
    def clear_graph(self):
        self.network_nodes = []
        self.network_edges = []

    @rx.var
    def nodes_by_category(self) -> dict[str, list[NetworkNode]]:
        categories = {
            "Infrastructure": ["domain", "ip", "location"],
            "Identity": ["email", "username", "phone", "person", "imei"],
            "Evidence": ["breach", "social", "image", "alert"],
        }
        result = {"Infrastructure": [], "Identity": [], "Evidence": [], "Other": []}
        for node in self.network_nodes:
            found = False
            for cat, types in categories.items():
                if node["type"] in types:
                    result[cat].append(node)
                    found = True
                    break
            if not found:
                result["Other"].append(node)
        return result

    @rx.event
    def set_imei_query(self, query: str):
        self.imei_query = query

    @rx.event
    async def search_imei(self):
        if not self.imei_query:
            return
        self.is_loading_imei = True
        self.imei_result = None
        yield
        await asyncio.sleep(1.5)
        clean_imei = self.imei_query.strip().replace("-", "").replace(" ", "")
        is_valid_format = len(clean_imei) == 15 and clean_imei.isdigit()
        if not is_valid_format:
            self.imei_result = {
                "imei": self.imei_query,
                "valid": False,
                "brand": "Unknown",
                "model": "Unknown",
                "specs": "N/A",
                "blacklist_status": "Invalid Format",
                "theft_record": False,
                "warranty_status": "N/A",
                "purchase_date": "N/A",
                "carrier_lock": "N/A",
                "country_sold": "N/A",
                "risk_score": 0,
                "db_source": "Validation Service",
                "risk_factors": [],
            }
            self.is_loading_imei = False
            return
        tac = clean_imei[:8]
        if tac in TAC_DB:
            brand, model, specs = TAC_DB[tac]
            is_known_tac = True
        else:
            seed = self._get_seed(clean_imei)
            rng = random.Random(seed)
            brands = [
                ("Apple", "iPhone 15 Pro Max", "256GB, Natural Titanium"),
                ("Samsung", "Galaxy S24 Ultra", "512GB, Titanium Black"),
                ("Google", "Pixel 8 Pro", "128GB, Obsidian"),
                ("Xiaomi", "13 Ultra", "512GB, Black"),
                ("OnePlus", "12", "256GB, Emerald Green"),
            ]
            brand, model, specs = rng.choice(brands)
            is_known_tac = False
        seed = self._get_seed(clean_imei)
        rng = random.Random(seed)
        countries = [
            "United States",
            "United Kingdom",
            "Nigeria",
            "Germany",
            "Canada",
            "UAE",
        ]
        country = rng.choice(countries)
        carriers = [
            "Locked (AT&T)",
            "Locked (Verizon)",
            "Unlocked",
            "Locked (T-Mobile)",
            "Locked (Vodafone)",
        ]
        carrier = rng.choice(carriers)
        last_digit = int(clean_imei[-1])
        is_stolen = last_digit % 9 == 0
        db_source = (
            "GSMA Database (Online)"
            if rng.random() > 0.5
            else "Police Record (Offline Cache)"
        )
        risk_factors = []
        if is_stolen:
            risk_factors.append("Flagged as Stolen in GSMA Registry")
            risk_factors.append("Multiple Activation Attempts Failed")
            risk_factors.append("Reported Lost by Original Owner")
        else:
            risk_factors.append("No Theft Reports Found")
            risk_factors.append("Valid Manufacturer Serial")
            if rng.random() > 0.7:
                risk_factors.append("Device Registered to Corporate Enterprise")
        self.imei_result = {
            "imei": clean_imei,
            "valid": True,
            "brand": brand,
            "model": model,
            "specs": specs,
            "blacklist_status": "Reported Stolen" if is_stolen else "Clean",
            "theft_record": is_stolen,
            "warranty_status": f"Active (Exp. 2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d})"
            if not is_stolen
            else "Voided",
            "purchase_date": f"2023-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "carrier_lock": carrier,
            "country_sold": country,
            "risk_score": rng.randint(80, 99) if is_stolen else rng.randint(0, 15),
            "db_source": db_source,
            "risk_factors": risk_factors,
        }
        self._add_to_graph(
            {
                "id": clean_imei,
                "type": "imei",
                "label": f"{brand} {model}",
                "icon": "smartphone",
            }
        )
        if is_stolen:
            self._add_to_graph(
                {
                    "id": f"stolen_{seed}",
                    "type": "alert",
                    "label": "Theft Record",
                    "icon": "shield-alert",
                },
                connected_to_id=clean_imei,
                edge_label="flagged_in",
            )
        self.is_loading_imei = False