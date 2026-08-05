#!/usr/bin/env python3
"""Liest die LXC-Container eines Proxmox-Hosts via pct aus.

Muss direkt auf dem PVE-Host laufen. Nutzt nur die Standardbibliothek.
"""

import subprocess
import sys

PCT = "/usr/sbin/pct"

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
            "pct %s fehlgeschlagen (rc=%d): %s"
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


def main():
    try:
        containers = collect()
    except (RuntimeError, OSError) as error:
        print("Fehler: %s" % error, file=sys.stderr)
        return 1

    for container in containers:
        print(container)
    return 0


if __name__ == "__main__":
    sys.exit(main())
