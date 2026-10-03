# Evidence-based improvement

Use the cycle history, task evidence, review findings, decisions, elapsed time, token usage where available, and any real product feedback. Produce retro.json:
{"observations":[{"finding":"What actually happened","evidence_ids":["E-example"]}],"improvements":[{"change":"Specific change to a skill, tool, model policy, or routing","evidence_ids":["E-example"],"eval_case":{"input":"Reproducible scenario","expected":"Observable success criterion"}}]}

An empty improvements array is valid if evidence supports no change. Avoid generic advice. Identify whether the issue came from product ambiguity, context, a missing tool, execution, validation, or model reasoning. Do not automatically modify the active workflow. Candidate improvements must be evaluated against representative and previously failing scenarios before adoption. Include user adoption or production feedback only if it was actually supplied.
