# Company roles and workflow responsibilities

Use the installed runtime catalog `product_cycle/resources/team-roles.json` for each agent's identity, department, model mapping, assigned stages and mission. The office reads the same catalog. A position is a separate schedulable agent, not an alias for a shared employee. Each mission gets a fresh recorded session; an available position is not evidence of a running session.

## Ownership across the product cycle

| Workflow work | Responsible agent | Specialist input when relevant | Independent reviewer | Required result |
| --- | --- | --- | --- | --- |
| Product analysis | BA | Product Manager, UX Researcher; Game Designer for games | BA Reviewer | Product requirements, business rules, flows, screen inventory, assumptions and measurable acceptance criteria |
| UI/UX and functional screen design | UI/UX Designer, with Design Director accountable for the experience decision | Art Director, UX Researcher, Design System Engineer, Frontend; Technical Artist for graphics, Game Designer for games | UX/UI Reviewer | Shared and per-screen specs, interaction/error states, linked screen flow, real asset inventory and versioned design images for the agreed scope |
| Technical design | Tech Lead / Solution Architect | Backend, Frontend, Security, DevOps; Mobile, Game Engineer, Data Engineer or AI Engineer according to product needs | Architecture Reviewer | Architecture, data/API contracts, common code conventions, dependencies, service access, risks and verifiable technical choices |
| Project and service preparation | Tech Lead, DEV | DevOps, Backend, Security, Release Engineer | Architecture or Code Reviewer according to the assigned setup task | Git/project foundation, environment, common components, checks and authorized provider setup; unavailable services block only their dependent work |
| Delivery planning | PM | Product Manager, relevant developers, QA Automation | Delivery Plan Reviewer | Traceable tasks, dependencies, selected screen/design references, expected evidence and completion criteria |
| Development | Assigned Web / Server / Mobile / Game engineer, or full-stack DEV | Frontend, Backend; domain engineers and Technical Artist where needed | Code Reviewer | A usable increment with functional logic, assets and visual fidelity to approved per-screen designs |
| Verification | QC / Test Engineer | QA Automation, Accessibility, Security, Performance, relevant domain expert | Test Reviewer | Reproducible results for the current version, real interface comparison, uncovered criteria and concrete defects |
| Local handoff | PM | Release Engineer, Technical Writer, DevOps; Mobile for installable mobile builds | QA Lead / Product Quality Reviewer | Actual local deliverable, install/run instructions, configuration requirements, known limitations and whole-product evidence |
| Retrospective and process improvement | Process Lead coordinates; Skill Engineer authors an assigned candidate; Evaluation Engineer measures it | PM, Product Manager, affected departments | Independent Improvement Reviewer; QA Lead retains product-quality responsibility | Observed causes, versioned candidate diff, comparable before/after results, regression evidence and an adoption/rollback decision |

The catalog includes software-product positions, design direction and an improvement team. It does not mean every position must run for every task. Core roles own the work; Web, Server, Mobile and Game engineers are distinct implementation workers as well as available specialists. Assign a build task to its specific worker with project configuration `team.task_agents` (task ID to agent ID); `team.build_agent` selects the project default, and `build` remains the full-stack fallback. Assignments do not give write permission to consultations or reviewers. Consultants run separate read-only missions with narrow questions and actual artifacts. Skill Engineer and Evaluation Engineer need an explicitly assigned worker scope to author a candidate or evaluation artifacts. Optional specialists must explain why they are relevant. Game Designer uses the project's game-team setting. Availability alone must not trigger extra infrastructure or broaden product scope.

Design Director judges the journey, functional specification and experience tradeoffs. Art Director judges the actual visual direction, asset decomposition, materials, typography, composition and consistency across screens. Neither invents unavailable Image Gen/browser capabilities or treats a selected image as a playable product. Under the autonomous-company policy, analysis is accepted through independent review and these directors decide design within the delegated scope; final human acceptance is optional. Previously configured human gates and owner-selected design references remain authoritative unless explicitly changed.

## Delegation and exchange

Keep the manager/controller pattern: the controller validates dependency readiness and authoritative state; PM prioritizes and coordinates within that registry. Send bounded questions through the authenticated peer tools, referencing the task, screen ID, artifact/version and decision needed. Structured consultation output contains a summary, findings, limitations and a blocker if one exists. The primary worker integrates useful findings into its actual outputs and identifies unresolved limitations; received advice is not accepted evidence by itself.

Reviewers use fresh read-only context with accepted requirements, actual artifacts, current code and applicable evidence. They do not receive the worker's peer persuasion as an approval or inherit its conversation. Their report must identify concrete inconsistencies and omissions with evidence and severity; merely confirming that files exist is insufficient. Keep specialist advice separate from department acceptance review. Human approval remains at the configured gates.

Model and effort map to the project's maintained model configuration for the assigned role. Do not invent unavailable models, claim that a bigger model guarantees quality, or silently equate requested configuration with observed runtime settings. Concurrency `0` removes the fixed project session cap and dispatches on demand; positive caps remain explicit, and provider capacity still applies. Preserve dependency readiness and the one-source-writer rule; parallelize independent investigation and consultation rather than simultaneous edits to shared source. Dynamic members keep their own session identity even when they share a base role; a base-role label must not merge their missions or imply that an illustrated employee represents several active people.

## Evidence and improvement loop

Record actual session/thread identity, task revision, attempt, requested and observed model settings, real usage, tool/progress events, messages, outputs and independent review. Track delivery and acknowledgement separately. Unknown usage stays unknown. Keep model-capacity retries distinct from product rework; reconcile interrupted sessions before dispatching duplicate work.

Use synthetic controller cases to evaluate routing, dependency/gate preservation, writer exclusion, reviewer isolation, message authenticity, retry recovery and usage deduplication. These checks do not establish real product quality or provider connectivity. For real product quality, evaluate the agreed experience and visuals against actual current outputs, record failures, repair the affected scope and re-review. Do not run a live product merely to validate controller changes.

Process Lead selects a narrow observed problem and a measurable outcome. Skill Engineer records the prior version, candidate version, actual changed guidance and expected mechanism. Evaluation Engineer compares both versions on identical representative inputs, prior failures and counterexamples; records the criteria, evidence and limitations; and separates instruction quality from missing runtime tools or model capacity. Improvement Reviewer independently examines the diff and evaluation, then recommends adoption, further repair or retention of the previous version. Adoption is an explicit recorded state with rollback material, not a conclusion inferred from a proposed change or successful synthetic test. Skill improvements guide a model's work; they cannot promise additional model ability or automatic success. The read-only office surfaces questions, recommendations, before/after findings and version/evidence records without becoming an approval or chat surface.

## Official grounding

This company catalog and department structure are Product-Cycle conventions. The underlying techniques follow official guidance:

- [OpenAI orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration): bounded specialists behind a manager, or explicit ownership handoff when appropriate.
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents): focused parallel work with separate context and configurable roles.
- [Evaluating agent workflows](https://developers.openai.com/api/docs/guides/agent-evals): inspect actual traces and evaluate observable outcomes.

The runtime uses the existing Codex connector and deterministic controller. It does not require adding Agents SDK just to imitate its orchestration pattern.
