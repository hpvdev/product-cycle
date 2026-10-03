# Stage contracts

Role guidance ships in `product_cycle/resources/roles/`. Load only the assigned role. File names are package conventions, not universal OpenAI requirements.

| Stage | Required output | Review focus |
|---|---|---|
| analysis | analysis.md, requirements.json | Outcome, facts/assumptions, scope, testable acceptance |
| design | design.md, design-baseline.json and visual artifact for UI | Journeys, states, design rules, visual target, requirement coverage, accessibility |
| architecture | architecture.md; services.json for new local cycles | Data, boundaries, decisions, verification and recovery |
| plan | plan.json | Coverage, acyclic tasks, local checks, runtime capabilities |
| setup | setup.md, readiness.json per assigned service | Scoped configuration, missing inputs, real connection checks |
| build | Actual product changes | Scope, correctness, checks, criterion links |
| verify | acceptance.md and observed evidence | Coverage, version, actual behavior |
| handoff | handoff.md | Setup, results, limitations, recovery, source location |
| retro | retro.json | Trace-supported findings and evaluable improvements |

Work result: `{summary,artifacts:[{path,purpose,criteria,requirements}],steps:[{id,summary,artifacts}],limitations,blocker}`. Paths are project-relative; criteria use C1, C2, etc. Every S-numbered work step in the context packet needs a concrete summary and paths from artifacts. Required files go in the assigned artifact directory. A non-null blocker cannot be accepted.

Review result: `{decision,summary,criteria:[{id,passed,evidence,reason}],steps:[{id,passed,evidence,reason}],findings}`. Decisions: approve/rework/blocked. Every reported work step must be reviewed against its actual output, with registered evidence IDs. Historical results without steps retain their original contract and show untracked step history. Human observations, controller checks, worker artifacts, and semantic opinions retain separate provenance. AI review does not guarantee product quality.

Design baseline: `{has_ui,visual_reference,flows,states,rules,acceptance}`. UI references must be registered visual artifacts; a description is insufficient. Non-UI products use has_ui=false, visual_reference=null and an explicit interaction contract. New local cycles gate handoff and review every preceding stage independently. Existing cycles keep their configured gates.

Plan tasks: `{id,title,instructions,depends_on,requirements,criteria,checks}`. Task IDs start with T. Checks and verification_commands are argv arrays. browser_required requires real operator browser evidence covering requirements before acceptance; model statements are not browser observations.

New local cycles (service_setup_required=true) require services.json with services:[{id,provider,purpose,environment,inputs,permissions,configuration,verification,checks,owner,cost,fallback}]. Inputs are names/references, never secret values. Design names required services; configuration happens only after plan review.

Plan adds service_ids and a services list per development task (empty if independent), and delivery:{mode:"local",access,instructions,run_commands,deferred}. Controller-generated setup tasks are dependencies only of increments that need that service. VPS and external publication are deferred.

Readiness: {services:[{id,status,note,input_refs}]} for the single assigned service; status is ready/needs_input/configuring/failed. A blocked setup may record valid outputs with result.blocker for the dashboard. It cannot be accepted until the blocker is resolved, planned checks pass and independent review approves.

Project foundation (project_setup_required=true): architecture also produces project-setup.json with stack:{language,runtime,framework,package_manager}, structure, coding_rules, common_components, environment_names, tooling:{format,lint,typecheck,test}, instructions and nonempty checks. Tooling states actual tools or justified omissions. The project_setup task outputs project-setup.md, root CODING_RULES.md, actual configured source/tooling artifacts and .env.example when environment names are required. Controller checks and independent review precede all feature and service setup tasks.
