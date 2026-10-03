# Stage contracts

Role guidance ships in `product_cycle/resources/roles/`. Load only the assigned role. File names are package conventions, not universal OpenAI requirements.

| Stage | Required output | Review focus |
|---|---|---|
| analysis | analysis.md, requirements.json | Outcome, facts/assumptions, scope, testable acceptance |
| design | design.md and visual artifact for UI | Journeys, states, requirement coverage, accessibility |
| architecture | architecture.md | Data, boundaries, decisions, verification and recovery |
| plan | plan.json | Coverage, acyclic tasks, local checks, runtime capabilities |
| build | Actual product changes | Scope, correctness, checks, criterion links |
| verify | acceptance.md and observed evidence | Coverage, version, actual behavior |
| handoff | handoff.md | Setup, results, limitations, recovery, source location |
| retro | retro.json | Trace-supported findings and evaluable improvements |

Work result: `{summary,artifacts:[{path,purpose,criteria,requirements}],limitations,blocker}`. Paths are project-relative; criteria use C1, C2, etc. Required files go in the assigned artifact directory. A non-null blocker cannot be accepted.

Review result: `{decision,summary,criteria:[{id,passed,evidence,reason}],findings}`. Decisions: approve/rework/blocked. Passing criteria reference real evidence IDs. Human observations, controller checks, worker artifacts, and semantic opinions retain separate provenance. AI review does not guarantee product quality.

Plan tasks: `{id,title,instructions,depends_on,requirements,criteria,checks}`. Task IDs start with T. Checks and verification_commands are argv arrays. browser_required requires real operator browser evidence covering requirements before acceptance; model statements are not browser observations.
