# Configure the assigned service

Run only after analysis, UX/UI, architecture and plan have completed independent review. The context.service is the exact accepted service contract for this task. Configure this service only; build increments that do not depend on it may continue independently.

Check the capabilities available to this worker. A logged-in Chrome tab in another session is not proof of access. Confirm the active Chrome profile before use; never use hungpv@hblab.vn / HungPV or an unidentified profile. Use the user's designated accounts and project through available CLI/API/MCP or computer use. Follow current provider documentation for this service. Access missing from this runtime is a capability blocker, not success.

Configure within authorized scope; keep secrets in provider/OS storage or secure environment files. Artifacts, screenshots, logs, URLs and argv must not contain secret values. Identify names/references of required credentials and scoped permissions, who supplies them and the next action. Do not purchase services, send email/messages, provision VPS or deploy. Local development is the current delivery scope.

Produce setup.md and readiness.json: {"services":[{"id":"context.service.id","status":"ready|needs_input|configuring|failed","note":"Observed result or exact missing input and next action","input_refs":["names/references only"]}]}. The controller executes checks from the accepted design before independent review. Returning ready does not itself prove connection success.

When required access, capability or inputs are missing, still produce these files and a concrete result.blocker. The controller records the report and blocks dependent work. No review approval until the blocker is resolved and real checks pass. Do not mark unavailable integrations as complete. VPS, remote release and DeployGate remain deferred.
