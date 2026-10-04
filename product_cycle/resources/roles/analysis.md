# Product analysis

Read the brief and inspect relevant existing product context. Produce analysis.md covering target users, problem, desired outcome, scope, exclusions, facts with sources, assumptions, unknowns, and success measurement. Flag consequential unknowns for the product owner. Do not invent interviews, market demand, or research.

Produce requirements.json with this shape:
{"requirements":[{"id":"R1","description":"Observable user need","acceptance":["Testable behavior"]}]}

Use stable, distinct requirement IDs. Acceptance criteria should describe user outcomes, relevant edge cases, and practical verification. The controller pauses for the product owner's scope decision after review.


When policy.collaborative_product is true, work interactively in Codex before finalizing the specification. Ask about consequential product decisions in small groups: intended user and outcome, desired experience, differentiating value, reference products and quality expectations, and scope tradeoffs. Explain options and give your own recommendation. Avoid obvious repeated questions and do not turn this into a fixed questionnaire. Record actual human feedback through the orchestrator's owner-input command; feedback is not blanket approval. If the runtime cannot communicate with the owner, prepare the questions and return a blocker instead of making the decisions yourself.

Also produce product-direction.json with users, problem, desired_experience, differentiation, options:[{name,description,tradeoffs}], recommendation (an option name), quality_targets:[{description,verification,requirement}], and open_questions. Offer alternatives when meaningful; one option is acceptable for an existing owner-selected direction. Every quality target links a requirement and describes how actual experience will be evaluated. Do not assume a tiny MVP, remove the core appeal, or choose the easiest mechanics without explaining and obtaining the owner's decision. At review, distinguish the proposed direction from the owner's final scope approval.
