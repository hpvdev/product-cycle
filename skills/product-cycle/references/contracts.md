# Stage contracts

Role guidance ships in `product_cycle/resources/roles/`. Load only the assigned role. File names are package conventions, not universal OpenAI requirements.

| Stage | Required output | Review focus |
|---|---|---|
| analysis | analysis.md, requirements.json | Outcome, facts/assumptions, scope, testable acceptance |
| design | design.md with shared and per-screen functional specs, design-baseline.json and visual artifact for UI | Business-rule consistency, action behavior, journeys/states, visual target, requirement coverage, accessibility |
| architecture | architecture.md; services.json for new local cycles | Data, boundaries, decisions, verification and recovery |
| feature_map | feature-map.json, feature-map.md for versioned agent cycles | Feature coverage, prerequisite links and observable procedures |
| plan | plan.json | Coverage, acyclic tasks, local checks, runtime capabilities |
| setup | setup.md, readiness.json per assigned service | Scoped configuration, missing inputs, real connection checks |
| build | Actual product changes | Scope, correctness, checks, criterion links |
| integration | integration.md, runtime-observations.json, feature-map-update.json for versioned agent cycles | Exact reviewed changes, canonical checks, runtime proof |
| verify | acceptance.md and observed evidence | Coverage, version, actual behavior |
| handoff | handoff.md | Setup, results, limitations, recovery, source location |
| retro | retro.json | Trace-supported findings and evaluable improvements |

Work result: `{summary,artifacts:[{path,purpose,criteria,requirements}],steps:[{id,summary,artifacts}],limitations,blocker}`. Paths are project-relative; criteria use C1, C2, etc. Every S-numbered work step in the context packet needs a concrete summary and paths from artifacts. Required files go in the assigned artifact directory. A non-null blocker cannot be accepted.

Review result: `{decision,summary,criteria:[{id,passed,evidence,reason}],steps:[{id,passed,evidence,reason}],findings}`. Decisions: approve/rework/blocked. Every reported work step must be reviewed against its actual output, with registered evidence IDs. Historical results without steps retain their original contract and show untracked step history. Human observations, controller checks, worker artifacts, and semantic opinions retain separate provenance. AI review does not guarantee product quality.

Design baseline: `{has_ui,visual_reference,flows,states,rules,acceptance}`. UI references must be registered visual artifacts; a description is insufficient. Non-UI products use has_ui=false, visual_reference=null and an explicit interaction contract. Gate ownership and scope follow context.authority; every stage retains independent review. Existing cycles keep their configured gates.

Plan tasks: `{id,title,instructions,depends_on,requirements,criteria,checks}`. Task IDs start with T. Checks and verification_commands are argv arrays. browser_required requires real operator browser evidence covering requirements before acceptance; model statements are not browser observations.

New local cycles (service_setup_required=true) require services.json with services:[{id,provider,purpose,environment,inputs,permissions,configuration,verification,checks,owner,cost,fallback}]. Inputs are names/references, never secret values. Design names required services; configuration happens only after plan review.

Plan adds service_ids and a services list per development task (empty if independent), and delivery:{mode:"local",access,instructions,run_commands,deferred}. Controller-generated setup tasks are dependencies only of increments that need that service. VPS and external publication are deferred.

Readiness: {services:[{id,status,note,input_refs}]} for the single assigned service; status is ready/needs_input/configuring/failed. A blocked setup may record valid outputs with result.blocker for the dashboard. It cannot be accepted until the blocker is resolved, planned checks pass and independent review approves.

Project foundation (project_setup_required=true): architecture also produces project-setup.json with stack:{language,runtime,framework,package_manager}, structure, coding_rules, common_components, environment_names, tooling:{format,lint,typecheck,test}, instructions and nonempty checks. Tooling states actual tools or justified omissions. The project_setup task outputs project-setup.md, root CODING_RULES.md, actual configured source/tooling artifacts and .env.example when environment names are required. Controller checks and independent review precede all feature and service setup tasks.


Collaborative analysis additionally requires product-direction.json: users, problem, desired_experience, differentiation, options:[{name,description,tradeoffs}], recommendation (one option name), quality_targets:[{description,verification,requirement}], open_questions:[string]. Link each quality target to a requirement. These remain proposals until accepted under the configured policy. In supervised mode, obtain the configured owner decision. In autonomous mode, record delegated assumptions and ask only indispensable questions. Never invent interviews or owner approval.

A plan with experience_checkpoint_required includes experience_checkpoint:{task_id,goal,evaluation:[string]}. The selected task provides a usable core journey, not a disconnected component. Every other development task is either a prerequisite of it or depends transitively on it. The controller assigns the configured checkpoint authority. In supervised mode the owner evaluates the reviewed core; in autonomous mode the delegated company evaluates it before expansion; unrelated service setup can continue. This is a project convention, not a universal OpenAI nine-step standard.

For screen_design_required cycles, read the screen_design_contract path supplied by the controller. Design adds version and screens with stable IDs, states, image references with viewports, transitions and prepared assets. Plan adds screen_targets per task and covers every reference. UI build/verify register screen-comparisons.json and rendered images tied to the exact accepted reference hash and current source. Gate ownership follows context.authority: supervised owner gates require an actual owner decision; delegated autonomous design choices are AI decisions, never human approval. Structural checks and worker comparison claims are separate from independent visual review and functional acceptance.

Within each screen, references must have unique state/viewport pairs and cover every declared state, but multiple entries may share the same image when only numbers, text, messages or button states change. Create separate images only for materially different layouts or presentation; no fixed image count is required. A selected Image Gen image can directly be the canonical baseline; Figma and browser captures are optional. Record target viewports, responsive rules, state differences and minor image corrections in design.md. Exact image pixel dimensions or aspect ratio are not absolute acceptance conditions. The image guides appearance and the specification determines exact labels, symbols, behavior and layout rules; build/verify evaluates them together.

For agent_workflow_version=1, architecture supplies verification.json and the reviewed feature_map stage precedes plan. Each development task declares features from feature-map.json. Read context.verification_contract_path for product-specific launch, doctor, drive, evidence and cleanup. Builder/reviewer/repair packs retain exact authority, criteria and sealed provenance. Feature completion distinguishes workspace verification, integration and current-product verification. Whole-product verify and handoff retain the configured gates and actual source version. Legacy cycles keep their recorded contract until an explicit idle upgrade.
