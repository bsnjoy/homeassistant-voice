#!/usr/bin/env python3
"""Toggle or set a Home Assistant entity from the command line.

Usage:
  ./ha.py <entity_id>              # toggle
  ./ha.py <entity_id> on|1         # turn_on
  ./ha.py <entity_id> off|0        # turn_off

Reads HA URL + token from config.py.
"""
import sys
import requests
import config

ON = {"on", "1", "true"}
OFF = {"off", "0", "false"}


def main(argv):
    if len(argv) < 2 or len(argv) > 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    entity_id = argv[1]
    if "." not in entity_id:
        print(f"entity_id must be domain.object_id, got {entity_id!r}", file=sys.stderr)
        sys.exit(2)
    domain = entity_id.split(".", 1)[0]

    if len(argv) == 2:
        service = "toggle"
    else:
        arg = argv[2].lower()
        if arg in ON:
            service = "turn_on"
        elif arg in OFF:
            service = "turn_off"
        else:
            print(f"unknown state {argv[2]!r}, expected on/off/1/0", file=sys.stderr)
            sys.exit(2)

    url = f"{config.HOMEASSISTANT_URL}/api/services/{domain}/{service}"
    headers = {
        "Authorization": f"Bearer {config.HOMEASSISTANT_TOKEN}",
        "Content-Type": "application/json",
    }
    r = requests.post(url, headers=headers, json={"entity_id": entity_id}, timeout=5)
    r.raise_for_status()
    print(f"{service} {entity_id} ok")


if __name__ == "__main__":
    main(sys.argv)
