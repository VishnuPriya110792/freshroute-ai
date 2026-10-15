# FreshRoute AI — implementation plan

## Scope and decisions

Implement the complete MVP from the supplied FreshRoute AI specification. Preserve its React/TypeScript/Vite/Tailwind/Recharts/Lucide frontend and Python/FastAPI/Pydantic backend; use SciPy linear programming for the allocation objective. Keep the example dataset deterministic and synthetic. No paid/live APIs, auth, database, or LLM-based planning are needed. Browser-held working data is sufficient for this single-user MVP; CSV is the import/export boundary.

The planning horizon is one dispatch window. Each destination has one aggregate route capacity in kilograms shared across all commodities for that destination during the horizon; it is not a per-trip capacity. Route cost is INR/kg. Arrival time is travel hours plus destination handling hours. A batch-destination assignment is feasible only when the destination is eligible for that batch and arrival time is no greater than its estimated remaining usable shelf life. Demand is per commodity and destination.

The optimizer creates nonnegative kg allocation variables only for feasible batch-destination pairs and maximizes total expected net contribution: sum of allocated kg × (destination selling price INR/kg − route cost INR/kg). It is a continuous LP, not a vehicle-routing or integer-trip solver. Inventory, commodity-market demand, and route-wide capacity form upper-bound constraints. Stable sorted inputs and solver variable order make repeated runs deterministic. The baseline processes batches by ascending usable shelf life then batch ID (FEFO), allocating each batch to feasible routes by descending net contribution/kg then destination ID while respecting the same remaining inventory, demand, and route capacities. Both strategies are evaluated with the same evaluator and economic inputs.

Evaluation reports delivered and unallocated kg, demand fulfillment, gross sales, route costs and net revenue. Unallocated kg means unsold at the modeled planning cutoff, not physically spoiled. Physical spoilage is not asserted without expiry observations. At-risk kg is residual inventory with at most 24 estimated usable hours at dispatch, kept distinct from rejected-by-shelf-life stock. Discounts are deterministic rule-based price scenarios only: show price reduction and the revenue trade-off if the same residual volume sold at that lower price; do not model demand response or claim increased sales.

## Architecture and project structure

- `backend/app/main.py`: FastAPI app, HTTP routes, CORS/static serving, startup health.
- `backend/app/models.py`: Pydantic input/output schemas and validation.
- `backend/app/data.py`: deterministic illustrative Indian produce sample and CSV schemas.
- `backend/app/planner.py`: feasible-edge generation, SciPy LP optimizer, FEFO baseline, traceable allocation explanations and diagnostics.
- `backend/app/evaluation.py`: single source of truth for strategy metrics, comparison deltas, and per-destination demand/allocation chart summaries.
- `backend/app/scenarios.py`: copy-based travel/demand/capacity perturbations and change summaries.
- `backend/app/discounts.py`: transparent rule-based residual-risk recommendations.
- `backend/app/reports.py`: backend-generated allocation/comparison CSV and print-ready HTML report.
- `frontend/src/`: React app shell, overview, inventory/market editors, plan/comparison/scenario/report views, API client, shared types and styles.
- `frontend/public/manus-routes.json`: complete static route manifest (the MVP is a single `/` route).
- `tests/`: Pytest tests of optimizer, baseline, metrics, validation, scenarios, exports and deterministic evaluation cases.
- `scripts/evaluate_scenarios.py`: reproducible normal, short-life, demand-spike, travel-delay, reduced-capacity, and low-margin/FEFO-competitive evaluation output.
- `README.md`: setup, API, schemas, equations, assumptions, limitations, deployment and three-minute demo.

The built Vite assets will be served by FastAPI from the same listener for Preview/deployment; `/api/*` remains real FastAPI behavior, while `/` serves the dashboard. Backend responses are the only source for core metric totals and chart aggregates; input-shelf-life visualization uses the submitted estimates directly. The Vite development workflow remains available for frontend work. Use pinned dependencies, no secrets, and no external runtime data dependency. Any unresolved solver infeasibility is returned as a structured result; the LP includes the zero-allocation feasible solution unless input structure is invalid.

## Design direction

Reuse the user-specified premium agricultural operations SaaS direction rather than introducing a competing visual style.

- **Design movement:** contemporary agrarian editorial design with restrained Swiss-influenced information hierarchy.
- **Core principles:** operational clarity first; calm, high-contrast surfaces; quantified risks with definitions; visible provenance for synthetic assumptions.
- **Color philosophy:** deep forest green anchors dispatch actions, warm ivory reduces glare across dense operational views, charcoal supports legibility, muted green signals favorable results, amber marks attention, and red is reserved for actual critical risks/errors. Signature brand green: `#174C3C`.
- **Layout paradigm:** compact persistent navigation and a wide, left-aligned operational workspace; tables and charts use purposeful split panels rather than a centered marketing grid.
- **Signature elements:** route/leaf monogram; slim risk bars keyed to shelf-life bands; understated numeric “dispatch ledger” treatments.
- **Interaction philosophy:** edits are explicit and validated; the primary plan action is always easy to find; scenario controls show units and apply only after simulation; errors explain recovery.
- **Animation:** brief 120–180 ms color/opacity transitions for hover and selection; no looping motion; honor reduced-motion preferences.
- **Typography system:** Inter/system sans for interface and headings, tabular numerals via system monospace for IDs/metrics; restrained weight contrast over decorative type.
- **Brand essence:** decision support for produce dispatch teams that connects shelf life, demand, transport and margin in one explainable plan; precise, grounded, practical.
- **Brand voice:** concise and operational, with explicit units and careful estimates. Examples: “Ready for dispatch planning.” “At risk means unallocated stock with ≤24 estimated hours remaining.”
- **Wordmark & logo:** custom leaf-and-route-line mark paired with a compact FreshRoute wordmark; implemented as a simple vector, not an emoji.

## Delivery approach

Build and test the algorithm/evaluator first, then wire Pydantic/FastAPI APIs, then the responsive React workspace and functional CSV/report exports. Run the deterministic evaluation script, Pytest suite, frontend production build, route-manifest check, and real API workflow. Document exact local startup commands and only report outcomes actually observed. Keep the project usable with its bundled sample and without credentials.
