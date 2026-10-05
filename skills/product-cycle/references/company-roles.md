# Company roles and workflow responsibilities

Use the installed runtime catalog `product_cycle/resources/team-roles.json` for each agent's identity, department, model mapping, assigned stages and mission. The office reads the same catalog. A position is a separate schedulable agent, not an alias for a shared employee. Each mission gets a fresh recorded session; an available position is not evidence of a running session.

## Ownership across the product cycle

| Workflow work | Responsible agent | Specialist input when relevant | Independent reviewer | Required result |
| --- | --- | --- | --- | --- |
| Product analysis | BA | Product Manager, UX Researcher; Game Designer for games | BA Reviewer | Product requirements, business rules, flows, screen inventory, assumptions and measurable acceptance criteria |
| UI/UX and functional screen design | UI/UX Designer | UX Researcher, Design System Engineer, Frontend; Technical Artist for graphics, Game Designer for games | UX/UI Reviewer | Shared and per-screen specs, interaction/error states, linked screen flow and versioned design images for the agreed scope |
| Technical design | Tech Lead / Solution Architect | Backend, Frontend, Security, DevOps; Mobile, Game Engineer, Data Engineer or AI Engineer according to product needs | Architecture Reviewer | Architecture, data/API contracts, common code conventions, dependencies, service access, risks and verifiable technical choices |
| Project and service preparation | Tech Lead, DEV | DevOps, Backend, Security, Release Engineer | Architecture or Code Reviewer according to the assigned setup task | Git/project foundation, environment, common components, checks and authorized provider setup; unavailable services block only their dependent work |
| Delivery planning | PM | Product Manager, relevant developers, QA Automation | Delivery Plan Reviewer | Traceable tasks, dependencies, selected screen/design references, expected evidence and completion criteria |
| Development | Assigned Web / Server / Mobile / Game engineer, or full-stack DEV | Frontend, Backend; domain engineers and Technical Artist where needed | Code Reviewer | A usable increment with functional logic, assets and visual fidelity to approved per-screen designs |
| Verification | QC / Test Engineer | QA Automation, Accessibility, Security, Performance, relevant domain expert | Test Reviewer | Reproducible results for the current version, real interface comparison, uncovered criteria and concrete defects |
| Local handoff | PM | Release Engineer, Technical Writer, DevOps; Mobile for installable mobile builds | QA Lead / Product Quality Reviewer | Actual local deliverable, install/run instructions, configuration requirements, known limitations and whole-product evidence |
| Retrospective | PM | Product Manager, participating departments | QA Lead for independent evidence assessment | Observed outcomes, causes of defects and actionable changes; do not silently rewrite the framework from an individual product run |

The catalog contains 31 software-product positions including department reviewers. It does not mean 31 sessions must run for every task. Core roles own the work; Web, Server, Mobile and Game engineers are distinct implementation workers as well as available specialists. Assign a build task to its specific worker with project configuration `team.task_agents` (task ID to agent ID); `team.build_agent` selects the project default, and `build` remains the full-stack fallback. Assignments do not give write permission to consultations or reviewers. Consultants run separate read-only missions with narrow questions and actual artifacts. Optional specialists must explain why they are relevant. Game Designer uses the project's game-team setting. Other domain consultants remain available for an explicit relevant consultation; their availability alone must not trigger extra infrastructure or broaden product scope.

## Delegation and exchange

Keep the manager/controller pattern: the controller validates dependency readiness and authoritative state; PM prioritizes and coordinates within that registry. Send bounded questions through the authenticated peer tools, referencing the task, screen ID, artifact/version and decision needed. Structured consultation output contains a summary, findings, limitations and a blocker if one exists. The primary worker integrates useful findings into its actual outputs and identifies unresolved limitations; received advice is not accepted evidence by itself.

Reviewers use fresh read-only context with accepted requirements, actual artifacts, current code and applicable evidence. They do not receive the worker's peer persuasion as an approval or inherit its conversation. Their report must identify concrete inconsistencies and omissions with evidence and severity; merely confirming that files exist is insufficient. Keep specialist advice separate from department acceptance review. Human approval remains at the configured gates.

Model and effort map to the project's maintained model configuration for the assigned role. Do not invent unavailable models, claim that a bigger model guarantees quality, or silently equate requested configuration with observed runtime settings. Preserve the session limit and one-source-writer rule; parallelize independent investigation and consultation rather than simultaneous edits to shared source.

## Evidence and improvement loop

Record actual session/thread identity, task revision, attempt, requested and observed model settings, real usage, tool/progress events, messages, outputs and independent review. Track delivery and acknowledgement separately. Unknown usage stays unknown. Keep model-capacity retries distinct from product rework; reconcile interrupted sessions before dispatching duplicate work.

Use synthetic controller cases to evaluate routing, dependency/gate preservation, writer exclusion, reviewer isolation, message authenticity, retry recovery and usage deduplication. These checks do not establish real product quality or provider connectivity. For real product quality, evaluate the agreed experience and visuals against actual current outputs, record failures, repair the affected scope and re-review. Do not run a live product merely to validate controller changes.

## Official grounding

This company catalog and department structure are Product-Cycle conventions. The underlying techniques follow official guidance:

- [OpenAI orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration): bounded specialists behind a manager, or explicit ownership handoff when appropriate.
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents): focused parallel work with separate context and configurable roles.
- [Evaluating agent workflows](https://developers.openai.com/api/docs/guides/agent-evals): inspect actual traces and evaluate observable outcomes.

The runtime uses the existing Codex connector and deterministic controller. It does not require adding Agents SDK just to imitate its orchestration pattern.
