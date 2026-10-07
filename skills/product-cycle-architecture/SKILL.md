---
name: product-cycle-architecture
description: Design scoped data contracts, component boundaries and technical decisions from accepted requirements and design.
---

# Technical design

Reuse existing structures. Record consequential choices and unresolved risks. Verify uncertain technical assumptions with focused experiments when useful; do not add architecture or infrastructure without a concrete requirement.

Use design.md's shared rules, screen/action IDs and behavior as the functional contract. In architecture.md, map the relevant actions to data/state ownership, component boundaries, validation, persistence and API/error contracts where needed. Separate common technical behavior from screen-specific behavior and reference the spec rather than duplicating it. Resolve contradictions with accepted requirements/design before dependent work; architecture must not silently redefine product behavior.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Read the relevant source and rules; reuse existing components.
2. Specify data, component boundaries and communication contracts.
3. Choose an implementation within scope and explain consequential tradeoffs.
4. Investigate uncertain technical assumptions or record the dependent blocker.
5. Define verification and recovery for the selected product.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

New local cycles use policy.service_setup_required: architecture identifies necessary services and user inputs without configuring them; plan links each increment to its required services and defines local delivery; handoff presents the verified local product. Configuration tasks run after design and plan review. VPS and external release are deferred. Respect configured owner gates.

For cycles with project_setup_required, produce project-setup.json describing the selected stack, structure, coding rules, tooling, common components, environment names and actual foundation checks. The controller creates a preparatory task inside Development, before feature tasks.

## Game products

If the brief or accepted direction asks for a game, read [Game Design](../product-cycle-game-design/SKILL.md) as a companion to this stage. Use its architecture guidance to map accepted gameplay rules to rendering, input/state/time ownership, assets and supported device constraints without choosing a new game concept. Keep accepted scope, configured owner gates and evidence boundaries; the companion is not a new stage or an execution command.

## Versioned verification contract

For agent_workflow_version=1, produce verification.json using context.verification_contract_path. Specify launch/readiness, read-only doctor, actual user-facing procedures, environment/tool needs, instance isolation, evidence and cleanup. Select exclusive for a shared runtime that cannot safely be driven concurrently; isolated requires separate instance/data/ports. Planned commands do not establish connectivity or behavior. The reviewed feature map follows architecture before planning.
