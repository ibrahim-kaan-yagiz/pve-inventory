#!/usr/bin/env python3
"""Read the LXC containers of a Proxmox host via pct.

Must run directly on the PVE host. Standard library only.
"""

import datetime
import functools
import os
import shutil
import subprocess
import sys
from urllib.parse import unquote

# Usual location on a PVE host; PATH is searched as a fallback.
PCT_PATH = "/usr/sbin/pct"

# Upper bound per pct call so a hung host does not block the run forever.
PCT_TIMEOUT = 60

ROOT_HINT = "pct requires root privileges - run this script as root (e.g. via sudo)."

NOT_A_PVE_HOST = (
    "pct not found (looked at %s and on PATH). This script has to run "
    "directly on a Proxmox VE host." % PCT_PATH
)

# stderr fragments that indicate pct refused the access rather than failing
# for a container-specific reason.
PERMISSION_MARKERS = (
    "permission denied",
    "insufficient permission",
    "no permission",
    "only root",
    "must be root",
    "need to be root",
    "not authorized",
    "operation not permitted",
)

# Target file for the markdown table, relative to the current directory.
OUTPUT_FILE = "homelab.md"

# Placeholder for fields the container does not set.
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

# Fields whose value is a comma-separated key-value string and that are
# additionally broken out into a sub-dict.
STRUCTURED_PREFIXES = ("net", "rootfs", "mp", "unused")

# Fields whose first element is positional (a volume without "=").
VOLUME_FIELDS = ("rootfs", "mp", "unused")


class PctError(RuntimeError):
    """Raised when pct cannot be run or reports a failure."""


def looks_like_permission_error(text):
    """True if the pct output points at missing privileges."""
    lowered = (text or "").lower()
    return any(marker in lowered for marker in PERMISSION_MARKERS)


@functools.lru_cache(maxsize=1)
def resolve_pct():
    """Return the path to the pct executable.

    Raises PctError with an explanatory message when pct is missing (not
    a PVE host) or cannot be executed by the current user (not root).
    """
    for candidate in (PCT_PATH, shutil.which("pct")):
        if candidate and os.path.isfile(candidate):
            if os.access(candidate, os.X_OK):
                return candidate
            raise PctError(
                "%s exists but is not executable as uid %d. %s"
                % (candidate, os.geteuid(), ROOT_HINT)
            )
    raise PctError(NOT_A_PVE_HOST)


def run_pct(args):
    """Run pct with the given arguments and return stdout."""
    command = [resolve_pct()] + args
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=PCT_TIMEOUT,
        )
    except FileNotFoundError:
        # pct disappeared between the lookup and the call.
        raise PctError(NOT_A_PVE_HOST)
    except PermissionError:
        raise PctError("Cannot execute %s. %s" % (command[0], ROOT_HINT))
    except subprocess.TimeoutExpired:
        raise PctError(
            "pct %s timed out after %d seconds." % (" ".join(args), PCT_TIMEOUT)
        )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        message = "pct %s failed (rc=%d)" % (" ".join(args), result.returncode)
        if stderr:
            message += ": %s" % stderr
        if looks_like_permission_error(stderr) or (not stderr and os.geteuid() != 0):
            message += "\n%s" % ROOT_HINT
        raise PctError(message)
    return result.stdout


def parse_pct_list(output):
    """Parse the table printed by 'pct list' into a list of dicts.

    Column boundaries are derived from the header line because the Lock
    column is usually empty, which would shift the columns if the rows
    were split on whitespace.

    An empty container list is not an error: pct still prints the header,
    so the result is simply an empty list.
    """
    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        return []

    header = lines[0]
    columns = []
    for name in header.split():
        start = header.index(name, columns[-1][1] if columns else 0)
        columns.append((name.lower(), start))

    if not any(name == "vmid" for name, _ in columns):
        # Without a VMID column this is not the table we expect, and
        # silently returning nothing would look like "no containers".
        raise PctError(
            "Unexpected 'pct list' output, no VMID column found:\n%s" % header
        )

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
    """Break a comma-separated key-value string into a dict.

    with_volume=True treats a leading element without "=" as a volume
    reference (e.g. 'local-lvm:vm-100-disk-0,size=8G').
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
    """Parse 'pct config <id>' into a dict.

    Structured fields (net0, rootfs, mp0, ...) are additionally stored as
    a broken-out sub-dict under '<field>_parsed'.
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
    """Collect status and configuration of all containers."""
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
    """'2 Cores / 2048 MB', with a placeholder for a missing half."""
    cores = config.get("cores")
    memory = config.get("memory")
    if not cores and not memory:
        return MISSING
    return "%s / %s" % (
        format_cores(cores) if cores else MISSING,
        "%s MB" % memory if memory else MISSING,
    )


def format_cores(cores):
    """'1 Core' or '2 Cores' - singular only for exactly one core."""
    try:
        singular = int(cores) == 1
    except (TypeError, ValueError):
        singular = False
    return "%s %s" % (cores, "Core" if singular else "Cores")


def format_storage(config):
    """'local-lvm, 20G' from rootfs_parsed."""
    rootfs = config.get("rootfs_parsed") or {}
    volume = rootfs.get("volume", "")
    # The backend is the part before the colon: 'local-lvm:vm-100-disk-0'.
    backend = volume.split(":")[0] if volume else ""
    size = rootfs.get("size", "")
    if not backend and not size:
        return MISSING
    return "%s, %s" % (backend or MISSING, size or MISSING)


def format_network(config):
    """'vmbr0, 192.168.178.72/24' or 'vmbr0, DHCP' from net0_parsed."""
    net = config.get("net0_parsed") or {}
    bridge = net.get("bridge", "")
    ip = net.get("ip", "")
    if ip.lower() == "dhcp":
        ip = "DHCP"
    if not bridge and not ip:
        return MISSING
    return "%s, %s" % (bridge or MISSING, ip or MISSING)


def format_autostart(config):
    """'yes' for onboot=1, with the startup order if set, otherwise 'no'."""
    if config.get("onboot", "0").strip() != "1":
        return "no"
    startup = parse_kv_string(config.get("startup", ""))
    order = startup.get("order")
    return "yes (order %s)" % order if order else "yes"


def format_purpose(config):
    """The container description, collapsed to a single table cell.

    pct stores the description URL-encoded (a newline as %0A), so decode
    it first and then turn the line breaks into <br>.
    """
    description = unquote(config.get("description", "")).strip()
    if not description:
        return MISSING
    lines = [line.strip() for line in description.splitlines() if line.strip()]
    return "<br>".join(lines) if lines else MISSING


def escape_cell(value):
    """Make a value safe for a markdown table cell.

    Pipes end a cell and line breaks end a row, so both have to go: pipes
    are escaped, line breaks become <br>. Applied to every cell, not just
    the description, so no field can break the table layout.
    """
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("|", "\\|")
    return "<br>".join(part.strip() for part in text.split("\n"))


def build_row(container):
    """Build the cells of one table row for a container."""
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
    """Render the complete markdown document as a string."""
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
    """Write the markdown table to path."""
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
