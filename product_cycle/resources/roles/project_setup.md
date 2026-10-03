# Set up the product project

Read context.project_setup from accepted architecture and plan. Before features, create CODING_RULES.md at the project root with the selected language/framework conventions: naming, formatting, types, module boundaries, dependencies, error handling, logging, configuration, testing and UI rules where applicable. State concrete tools/commands and justified omissions.

Set up the designed source structure, local runtime, dependencies, development scripts and required shared components. Do not implement the feature backlog in this stage. Preserve existing code and configuration; do not edit AGENTS.md, PRODUCT_CYCLE_RULES.md or installed skills.

If environment_names is nonempty, produce .env.example with names and safe empty/example values. Never supply credentials. External services have their own setup tasks; use local defaults or fail clearly when a missing integration is invoked.

Produce project-setup.md in artifact_directory with actual files, installation/run/check commands and limitations. Register CODING_RULES.md, .env.example when required, and source/tooling files as artifacts. The controller runs architecture setup checks and independent review before feature tasks are released.

Graphify is optional for complex existing code relationships. Record a reason in architecture before adding it. For a new small codebase use direct inspection and search. Do not install global hooks or enable a remote semantic backend as part of ordinary setup.
