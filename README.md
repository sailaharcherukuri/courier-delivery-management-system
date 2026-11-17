# Courier and Delivery Management System

A beginner-friendly Python console application for managing customers, packages, delivery agents, shipments, tracking, and delivery history. It uses only Python's standard library.

## Assumptions and rules

- The sample classroom shipping rate is **50 currency units + 20 currency units per kilogram**. The amount is rounded to two decimals and is not a real courier quote.
- Expected delivery dates use `YYYY-MM-DD`.
- Status flow: `CREATED` can become `ASSIGNED` through agent assignment or `CANCELLED`; `ASSIGNED` can become `IN_TRANSIT` or `CANCELLED`; `IN_TRANSIT` can become `OUT_FOR_DELIVERY` or `CANCELLED`; `OUT_FOR_DELIVERY` can become `DELIVERED` or `CANCELLED`. Delivered and cancelled shipments are terminal.
- An agent is occupied while assigned to a shipment that is not delivered or cancelled. The application recalculates availability from shipment records at startup.
- Record IDs are unique within their own category. Tracking IDs are generated automatically.

## Project files

```text
Courier and Delivery Management System/
├── main.py
├── README.md
└── data/                    # created on first run
    ├── customers.txt
    ├── packages.txt
    ├── agents.txt
    └── shipments.txt
```

Each `.txt` data file contains a human-readable JSON object keyed by record ID. This safely stores commas, line breaks, and other characters in addresses and names. If a file is missing, it is initialized as an empty object. If a file contains invalid JSON, the app preserves it and opens in read-only mode until the file is repaired; it will not overwrite that file.

## Requirements and run instructions

Use Python **3.10 or newer**. Open a terminal in this project folder and run:

```text
python main.py
```

On systems where Python is invoked as `python3`:

```text
python3 main.py
```

These commands work in Windows PowerShell or Command Prompt, macOS Terminal, and Linux terminals when Python is on the PATH.

## Normal workflow

1. Add a customer (menu option 1).
2. Register a package (option 3).
3. Add one or more delivery agents (option 5).
4. Create a shipment (option 7), selecting the customer and package, entering recipient details and expected delivery date, and confirming the displayed charge.
5. Assign an available agent (option 8).
6. Update the shipment as it moves through delivery (option 9).
7. Track a shipment by its generated tracking ID (option 10), or view filtered delivery history (option 11).

Changes are written as actions complete. Restarting the program loads the same records.

## Course concepts in the code

- **Classes and objects:** `Customer`, `Package`, `Agent`, and `Shipment` model records.
- **Inheritance:** `Customer` and `Agent` inherit shared contact fields from `Person`.
- **Dictionaries:** customer, package, agent, and shipment collections are keyed by IDs for lookup.
- **Functions and methods:** validation, charge calculation, persistence, tracking, and workflow actions are separated into named methods.
- **Conditional logic:** menu choices, input checks, availability, and status transitions use conditions.
- **Exception handling:** invalid input, dates, unknown IDs, and file errors are caught and reported.
- **Basic modules:** the app uses standard-library modules including `dataclasses`, `datetime`, `json`, `pathlib`, and `uuid`.
- **TXT file handling:** JSON text is loaded from and saved to the `.txt` files under `data/`.

## Manual verification checklist

- Add a customer, package, and agent; confirm they appear in their list views.
- Try a duplicate customer/package/agent ID; the app should reject it.
- Enter zero, a negative value, or nonnumeric text for weight; the app should reject it.
- Enter an invalid calendar date or a date in a different format; shipment creation should reject it.
- Create a shipment and confirm the sample charge and generated tracking ID.
- Assign an agent; try assigning that same agent to another active shipment and confirm it is rejected.
- Update through the allowed status flow; try skipping a step or changing a terminal shipment and confirm it is rejected.
- Track an unknown ID and confirm a clear error message.
- Exit and restart; verify records and shipment status history remain available.
- For a malformed-file recovery check, make a backup before editing a `.txt` data file into invalid JSON. Restart and confirm the file is preserved and changes are disabled until it is repaired.
