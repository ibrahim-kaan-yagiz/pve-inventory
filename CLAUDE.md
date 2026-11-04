# CLAUDE.md

## Project

pve-inventory is a single Python script (`pve_inventory.py`) that reads the LXC
containers on a Proxmox VE host via `pct` and writes a markdown table to
`homelab.md`. `homelab.md` is generated output and stays in `.gitignore`.

## Rules

- Everything in the repo is in English: code, comments, docstrings, commit
  messages, README, IDEAS.md.
- Python 3 standard library only. No external dependencies.
- The script runs on the Proxmox host itself as root, because `pct` needs root.
  There is no remote or API mode in v1.
- Missing fields are rendered as `–` so a container never breaks the table.
- Scope: v1 is a CLI that writes `homelab.md`, nothing more. Implement only what
  the current task asks for. Any new idea goes into IDEAS.md, not into the code.
- When behaviour or output changes, update README.md in the same change
  (example output, Limitations section).

## Testing

`pct` is not available outside a Proxmox host. Test parsing and rendering with
realistic sample output of `pct list` and `pct config`. Never claim something
was tested on a real host unless it was.

## Git

- Work on a separate branch and open a pull request. Never push to main.
- The owner reviews and merges every pull request himself.

## Communication

- Talk to me in German.
- Explain steps one at a time, one step per message.
