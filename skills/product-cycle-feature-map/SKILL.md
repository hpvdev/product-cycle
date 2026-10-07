---
name: product-cycle-feature-map
description: Map accepted Product Cycle features to requirements, screen states, dependencies and concrete verification procedures before planning, then maintain observed implementation links.
---

# Feature map

Work only on the assigned project and stage. Read its rules and accepted requirements, design, architecture and verification.json. Map stable feature IDs to user-facing behavior and observable acceptance. Return feature-map.json (version:1) and feature-map.md in the assigned artifact directory.

Each feature includes id, name, purpose, requirements, depends_on feature IDs, screen_states:[{screen_id,state}], code_entry_points, implementation_status:"planned", and verification procedure IDs. Explain how users reach it, what to do, expected effects and evidence needed. Before build, code entry points are proposals and may be empty. Use the accepted visual reference and exact behavior specification; do not build HTML/CSS prototypes to make design images.

During build/integration, update the assigned features with actual code paths and runtime observations. Separate planned, workspace-verified, integrated and product-verified outcomes. Preserve evidence and authority boundaries. Never infer tool availability from a role title or claim observed behavior from an image or a generated map.
