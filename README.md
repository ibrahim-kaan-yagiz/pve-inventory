# pve-inventory

Reads the LXC containers on a Proxmox VE host via `pct` and writes a markdown
table to `homelab.md`.

## Example output

```markdown
# Homelab – LXC Containers

Generated 2026-08-05 23:24:17

| CTID | Hostname | Status | CPU/RAM | Storage | Network | Autostart | Purpose |
|---|---|---|---|---|---|---|---|
| 100 | minecraft-server | running | 2 Cores / 2048 MB | local-lvm, 20G | vmbr0, 192.168.178.72/24 | yes (order 3) | Minecraft server for friends |
| 101 | discord-bot | running | 1 Core / 1024 MB | local-lvm, 8G | vmbr0, DHCP | yes (order 2) | Discord bot |
| 102 | tailscale | running | 1 Core / 1024 MB | local-lvm, 6G | vmbr0, DHCP | yes (order 1) | Tailscale subnet router for 192.168.178.0/24 |
| 103 | uptime-kuma | running | 1 Core / 512 MB | local-lvm, 8G | vmbr0, DHCP | no | Uptime Kuma monitoring |
| 104 | nginx-proxy-manager | running | 1 Core / 1024 MB | local-lvm, 8G | vmbr0, 192.168.178.80/24 | no | Nginx Proxy Manager reverse proxy |
| 105 | n8n-server | running | 2 Cores / 2048 MB | local-lvm, 10G | vmbr0, DHCP | no | n8n automation workflows |
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
