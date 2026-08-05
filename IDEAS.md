# Ideen

Parkplatz für alles, was bewusst **nicht** in v1 gehört.

v1 ist ein CLI-Tool, das per `pct` die LXC-Container ausliest und eine
Markdown-Tabelle in `homelab.md` schreibt — mehr nicht.

**Regel: jede neue Idee kommt hierher, nicht in den Code.**

## Oberfläche und Betrieb

- [ ] Web-UI statt CLI
- [ ] Historie und Änderungs-Diffs
- [ ] Proxmox-API mit Token statt `pct`, für Remote-Betrieb

## Datenerfassung

- [ ] Mehrere Netzwerk-Interfaces (`net1`, `net2`, …) statt nur `net0`
- [ ] `unprivileged` auswerten für einen Security-Check
- [ ] Versionsstände installierter Dienste erfassen
- [ ] Tailscale-Routen dokumentieren
- [ ] QEMU-VMs zusätzlich zu LXC (`qm list` / `qm config`)
- [ ] Bei `ip=dhcp` die tatsächlich vergebene IP ermitteln

## Ausgabe

- [ ] Custom-Config-Zeilen wie `lxc.mount.entry` hervorheben
- [ ] Fehlende Felder wie `onboot` in der Ausgabe sichtbar machen

## Codebasis

- [ ] Kommentare und Docstrings von Deutsch auf Englisch umstellen, sobald das
      Projekt Mitwirkende bekommt

## Später, frühestens nach v1

- [ ] Bezahlte Pro-Version, frühestens nach dem ersten Release
- [ ] E-Book bzw. Guide zum Thema Self-Hosting, sinnvoll erst mit Nutzerbasis
