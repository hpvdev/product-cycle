# Operating the packaged controller

Run commands from the Product-Cycle repository, or use `product-cycle` after local installation. Replace example paths with the user's selected project.

1. Create a brief with desired outcome, users, scope, constraints, and known unknowns.
2. `python3 -m product_cycle init --project /absolute/project --brief /absolute/brief.md --name "Product name"`
3. `python3 -m product_cycle serve --project /absolute/project`
4. `python3 -m product_cycle run --project /absolute/project`

`run` advances ready tasks sequentially, with a separate read-only review session. It stops at a product-owner decision, a blocker, a budget limit, or no ready work. Default human gates: analysis, plan, handoff. Respect authorization already supplied when recording decisions; never invent it.

`decide --project ... --task analysis --action approve --actor "Owner" --note "Specific accepted scope"` records a decision tied to the reviewed revision. `reject` returns it for rework. `reopen --task ... --note ...` starts a revision and invalidates dependents without deleting evidence.

`pause` takes effect at task boundaries. `resume` lifts that pause; use `run` to continue. After a controller crash, `recover` marks unfinished work blocked. Inspect actual changes, then use `reopen` before repeating work. Publication, merge, deployment, account changes, and messages require separate authorization; this controller does not perform them.

Codex must be installed and authenticated. `doctor` reports availability without secrets. Browser/MCP capabilities from desktop are not assumed to exist in app-server. If browser acceptance is needed and unavailable, the operator records real observations with `browser-evidence`, then invokes `review`. `judge` sends explicitly supplied non-sensitive text to Jev for a semantic opinion.

`package --output /outside/project/delivery` exports source, evidence, decisions, and full history after all stages are accepted. It skips .env files and symlinks, listing omissions in the manifest. It does not deploy; handoff.md explains setup and product version.
