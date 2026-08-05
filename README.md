# pve-inventory

Reads the LXC containers on a Proxmox VE host via `pct` and writes a markdown
table to `homelab.md`.

## Example output

```markdown
# Homelab – LXC Containers

Generated 2026-08-05 14:30:00

| CTID | Hostname | Status | CPU/RAM | Storage | Network | Autostart | Purpose |
|---|---|---|---|---|---|---|---|
| 100 | proxy | running | 2 Cores / 1024 MB | local-lvm, 8G | vmbr0, 192.168.1.10/24 | yes (order 1) | Reverse proxy |
| 101 | db | running | 4 Cores / 4096 MB | local-zfs, 32G | vmbr0, DHCP | yes | Postgres |
| 102 | scratch | stopped | 1 Core / 512 MB | local-lvm, 4G | – | no | – |
```

Missing fields are rendered as `–`, so containers without a network interface,
a description or an `onboot` setting still show up.

## Installation

```sh
git clone https://github.com/ibrahim-kaan-yagiz/pve-inventory.git
cd pve-inventory
sudo python3 pve_inventory.py
```

`homelab.md` is written to the current directory and overwritten on every run.

## Requirements

- A Proxmox VE host; the script calls `pct` and has to run on the host itself
- Python 3
- root, because `pct` needs it
- No external dependencies, standard library only

## Filling the Purpose column

The Purpose column comes from the container description, which is empty by
default. Set it per container:

```sh
pct set 100 --description "Reverse proxy"
```

The same text appears in the Proxmox web UI as the container's Notes.
Multi-line descriptions are kept and joined with `<br>` so they stay inside one
table cell.

## Limitations

- LXC containers only, no QEMU VMs
- Only the first network interface (`net0`) is reported
- Has to run on the Proxmox host itself, there is no remote or API mode

Ideas that are deliberately out of scope for now are collected in
[IDEAS.md](IDEAS.md).
