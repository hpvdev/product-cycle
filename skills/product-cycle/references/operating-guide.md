# Operating the packaged controller

Run commands from the Product-Cycle repository, or use `product-cycle` after local installation. Replace example paths with the user's selected project.

1. Create a brief with desired outcome, users, scope, constraints, and known unknowns.
2. `python3 -m product_cycle init --project /absolute/project --brief /absolute/brief.md --name "Product name"`
3. `python3 -m product_cycle serve --project /absolute/project`
4. `python3 -m product_cycle run --project /absolute/project`

`run` advances ready tasks sequentially, with a separate read-only review session. It stops at a product-owner decision, a blocker, an explicitly configured budget limit, or no ready work. New local cycles track token usage without a token ceiling; `init --max-turn-tokens N` and `--max-cycle-tokens N` opt into positive limits. In an idle cycle's config.json, `null` disables the corresponding ceiling; existing numeric limits are preserved. Timeouts and retry limits still apply. New local cycles have an owner gate at handoff and independent review at each stage; existing cycles keep their configured gates. Respect authorization already supplied when recording decisions; never invent it.

`decide --project ... --task handoff --action approve --actor "Owner" --note "Accepted verified local product"` records a decision tied to the reviewed revision. `reject` returns it for rework. `reopen --task ... --note ...` starts a revision and invalidates dependents without deleting evidence.

`pause` takes effect at task boundaries. `resume` lifts that pause; use `run` to continue. After a controller crash, `recover` marks unfinished work blocked. Inspect actual changes, then use `reopen` before repeating work. Third-party setup starts after design and plan review, scoped to the selected accounts/project. Missing inputs block dependent increments; independent work can continue. VPS provisioning and external deployment/publication are deferred.

Codex must be installed and authenticated. `doctor` reports availability without secrets. Browser/MCP capabilities from desktop are not assumed to exist in app-server. If browser acceptance is needed and unavailable, the operator records real observations with `browser-evidence`, then invokes `review`. `judge` sends explicitly supplied non-sensitive text to Jev for a semantic opinion.

`package --output /outside/project/delivery` exports source, evidence, decisions, and full history after all stages are accepted. It skips .env files and symlinks, listing omissions in the manifest. It does not deploy; handoff.md explains setup and product version.

`init` prepares Git, .gitignore, AGENTS.md, PRODUCT_CYCLE_RULES.md and the bundled skills without replacing existing user instructions or publishing. Inside Development, architecture and plan precede the preparatory project_setup task, which creates CODING_RULES.md, source/tooling foundations and local checks before features. Use `doctor --project ...` for project readiness and `bootstrap --project ...` to adopt missing or explicitly reviewed common-rule changes in an idle old cycle. The pip-installed CLI also offers `install-skills`.
