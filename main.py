"""Console courier manager. Records are JSON stored in .txt files."""

from dataclasses import asdict, dataclass
from datetime import date, datetime
import copy
import json
import math
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
        loaded = {}
        errors = []
        for key, filename in FILES.items():
            path = FOLDER / filename
            try:
                if not path.exists():
                    path.write_text("{}\n", encoding="utf-8")
                value = json.loads(path.read_text(encoding="utf-8") or "{}")
                if not isinstance(value, dict):
                    raise ValueError("top-level JSON value must be an object")
                loaded[key] = value
            except (OSError, ValueError) as error:
                errors.append((filename, "<file>", str(error)))

        if len(loaded) == len(FILES):
            errors.extend(self.validate_records(loaded))
        self.read_only = bool(errors)
        self.data = loaded if not errors else {key: {} for key in FILES}
        for filename, record_id, reason in errors:
            print(f"Invalid data in {filename}, record {record_id}: {reason}. File preserved.")
        if errors:
            print("The application is read-only until the data is repaired.")

    @staticmethod
    def validate_records(data):
        errors = []

        def invalid(kind, record_id, reason):
            errors.append((FILES[kind], record_id, reason))

        def text_fields(record, fields):
            return all(isinstance(record.get(field), str) and record[field].strip() for field in fields)

        for kind in ("customers", "agents", "packages", "shipments"):
            for record_id, record in data[kind].items():
                if not isinstance(record_id, str) or not record_id.strip() or not isinstance(record, dict):
                    invalid(kind, record_id, "record ID and value must be valid")
                    continue
                if record.get("id") != record_id:
                    invalid(kind, record_id, "record id field does not match its dictionary key")
                    continue
                if kind == "customers":
                    if not text_fields(record, ("name", "phone", "address")):
                        invalid(kind, record_id, "name, phone, and address are required")
                elif kind == "agents":
                    if not text_fields(record, ("name", "phone")) or not isinstance(record.get("available"), bool):
                        invalid(kind, record_id, "name, phone, and a boolean available field are required")
                elif kind == "packages":
                    weight = record.get("weight")
                    try:
                        valid_weight = (isinstance(weight, (int, float)) and not isinstance(weight, bool)
                                        and math.isfinite(weight) and weight > 0)
                    except (TypeError, OverflowError):
                        valid_weight = False
                    if not text_fields(record, ("description", "kind")) or not valid_weight:
                        invalid(kind, record_id, "description, type, and finite positive weight are required")
                else:
                    required = ("customer_id", "package_id", "recipient", "address", "expected", "status")
                    charge = record.get("charge")
                    try:
                        valid_charge = (isinstance(charge, (int, float)) and not isinstance(charge, bool)
                                        and math.isfinite(charge) and charge >= 0)
                    except (TypeError, OverflowError):
                        valid_charge = False
                    try:
                        valid_date = (isinstance(record.get("expected"), str)
                                      and date.fromisoformat(record["expected"]).isoformat() == record["expected"])
                    except (TypeError, ValueError):
                        valid_date = False
                    history = record.get("history")
                    valid_history = isinstance(history, list) and bool(history)
                    if valid_history:
                        for entry in history:
                            if not isinstance(entry, dict) or not text_fields(entry, ("status", "time")) \
                                    or not isinstance(entry.get("note"), str) \
                                    or entry.get("status") not in NEXT:
                                valid_history = False
                                break
                            try:
                                datetime.fromisoformat(entry["time"])
                            except ValueError:
                                valid_history = False
                                break
                    if (not text_fields(record, required) or not isinstance(record.get("agent_id"), str)
                            or not valid_charge or not valid_date
                            or record.get("status") not in NEXT or not valid_history):
                        invalid(kind, record_id, "required shipment fields, date, finite charge, status, or history are invalid")
                        continue
                    if history[0]["status"] != "CREATED" or history[-1]["status"] != record["status"]:
                        invalid(kind, record_id, "history must start at CREATED and end at the current status")
                        continue
                    if any(after["status"] not in NEXT[before["status"]]
                           for before, after in zip(history, history[1:])):
                        invalid(kind, record_id, "history contains an invalid status transition")

        for record_id, shipment in data["shipments"].items():
            if not isinstance(shipment, dict) or "status" not in shipment:
                continue
            customer_id = shipment.get("customer_id")
            package_id = shipment.get("package_id")
            agent_id = shipment.get("agent_id", "")
            if not all(isinstance(value, str) for value in (customer_id, package_id, agent_id)):
                continue
            if customer_id not in data["customers"]:
                invalid("shipments", record_id, "customer does not exist")
            if package_id not in data["packages"]:
                invalid("shipments", record_id, "package does not exist")
            if agent_id and agent_id not in data["agents"]:
                invalid("shipments", record_id, "assigned agent does not exist")
            if shipment.get("status") in {"ASSIGNED", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"} and not agent_id:
                invalid("shipments", record_id, "this status requires an assigned agent")
        return errors

    def save(self, kind):
        if self.read_only:
            raise ValueError("Repair the malformed data file before changing records.")
        path = FOLDER / FILES[kind]
        temp = path.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(self.data[kind], indent=2, allow_nan=False), encoding="utf-8")
            temp.replace(path)
        except (OSError, TypeError, ValueError):
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def add_record(self, kind, key, record):
        self.data[kind][key] = record
        try:
            self.save(kind)
        except (OSError, TypeError, ValueError):
            self.data[kind].pop(key, None)
            raise

    def save_update(self, kind, key, previous):
        try:
            self.save(kind)
        except (OSError, TypeError, ValueError):
            self.data[kind][key] = previous
            raise

    def add_person(self, kind):
        records = self.data[kind]
        key = ask(f"{kind[:-1].title()} ID: ")
        if key in records:
            raise ValueError("That ID already exists.")
        person = [key, ask("Name: "), ask("Phone: ")]
        record = Customer(*person, ask("Address: ")) if kind == "customers" else Agent(*person)
        self.add_record(kind, key, asdict(record))
        print("Saved.")

    def add_package(self):
        key = ask("Package ID: ")
        if key in self.data["packages"]:
            raise ValueError("That ID already exists.")
        try:
            weight = float(ask("Weight in kg: "))
            if not math.isfinite(weight) or weight <= 0:
                raise ValueError
        except ValueError as error:
            raise ValueError("Weight must be a positive number.") from error
        item = Package(key, ask("Description: "), weight, ask("Type/size: "))
        self.add_record("packages", key, asdict(item))
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
            parsed_date = date.fromisoformat(expected)
            if parsed_date.isoformat() != expected:
                raise ValueError
        except ValueError as error:
            raise ValueError("Use a real date in YYYY-MM-DD format.") from error
        weight = self.data["packages"][package]["weight"]
        charge = 50 + 20 * weight
        if not math.isfinite(charge):
            raise ValueError("The calculated shipping charge is not finite.")
        charge = round(charge, 2)
        if not math.isfinite(charge):
            raise ValueError("The calculated shipping charge is not finite.")
        print(f"Sample charge: 50 + 20 x {weight} kg = {charge:.2f} units.")
        if input("Create shipment? (y/n): ").strip().lower() != "y":
            return
        key = "TRK-" + uuid.uuid4().hex[:8].upper()
        item = Shipment(key, customer, package, recipient, address, parsed_date.isoformat(), charge, history=[])
        item.history.append({"status": "CREATED", "time": stamp(), "note": "Shipment created"})
        self.add_record("shipments", key, asdict(item))
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
        previous = copy.deepcopy(shipment)
        shipment["agent_id"] = agent
        self.status(shipment, "ASSIGNED", "Agent assigned")
        self.save_update("shipments", key, previous)
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
        previous = copy.deepcopy(shipment)
        self.status(shipment, new, input("Note (optional): ").strip() or new)
        self.save_update("shipments", shipment["id"], previous)
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

    def run(self):
        actions = {
            "1": ("Add customer", lambda: self.add_person("customers")),
            "2": ("List customers", lambda: self.listing("customers")),
            "3": ("Register package", self.add_package),
            "4": ("List packages", lambda: self.listing("packages")),
            "5": ("Add agent", lambda: self.add_person("agents")),
            "6": ("List agents", lambda: self.listing("agents")),
            "7": ("Create shipment", self.create_shipment), "8": ("Assign agent", self.assign),
            "9": ("Update status", self.update_status), "10": ("Track shipment", self.track),
            "11": ("Delivery history", self.history),
        }
        while True:
            print("\n=== Courier Manager ===")
            for number, (label, _) in actions.items():
                print(f"{number}. {label}")
            print("0. Exit")
            choice = input("Choose: ").strip()
            if choice == "0":
                return
            if self.read_only:
                print("Data is invalid. Repair the file shown above before using the application.")
                continue
            if choice not in actions:
                print("Choose a listed number.")
                continue
            try:
                actions[choice][1]()
            except (ValueError, OSError) as error:
                print("Error:", error)


if __name__ == "__main__":
    try:
        CourierApp().run()
    except OSError as error:
        print("Could not open data folder:", error)
