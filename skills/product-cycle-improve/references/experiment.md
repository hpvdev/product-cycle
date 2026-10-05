# Experiment contract

`ImprovementStore` is a controller API; agents submit artifacts through their authenticated mission. The controller constructs it with default trusted targets/checks. Agents cannot register targets, command argv or permissions.

Candidate (`improve_propose`):

```json
{
  "schema_version": 1,
  "title": "Wait without repeated full-context reads",
  "rationale": "A recorded mission repeatedly reread unchanged files during a Desktop handoff.",
  "hypothesis": "A bounded wait preserves the handoff evidence while reducing redundant reads.",
  "case_ids": [".product-cycle/artifacts/design/r1/a1/work/raw-handoff-case.json"],
  "changes": [{
    "target_id": "product-cycle-design",
    "before_sha256": "controller-supplied current guidance hash, or SHA256 of empty bytes",
    "guidance": "During a pending Desktop handoff, wait in bounded intervals and inspect only the requested manifest until it changes. Keep the original references accessible."
  }],
  "evidence": [".product-cycle/artifacts/design/r1/a1/work/raw-handoff-case.json", ".product-cycle/artifacts/design/r1/a1/work/observation.json"]
}
```

Only listed installed skill targets are eligible, at most three. Original `SKILL.md` content is preserved; the controller adds a fixed link to the learned-guidance reference. Guidance cannot contain executable blocks, remote references, or permission/policy/goal/acceptance instructions. This conservative filter and bounded file scope supplement semantic independent review; a text filter cannot prove every possible statement safe.

`evaluate(candidate_id)` runs the controller's fixed checks against sealed before and after versions. It leaves a passing candidate `evaluating` until a separate actual forward report exists. Obtain its immutable packet from `evaluation_context(candidate_id)`.

Forward report (`improve_evaluate`):

```json
{
  "candidate_hash": "from evaluation context",
  "context_hash": "from evaluation context",
  "decision": "pass",
  "permissions_preserved": true,
  "goals_preserved": true,
  "acceptance_preserved": true,
  "cases": [{
    "case_id": ".product-cycle/artifacts/design/r1/a1/work/raw-handoff-case.json",
    "input_artifact": ".product-cycle/improvement-tests/raw-handoff-copy.json",
    "input_sha256": "exact sealed raw_case_sources hash",
    "before_artifacts": [".product-cycle/improvement-tests/before.json"],
    "after_artifacts": [".product-cycle/improvement-tests/after.json"],
    "improved": true,
    "regressed": false,
    "reason": "Concrete observed before/after difference, including remaining limitations."
  }]
}
```

case_ids are project-relative raw input paths included in candidate evidence. Evidence must be workflow artifacts under `.product-cycle/`; private files, source files outside that directory and symlinks are excluded. evaluation_context.raw_case_sources provides their sealed bytes and SHA256. Both variants use the identical input; input_artifact must retain that exact hash. Use the same raw cases and actual outputs. Every case must have both sets of artifacts. `fail` or a regression rejects the candidate; one supported benefit and no regression are required to advance. File existence is provenance, not proof the author's claim is true: the fresh reviewer judges those actual artifacts.

Review (`improve_review`): obtain `review_context(candidate_id)` after verified evaluation. Submit `candidate_hash`, `context_hash`, `decision` (`approve` or `reject`), `reason`, `findings` (string array), `artifacts` (actual report paths), and true attestations `permissions_preserved`, `goals_preserved`, `acceptance_preserved`, `evidence_verified`. Use a different recorded identity/thread from author and evaluator, without their chat history. Check claims against raw output and exact immutable versions.

Controller lifecycle:

- `propose(bundle, author_run_id)` stores a versioned candidate and sealed snapshots.
- `evaluate(id)` runs registered checks; `record_evaluation(id, report, evaluator_run_id)` records forward evidence.
- `record_review(id, report, reviewer_run_id)` records the fresh independent decision.
- `apply(id)` defaults to automatic use after the whole product cycle is done. It requires independent approval, no active/unknown missions or pending reviewed owner decision, unchanged known-original installed versions, and a restorable backup. A deliberately scoped manual stable-point update uses automatic=False and a recorded reason. Apply and rollback refresh the foundation through normal bootstrap; earlier product evidence remains tied to its original source fingerprint.
- `monitor(id)` executes registered checks, with truthful structural-monitoring limits; a failed check triggers stable-point rollback.
- `rollback(id)` restores that version's before state and manifest entries, preserving any later customization rather than overwriting it.
- `snapshot()` exposes versions, before/after hashes, evidence, decisions and durable events. Interrupted filesystem transitions remain visible and are not silently retried.

Application and rollback never commit, push, publish or change product goals, configured gates, controller permissions or registered product evidence. An installed-skill update changes the source fingerprint; do not apply while an owner decision is pending for an earlier reviewed fingerprint.
