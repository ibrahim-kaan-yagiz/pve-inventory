# Ideas

Parking lot for everything deliberately **out of scope** for v1.

v1 is a CLI tool that reads the LXC containers via `pct` and writes a markdown
table to `homelab.md` — nothing more.

**Rule: every new idea goes here, not into the code.**

## Interface and operation

- [ ] Web UI instead of CLI
- [ ] History and change diffs
- [ ] Proxmox API with a token instead of `pct`, for remote operation

## Data collection

- [ ] Multiple network interfaces (`net1`, `net2`, …) instead of only `net0`
- [ ] Evaluate `unprivileged` for a security check
- [ ] Record versions of installed services
- [ ] Document Tailscale routes
- [ ] QEMU VMs in addition to LXC (`qm list` / `qm config`)
- [ ] Determine the actually assigned IP when `ip=dhcp`

## Output

- [ ] Highlight custom config lines such as `lxc.mount.entry`
- [ ] Make missing fields such as `onboot` visible in the output

## Later, at the earliest after v1

- [ ] Paid pro version, at the earliest after the first release
- [ ] E-book or guide on self-hosting, worthwhile only with a user base
