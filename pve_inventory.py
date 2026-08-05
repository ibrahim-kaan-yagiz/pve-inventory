#!/usr/bin/env python3
"""Liest die LXC-Container eines Proxmox-Hosts via pct aus.

Muss direkt auf dem PVE-Host laufen. Nutzt nur die Standardbibliothek.
"""

import datetime
import subprocess
import sys
from urllib.parse import unquote

PCT = "/usr/sbin/pct"

# Zieldatei der Markdown-Tabelle, relativ zum aktuellen Verzeichnis.
OUTPUT_FILE = "homelab.md"

# Platzhalter fuer Felder, die der Container nicht gesetzt hat.
MISSING = "–"

COLUMNS = (
    "CTID",
    "Hostname",
    "Status",
    "CPU/RAM",
    "Storage",
    "Network",
    "Autostart",
    "Purpose",
)

# Felder, deren Wert ein komma-separierter Key-Value-String ist und die
# zusaetzlich in ein Sub-Dict aufgeschluesselt werden.
STRUCTURED_PREFIXES = ("net", "rootfs", "mp", "unused")

# Felder, bei denen das erste Element positional ist (Volume-Angabe ohne "=").
VOLUME_FIELDS = ("rootfs", "mp", "unused")


def run_pct(args):
    """Ruft pct mit den uebergebenen Argumenten auf und liefert stdout."""
    result = subprocess.run(
        [PCT] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "pct %s failed (rc=%d): %s"
            % (" ".join(args), result.returncode, result.stderr.strip())
        )
    return result.stdout


def parse_pct_list(output):
    """Parst die Tabelle von 'pct list' in eine Liste von Dicts.

    Die Spaltenbreiten werden aus der Kopfzeile abgeleitet, weil die
    Lock-Spalte haeufig leer ist und ein simples split() sonst die
    Spalten verschieben wuerde.
    """
    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        return []

    header = lines[0]
    columns = []
    for name in header.split():
        start = header.index(name, columns[-1][1] if columns else 0)
        columns.append((name.lower(), start))

    containers = []
    for line in lines[1:]:
        entry = {}
        for index, (name, start) in enumerate(columns):
            end = columns[index + 1][1] if index + 1 < len(columns) else len(line)
            entry[name] = line[start:end].strip()
        if entry.get("vmid"):
            containers.append(entry)
    return containers


def parse_kv_string(value, with_volume=False):
    """Schluesselt einen komma-separierten Key-Value-String auf.

    with_volume=True behandelt ein fuehrendes Element ohne "=" als
    Volume-Angabe (z.B. 'local-lvm:vm-100-disk-0,size=8G').
    """
    parsed = {}
    for position, part in enumerate(value.split(",")):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, _, item = part.partition("=")
            parsed[key.strip()] = item.strip()
        elif position == 0 and with_volume:
            parsed["volume"] = part
        else:
            parsed[part] = ""
    return parsed


def parse_pct_config(output):
    """Parst 'pct config <id>' in ein Dict.

    Strukturierte Felder (net0, rootfs, mp0, ...) landen zusaetzlich
    als aufgeschluesseltes Sub-Dict unter '<feld>_parsed'.
    """
    config = {}
    for line in output.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        config[key] = value

        if key.startswith(STRUCTURED_PREFIXES) and value:
            config[key + "_parsed"] = parse_kv_string(
                value, with_volume=key.startswith(VOLUME_FIELDS)
            )
    return config


def collect():
    """Sammelt Status und Konfiguration aller Container."""
    containers = parse_pct_list(run_pct(["list"]))
    for container in containers:
        vmid = container["vmid"]
        try:
            container["config"] = parse_pct_config(run_pct(["config", vmid]))
        except RuntimeError as error:
            container["config"] = {}
            container["error"] = str(error)
    return containers


def format_cpu_ram(config):
    """'2 Cores / 2048 MB', fehlende Haelften als Platzhalter."""
    cores = config.get("cores")
    memory = config.get("memory")
    if not cores and not memory:
        return MISSING
    return "%s / %s" % (
        format_cores(cores) if cores else MISSING,
        "%s MB" % memory if memory else MISSING,
    )


def format_cores(cores):
    """'1 Core' bzw. '2 Cores' - Singular nur bei exakt einem Kern."""
    try:
        singular = int(cores) == 1
    except (TypeError, ValueError):
        singular = False
    return "%s %s" % (cores, "Core" if singular else "Cores")


def format_storage(config):
    """'local-lvm, 20G' aus rootfs_parsed."""
    rootfs = config.get("rootfs_parsed") or {}
    volume = rootfs.get("volume", "")
    # Backend ist der Teil vor dem Doppelpunkt: 'local-lvm:vm-100-disk-0'.
    backend = volume.split(":")[0] if volume else ""
    size = rootfs.get("size", "")
    if not backend and not size:
        return MISSING
    return "%s, %s" % (backend or MISSING, size or MISSING)


def format_network(config):
    """'vmbr0, 192.168.178.72/24' bzw. 'vmbr0, DHCP' aus net0_parsed."""
    net = config.get("net0_parsed") or {}
    bridge = net.get("bridge", "")
    ip = net.get("ip", "")
    if ip.lower() == "dhcp":
        ip = "DHCP"
    if not bridge and not ip:
        return MISSING
    return "%s, %s" % (bridge or MISSING, ip or MISSING)


def format_autostart(config):
    """'yes' bei onboot=1, mit Startup-Order falls gesetzt, sonst 'no'."""
    if config.get("onboot", "0").strip() != "1":
        return "no"
    startup = parse_kv_string(config.get("startup", ""))
    order = startup.get("order")
    return "yes (order %s)" % order if order else "yes"


def format_purpose(config):
    """Beschreibungstext des Containers, einzeilig fuer die Tabelle.

    pct speichert die Description URL-kodiert (Zeilenumbruch als %0A),
    daher erst dekodieren und dann auf <br> umstellen.
    """
    description = unquote(config.get("description", "")).strip()
    if not description:
        return MISSING
    lines = [line.strip() for line in description.splitlines() if line.strip()]
    return "<br>".join(lines) if lines else MISSING


def escape_cell(value):
    """Schuetzt Pipes, damit sie die Tabelle nicht zerreissen."""
    return str(value).replace("|", "\\|")


def build_row(container):
    """Baut die Zellen einer Tabellenzeile fuer einen Container."""
    config = container.get("config") or {}
    return [
        container.get("vmid") or MISSING,
        config.get("hostname") or container.get("name") or MISSING,
        container.get("status") or MISSING,
        format_cpu_ram(config),
        format_storage(config),
        format_network(config),
        format_autostart(config),
        format_purpose(config),
    ]


def render_markdown(containers, generated_at=None):
    """Erzeugt das komplette Markdown-Dokument als String."""
    if generated_at is None:
        generated_at = datetime.datetime.now()

    lines = [
        "# Homelab – LXC Containers",
        "",
        "Generated %s" % generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "| %s |" % " | ".join(COLUMNS),
        "|%s|" % "|".join(["---"] * len(COLUMNS)),
    ]
    for container in containers:
        lines.append("| %s |" % " | ".join(escape_cell(c) for c in build_row(container)))
    if not containers:
        lines.extend(["", "No containers found."])
    lines.append("")
    return "\n".join(lines)


def write_markdown(containers, path=OUTPUT_FILE):
    """Schreibt die Markdown-Tabelle nach path."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_markdown(containers))
    return path


def main():
    try:
        containers = collect()
    except (RuntimeError, OSError) as error:
        print("Error: %s" % error, file=sys.stderr)
        return 1

    try:
        path = write_markdown(containers)
    except OSError as error:
        print("Error writing %s: %s" % (OUTPUT_FILE, error), file=sys.stderr)
        return 1

    print("Wrote %d container(s) to %s" % (len(containers), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
