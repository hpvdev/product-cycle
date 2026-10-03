# Product analysis

Read the brief and inspect relevant existing product context. Produce analysis.md covering target users, problem, desired outcome, scope, exclusions, facts with sources, assumptions, unknowns, and success measurement. Flag consequential unknowns for the product owner. Do not invent interviews, market demand, or research.

Produce requirements.json with this shape:
{"requirements":[{"id":"R1","description":"Observable user need","acceptance":["Testable behavior"]}]}

Use stable, distinct requirement IDs. Acceptance criteria should describe user outcomes, relevant edge cases, and practical verification. The controller pauses for the product owner's scope decision after review.
