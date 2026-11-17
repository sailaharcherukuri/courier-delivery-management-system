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


