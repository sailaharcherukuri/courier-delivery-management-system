"""Console courier manager. Records are JSON stored in .txt files."""

from dataclasses import asdict, dataclass
from datetime import date, datetime
import json
from pathlib import Path
import uuid

FOLDER = Path(__file__).parent / "data"
FILES = {"customers": "customers.txt", "packages": "packages.txt",
         "agents": "agents.txt", "shipments": "shipments.txt"}
NEXT = {"CREATED": ["CANCELLED"], "ASSIGNED": ["IN_TRANSIT", "CANCELLED"],
        "IN_TRANSIT": ["OUT_FOR_DELIVERY", "CANCELLED"],
        "OUT_FOR_DELIVERY": ["DELIVERED", "CANCELLED"],
        "DELIVERED": [], "CANCELLED": []}


@dataclass
class Person:
    id: str
    name: str
    phone: str


@dataclass
class Customer(Person):
    address: str


@dataclass
class Agent(Person):
    available: bool = True


@dataclass
class Package:
    id: str
    description: str
    weight: float
    kind: str


@dataclass
class Shipment:
    id: str
    customer_id: str
    package_id: str
    recipient: str
    address: str
    expected: str
    charge: float
    status: str = "CREATED"
    agent_id: str = ""
    history: list = None


def ask(label):
    value = input(label).strip()
    if not value:
        raise ValueError("This field cannot be empty.")
    return value


def stamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class CourierApp:
    def __init__(self):
        FOLDER.mkdir(exist_ok=True)
        self.data, self.read_only = {key: {} for key in FILES}, False
        for key, filename in FILES.items():
            path = FOLDER / filename
            try:
                if not path.exists():
                    path.write_text("{}\n", encoding="utf-8")
                value = json.loads(path.read_text(encoding="utf-8") or "{}")
                if not isinstance(value, dict):
                    raise ValueError("expected a JSON object")
                self.data[key] = value
            except (OSError, ValueError) as error:
                print(f"Cannot read {filename}: {error}. File preserved; app is read-only.")
                self.read_only = True

    def save(self):
        if self.read_only:
            raise ValueError("Repair the malformed data file before changing records.")
        for key, filename in FILES.items():
            path = FOLDER / filename
            temp = path.with_suffix(".tmp")
            temp.write_text(json.dumps(self.data[key], indent=2), encoding="utf-8")
            temp.replace(path)

    def add_person(self, kind):
        records = self.data[kind]
        key = ask(f"{kind[:-1].title()} ID: ")
        if key in records:
            raise ValueError("That ID already exists.")
        person = [key, ask("Name: "), ask("Phone: ")]
        record = Customer(*person, ask("Address: ")) if kind == "customers" else Agent(*person)
        records[key] = asdict(record)
        self.save()
        print("Saved.")

    def add_package(self):
        key = ask("Package ID: ")
        if key in self.data["packages"]:
            raise ValueError("That ID already exists.")
        try:
            weight = float(ask("Weight in kg: "))
            if weight <= 0:
                raise ValueError
        except ValueError as error:
            raise ValueError("Weight must be a positive number.") from error
        item = Package(key, ask("Description: "), weight, ask("Type/size: "))
        self.data["packages"][key] = asdict(item)
        self.save()
        print("Package saved.")

    def listing(self, kind):
        records = self.data[kind]
        if not records:
            print("No records found.")
        for key, item in records.items():
            if kind == "customers":
                print(f"{key}: {item['name']} | {item['phone']} | {item['address']}")
            elif kind == "packages":
                print(f"{key}: {item['description']} | {item['weight']} kg | {item['kind']}")
            else:
                busy = any(s["agent_id"] == key and s["status"] not in ("DELIVERED", "CANCELLED")
                           for s in self.data["shipments"].values())
                print(f"{key}: {item['name']} | {item['phone']} | {'Busy' if busy else 'Available'}")

    def create_shipment(self):
        if not self.data["customers"] or not self.data["packages"]:
            raise ValueError("Add a customer and package first.")
        self.listing("customers")
        customer = ask("Customer ID: ")
        self.listing("packages")
        package = ask("Package ID: ")
        if customer not in self.data["customers"] or package not in self.data["packages"]:
            raise ValueError("Customer or package not found.")
        recipient, address = ask("Recipient: "), ask("Delivery address: ")
        expected = ask("Expected delivery (YYYY-MM-DD): ")
        try:
            date.fromisoformat(expected)
        except ValueError as error:
            raise ValueError("Use a real date in YYYY-MM-DD format.") from error
        weight = self.data["packages"][package]["weight"]
        charge = round(50 + 20 * weight, 2)
        print(f"Sample charge: 50 + 20 x {weight} kg = {charge:.2f} units.")
        if input("Create shipment? (y/n): ").strip().lower() != "y":
            return
        key = "TRK-" + uuid.uuid4().hex[:8].upper()
        item = Shipment(key, customer, package, recipient, address, expected, charge, history=[])
        item.history.append({"status": "CREATED", "time": stamp(), "note": "Shipment created"})
        self.data["shipments"][key] = asdict(item)
        self.save()
        print("Tracking ID:", key)

    def assign(self):
        key = ask("Tracking ID: ")
        shipment = self.data["shipments"].get(key)
        if not shipment or shipment["status"] in ("DELIVERED", "CANCELLED") or shipment["agent_id"]:
            raise ValueError("Shipment not found or cannot be assigned.")
        self.listing("agents")
        agent = ask("Agent ID: ")
        busy = any(s["agent_id"] == agent and s["status"] not in ("DELIVERED", "CANCELLED")
                   for s in self.data["shipments"].values())
        if agent not in self.data["agents"] or busy:
            raise ValueError("Agent not found or already assigned.")
        shipment["agent_id"] = agent
        self.status(shipment, "ASSIGNED", "Agent assigned")
        self.save()
        print("Agent assigned.")

    @staticmethod
    def status(shipment, new_status, note):
        shipment["status"] = new_status
        shipment["history"].append({"status": new_status, "time": stamp(), "note": note})

    def update_status(self):
        shipment = self.data["shipments"].get(ask("Tracking ID: "))
        if not shipment:
            raise ValueError("Shipment not found.")
        current = shipment["status"]
        print("Allowed next status:", ", ".join(NEXT[current]) or "none")
        new = ask("New status: ").upper()
        if new not in NEXT[current]:
            raise ValueError("That status change is not allowed.")
        self.status(shipment, new, input("Note (optional): ").strip() or new)
        self.save()
        print("Status updated.")

    def track(self):
        key = ask("Tracking ID: ")
        s = self.data["shipments"].get(key)
        if not s:
            raise ValueError("Shipment not found.")
        c, p = self.data["customers"].get(s["customer_id"], {}), self.data["packages"].get(s["package_id"], {})
        a = self.data["agents"].get(s["agent_id"], {})
        print(f"{key} | {s['status']} | Customer: {c.get('name', '?')} | Recipient: {s['recipient']}")
        print(f"Address: {s['address']} | Package: {p.get('description', '?')} ({p.get('weight', '?')} kg)")
        print(f"Charge: {s['charge']:.2f} | Expected: {s['expected']} | Agent: {a.get('name', 'Not assigned')}")
        for h in s["history"]:
            print(f"  {h['time']} - {h['status']}: {h['note']}")

    def history(self):
        choice = input("1 all, 2 customer, 3 status, 4 agent: ").strip()
        fields = {"1": None, "2": "customer_id", "3": "status", "4": "agent_id"}
        if choice not in fields:
            raise ValueError("Choose 1, 2, 3, or 4.")
        field = fields[choice]
        value = input("Filter value: ").strip().upper() if field else ""
        found = False
        for key, s in self.data["shipments"].items():
            if field and str(s[field]).upper() != value:
                continue
            print(f"{key} | {s['status']} | {s['expected']}")
            found = True
        if not found:
            print("No matching shipments.")

