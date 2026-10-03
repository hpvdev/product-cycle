# Executable plan

Produce plan.json with this shape:
{"tasks":[{"id":"T1","title":"User-visible increment","instructions":"Concrete scope and deliverables","depends_on":[],"requirements":["R1"],"criteria":["Observable completion condition"],"checks":[["python3","existing_check.py"]]}],"verification_commands":[["python3","existing_check.py"]],"browser_required":false}

Commands are argv arrays executed by the controller, without shell interpretation. They must be relevant, bounded, repeatable, local verification commands within the authorized project. Do not use a shell wrapper, network publication, destructive command, or secrets in command arguments. Include checks that will exist after development; explain their intended coverage in task instructions. Prefer existing checks; add focused tests when realistic acceptance criteria require them.

Cover every accepted requirement. Task dependencies must be acyclic. Split tasks into coherent, reviewable increments. Require real browser verification for a user-facing UI when acceptance depends on interaction or appearance. Human browser evidence can be registered if this runtime has no browser tool. Do not confuse browser availability with browser verification. The product owner approves this plan before any build task starts.
