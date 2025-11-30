**Project Title (as assigned):** FastAPI Inventory Reservation Service (Optimistic & Pessimistic)  
**Project Type:** Application Developer  
**Stack / Framework:** FastAPI, SQLAlchemy, asyncio locks, uvicorn, pytest

**1\. Problem Understanding**

**1.1 What is the problem statement in your own words?**  
To build a highly concurrent and reliable inventory reservation service that can protect stock across multiple SKUs. The service must handle temporary holds with strict expiry policies, convert these holds to final allocations, and safely release stock. A critical requirement is implementing robust, multi-strategy (optimistic vs. pessimistic) inventory math to prevent oversells and ensure atomicity, especially during high-demand events like flash sales.

**1.2 Why does this problem exist or matter?**  
This problem exists in e-commerce and ticketing systems where available stock is a shared, time-sensitive resource. Inaccurate or slow inventory calculations lead to overselling (damaging customer trust) or underselling (losing revenue).

* **Who benefits from the solution:**  
  * **User/Customer:** Benefits from reliable stock reservation and a fair chance at purchasing during high-demand events.  
  * **Developer/Company:** Benefits from robust, scalable retail/ticketing stock protection, idempotent operations, and tools for consistency checking and reconciliation.

**1.3 Key inputs and expected outputs:**

| Inputs | Process | Expected Outputs |
| ----- | ----- | ----- |
| Client tokens (for idempotency), SKU IDs, quantities, hold/allocation/release requests. | Inventory math and race control; holds/allocations/expiries; idempotent tokens; batch atomicity; conflict detection; audit logs and reconciliation. | Reservation API, consistency check tools, flash-sale fairness report, Waitlist notifications. |

**2\. Functional Scope**

**2.1 What are the core features you plan to build (must-haves)?**

1. Provide core REST endpoints for creating, converting, and releasing inventory *holds* with an expiry mechanism.  
2. Implement inventory math and race control using both **optimistic** and **pessimistic** reservation strategies.  
3. Ensure all operations are **idempotent** using client tokens to prevent duplicate transactions.  
4. Support **batch holds** across multiple SKUs with all-or-nothing (atomic) semantics.  
5. Track and expose **availability snapshots** and a dedicated consistency check endpoint.

**2.2 What stretch goals could you attempt if time permits?**

1. Implement a Waitlist mechanism that notifies users when a held-out-of-stock item returns to availability.  
2. Develop a dedicated module to persist detailed audit logs and reconciliation tools.  
3. Generate a "flash-sale report" that includes fairness metrics under burst loads.

**2.3 Which libraries or tools will you use?**

* **Framework:** FastAPI (for API development and asynchronous operations).  
* **Database/ORM:** SQLAlchemy (for database modeling, transaction management, and connection pooling).  
* **Concurrency:** `asyncio` locks or database-level mechanisms (for pessimistic strategy and race control).  
* **Testing:** `pytest` (for unit and integration testing).  
* **Server:** `uvicorn`.

**3\. System & Design Thinking**

**3.1 Sketch or describe your app flow / pipeline:**

1. **Input (Client Request):** Receive a Hold/Allocate/Release request with SKU, Quantity, and Client Token.  
2. **Processing (Idempotency & Conflict Check):** Check for existing operations using the Client Token. Verify current inventory state (Availability Snapshot). If a hold/allocation, check for oversell conflict.  
3. **Processing (Strategy Logic):** Apply Optimistic (e.g., version checking) or Pessimistic (e.g., explicit locking via `asyncio` or DB) strategy based on the request type/flag.  
4. **Processing (Inventory Math):** Update inventory totals, holds, and allocations. Ensure "No negative inventory" invariant is maintained.  
5. **Output (Response & Side Effects):** Return Success/Conflict/Expired status. Trigger expiry cron/task (side effect) and persist Audit Log (side effect).

**3.2 What data structures or algorithms are central to this project?**

* **Data Structures:** Database tables for **SKUs**, **Reservations** (Holds/Allocations), **Client Tokens** (for idempotency), and **Availability Snapshots**.  
* **Algorithms:** Transaction Management (ACID properties for inventory math), Hashing (for fast Client Token lookup), Explicit Locking/Mutexes (`asyncio` locks) or Database Versioning (Optimistic Locking).

**3.3 How will you test correctness or performance?**

* **Correctness:** Extensive unit tests (`pytest`) to cover all inventory flows (hold, allocate, release, expiry). Verification of the Consistency Check endpoint. Test cases to ensure "No negative inventory" and correct expiry behavior.  
* **Performance:** Stress testing/Load simulation (e.g., flash-sale simulation) to measure system performance and fairness metrics under burst loads.

I have generated the database schema and design notes based on your input. You can add the following section, perhaps as a new Section 3.4 or as an expansion of Section 3.2, in your document.-----

**3.4 Database Schema (Normalized)**

The following tables represent the normalized schema designed to support the core functional requirements, including multi-strategy concurrency control (optimistic/pessimistic), idempotency, batch atomicity, expiry, and comprehensive auditing/reconciliation.

**Key Tables and Purpose**

| Table Name | Purpose |
| ----- | ----- |
| **`skus`** | Product/stock-keeping units metadata. |
| **`inventory`** | Canonical current inventory per SKU (total, reserved, allocated, version). **Central table for all inventory math.** |
| **`reservations`** | Header for a reservation (hold or allocation). Enforces **idempotency** via a unique `client_token`. |
| **`reservation_items`** | Line items for a reservation, linking multiple SKUs to a single reservation for **batch atomicity**. |
| **`idempotency_tokens`** | (Alternate) Client tokens to enforce idempotency and track results. |
| **`inventory_snapshots`** | Periodic snapshots for reporting and high-level **consistency checks**. |
| **`audit_logs`** | Append-only record of all inventory-changing operations for full **traceability**. |
| **`reconciliation_runs`** | Records of background reconciliation jobs and their outcomes. |
| **`waitlist_entries`** | (Optional Stretch) Notifies users when a held-out-of-stock item returns to availability. |
| **`pessimistic_locks`** | (Optional) Explicit database-managed lock records for the **pessimistic strategy**. |

**SQL `CREATE TABLE` Statements (Postgres-flavored)**

\-- 1\. SKUs

CREATE TABLE skus (

    sku\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    sku\_code TEXT NOT NULL UNIQUE, \-- human/partner code

    name TEXT NOT NULL,

    description TEXT,

    attributes JSONB, \-- optional: size/color/etc

    created\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    updated\_at TIMESTAMPTZ NOT NULL DEFAULT now()

);

\-- 2\. Inventory (canonical single-row per SKU)

CREATE TABLE inventory (

    sku\_id UUID PRIMARY KEY REFERENCES skus(sku\_id) ON DELETE CASCADE,

    total\_qty BIGINT NOT NULL CHECK (total\_qty \>= 0), \-- total physical stock

    reserved\_qty BIGINT NOT NULL DEFAULT 0 CHECK (reserved\_qty \>= 0),

    allocated\_qty BIGINT NOT NULL DEFAULT 0 CHECK (allocated\_qty \>= 0),

    available\_qty BIGINT NOT NULL GENERATED ALWAYS AS (total\_qty \- reserved\_qty \- allocated\_qty) STORED CHECK (available\_qty \>= 0),

    version BIGINT NOT NULL DEFAULT 1, \-- optimistic locking/version

    updated\_at TIMESTAMPTZ NOT NULL DEFAULT now()

);

CREATE INDEX ix\_inventory\_available ON inventory (available\_qty);

\-- 3\. Reservations (holds or final allocations) \- idempotent by client\_token

CREATE TYPE reservation\_status AS ENUM ('PENDING','HELD','ALLOCATED','RELEASED','EXPIRED','FAILED','CANCELLED');

CREATE TABLE reservations (

    reservation\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    client\_token TEXT NOT NULL, \-- idempotency token (client-supplied)

    user\_id UUID, \-- optional customer identifier

    status reservation\_status NOT NULL DEFAULT 'PENDING',

    type TEXT NOT NULL CHECK (type IN ('HOLD','ALLOCATE')), \-- intent

    total\_items INT NOT NULL CHECK (total\_items \> 0),

    requested\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    expires\_at TIMESTAMPTZ, \-- only for holds

    completed\_at TIMESTAMPTZ,

    error TEXT,

    metadata JSONB,

    created\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    updated\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (client\_token) \-- ensures idempotency

);

CREATE INDEX ix\_reservations\_status ON reservations (status);

CREATE INDEX ix\_reservations\_expires\_at ON reservations (expires\_at);

\-- 4\. Reservation items (supports batch atomicity)

CREATE TABLE reservation\_items (

    reservation\_item\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    reservation\_id UUID NOT NULL REFERENCES reservations(reservation\_id) ON DELETE CASCADE,

    sku\_id UUID NOT NULL REFERENCES skus(sku\_id) ON DELETE RESTRICT,

    qty BIGINT NOT NULL CHECK (qty \> 0),

    unit\_price NUMERIC(18,4),

    created\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (reservation\_id, sku\_id) \-- per reservation, a SKU appears once

);

CREATE INDEX ix\_res\_items\_reservation ON reservation\_items (reservation\_id);

CREATE INDEX ix\_res\_items\_sku ON reservation\_items (sku\_id);

\-- 5\. Idempotency tokens (alternate approach)

CREATE TABLE idempotency\_tokens (

    token TEXT PRIMARY KEY,

    reservation\_id UUID REFERENCES reservations(reservation\_id),

    status TEXT NOT NULL,

    created\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    expires\_at TIMESTAMPTZ

);

\-- 6\. Inventory snapshots (for reporting / consistency checks)

CREATE TABLE inventory\_snapshots (

    snapshot\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    sku\_id UUID NOT NULL REFERENCES skus(sku\_id),

    snapshot\_time TIMESTAMPTZ NOT NULL DEFAULT now(),

    total\_qty BIGINT NOT NULL,

    reserved\_qty BIGINT NOT NULL,

    allocated\_qty BIGINT NOT NULL,

    available\_qty BIGINT NOT NULL,

    metadata JSONB

);

CREATE INDEX ix\_snapshots\_time ON inventory\_snapshots (snapshot\_time);

\-- 7\. Audit logs (append-only)

CREATE TABLE audit\_logs (

    audit\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    reservation\_id UUID REFERENCES reservations(reservation\_id),

    sku\_id UUID REFERENCES skus(sku\_id),

    operation TEXT NOT NULL CHECK (operation IN ('HOLD\_CREATED','HOLD\_RELEASED','ALLOCATED','RELEASED','EXPIRED','INVENTORY\_ADJUST','MANUAL\_ADJUST')),

    delta BIGINT, \-- positive or negative change to reserved/allocated/total as applicable

    prev\_total\_qty BIGINT,

    new\_total\_qty BIGINT,

    prev\_reserved\_qty BIGINT,

    new\_reserved\_qty BIGINT,

    prev\_allocated\_qty BIGINT,

    new\_allocated\_qty BIGINT,

    actor TEXT, \-- service, worker, user id, etc.

    created\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    metadata JSONB

);

CREATE INDEX ix\_audit\_by\_reservation ON audit\_logs (reservation\_id);

CREATE INDEX ix\_audit\_by\_sku ON audit\_logs (sku\_id);

\-- 8\. Reconciliation runs

CREATE TABLE reconciliation\_runs (

    run\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    started\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    finished\_at TIMESTAMPTZ,

    status TEXT NOT NULL CHECK (status IN ('RUNNING','OK','ISSUES','FAILED')),

    summary JSONB,

    created\_by TEXT

);

\-- 9\. Optional: Waitlist entries

CREATE TABLE waitlist\_entries (

    entry\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    sku\_id UUID NOT NULL REFERENCES skus(sku\_id),

    user\_id UUID,

    desired\_qty BIGINT NOT NULL CHECK (desired\_qty \> 0),

    created\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    notified\_at TIMESTAMPTZ,

    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','NOTIFIED','CANCELLED'))

);

CREATE INDEX ix\_waitlist\_sku ON waitlist\_entries (sku\_id);

\-- 10\. Optional: Pessimistic locks table

CREATE TABLE pessimistic\_locks (

    lock\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    sku\_id UUID NOT NULL REFERENCES skus(sku\_id),

    reservation\_id UUID,

    locked\_by TEXT, \-- worker id or request id

    lock\_acquired\_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    lock\_expires\_at TIMESTAMPTZ,

    UNIQUE (sku\_id) \-- one lock per SKU

);

CREATE INDEX ix\_locks\_sku ON pessimistic\_locks (sku\_id);

**Constraints, Transactions, and Enforcement Notes (Concise)**

* **Batch Atomicity:** Use transactions that modify `inventory` \+ `reservation_items` \+ `reservations` in a single DB transaction.  
* **Optimistic Concurrency:**  
  * Read `inventory.version`.  
  * Apply `UPDATE inventory SET reserved_qty = reserved_qty + X, version = version + 1 WHERE sku_id = ? AND version = <old_version>`.  
  * Check `rows_affected = 1`. Rollback and retry on mismatch.  
* **Pessimistic Concurrency:** Acquire an application-level lock (e.g., `FOR UPDATE` on the `inventory` row within the same transaction or use the `pessimistic_locks` table/advisory locks) before modifying counts.  
* **Safety:** Never rely on `available_qty` client-side; compute within the DB transaction and enforce `available_qty >= 0` via explicit checks and application logic.  
* **Expiry:** A background worker must scan reservations where `status='HELD' AND expires_at <= now()` and atomically transition to `EXPIRED`, decrementing `reserved_qty` in `inventory` with corresponding `audit_logs`.

**Normalization Justification (3NF)**

* **`skus`** holds SKU attributes (no repeating groups).  
* **`inventory`** is one canonical row per `sku_id` (no derived repeating sets).  
* **`reservations`** separates the header from **`reservation_items`** (1-to-many) for batch atomicity.  
* **`audit_logs`** are append-only facts for traceability; no redundant storage of reservation details beyond references.  
* **Idempotency** is enforced via the `UNIQUE (client_token)` constraint on the `reservations` table (or alternatively, stored in a separate `idempotency_tokens` table).

**4\. Timeline & Milestones (4 Weeks)**

| Week | Planned Deliverables | Mentor Checkpoint |
| ----- | ----- | ----- |
| W1 | Model design (SKU, Reservation, Idempotency tables) \+ Basic Hold and Release flows. | ☐ |
| W2 | Hold Expiries implementation \+ Conversion to Allocations \+ Conflict detection for oversells. | ☐ |
| W3 | Implement Batch Atomicity \+ Fairness under burst simulation \+ Availability Snapshots tracking. | ☐ |
| W4 | Develop Consistency Check endpoint and reconciliation tools \+ Final documentation and project demos. | ☐ |

**5\. Risks & Dependencies**

**5.1 What’s the hardest part technically for you right now?**  
Inventory math and race control, particularly ensuring the correctness of the optimistic and pessimistic strategies under high concurrency and implementing atomic batch operations.

**5.2 What dependencies or help do you need from mentors?**  
Guidance or code review on the implementation of `asyncio` locks/database transactions for race control, and feedback on the proposed fairness metrics for the flash-sale simulation.

**6\. Evaluation Readiness**

**6.1 How will you prove that your project “works”?**

* Deployment links and Git links.  
* Test cases demonstrating: successful hold/allocate/release flows, no negative inventory, correct expiry functionality, and successful idempotent request handling.  
* Metrics table from the flash-sale simulation showing fairness under burst loads.

**6.2 What success metric or goal will you aim for?**

* 100% functional CRUD for holds, allocations, and releases.  
* Guaranteed **No negative inventory** and **Correct expiry behavior**.  
* **Consistency Check Endpoint** returns OK across all inventory records after reconciliation runs.

**Signatures (Students):**  
**Mentor Approval:**  
**Date:**  
