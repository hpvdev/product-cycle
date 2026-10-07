# Feature map

Read accepted requirements, design and architecture, including verification.json. Produce feature-map.json and a short feature-map.md. Each feature has a stable id, name, purpose, requirements, depends_on feature IDs, screen_states:[{screen_id,state}], code_entry_points, implementation_status:"planned", and verification procedure IDs from verification.json. Use version:1. Cover accepted requirements; do not invent screens or claim planned entry points already exist.

Explain how users reach each feature, its visible behavior, dependencies, expected results and verification limitations. This map is maintained through build and integration. Runtime evidence and confirmed code entry points belong to implementation; a draft map is not proof of behavior. Gate authority follows context.authority; independent review remains required.
