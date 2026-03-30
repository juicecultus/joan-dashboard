---
description: Ensure README.md is updated when making documentable changes
---

# Update README Workflow

Whenever you make changes to the joan-dashboard codebase that affect any of the following, you MUST update `README.md` before committing:

## What triggers a README update

1. **New or removed screens** — Update the playlist screen count in the Features heading, the screen description list, the `Available screen names:` line, and the Playlist Screens table.
2. **New environment variables** — Add to the `.env` configuration example block with a comment explaining the variable.
3. **Architecture changes** — Update the "How It Works" section if the rendering/push pipeline changes.
4. **New dependencies or prerequisites** — Update the Prerequisites table and install instructions.
5. **New CLI arguments** — Update the usage examples in Quick Start.
6. **New troubleshooting scenarios** — Add a row to the Troubleshooting table.
7. **Infrastructure/deployment changes** — Update the "Running as a Service" or "Setting Up VSS" sections (including Pi 5 specific steps).
8. **New API integrations** — Update the Tech Stack section and the Additional data sources list.

## How to update

1. Read the current `README.md` to understand existing structure.
2. Make targeted edits to only the affected sections — do not rewrite unrelated parts.
3. Keep the existing tone and formatting style (Markdown tables, code blocks, blockquotes).
4. Include the README changes in the same commit as the code changes, not as a separate commit.

## Checklist before committing

- [ ] Screen count in Features heading matches actual count
- [ ] All env vars used in code appear in the `.env` example
- [ ] Available screen names list matches `ALL_SCREENS` keys
- [ ] Troubleshooting table covers known failure modes
- [ ] Tech Stack lists all external APIs used
