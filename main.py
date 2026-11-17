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

