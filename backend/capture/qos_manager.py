# backend/capture/qos_manager.py
import subprocess
import logging

logger = logging.getLogger(__name__)

def apply_qos_rule(interface: str, rule: dict):
    """
    Apply a tc qdisc HTB rule to an interface.
    rule = {
        "priority": int (1-5),
        "bandwidth_limit_kbps": int or None,
        "protocol": "TCP"|"UDP",
        "dst_port": int or None
    }
    """
    # Step 1: Add root qdisc if not already there (ignore error if exists)
    subprocess.run(
        ["tc", "qdisc", "add", "dev", interface, "root", "handle", "1:", "htb", "default", "30"],
        capture_output=True
    )

    # Step 2: Add root class
    subprocess.run(
        ["tc", "class", "add", "dev", interface, "parent", "1:", "classid", "1:1",
         "htb", "rate", "100mbit"],
        capture_output=True
    )

    # Step 3: Map priority to bandwidth ceiling
    priority = rule.get("priority", 3)
    bandwidth = rule.get("bandwidth_limit_kbps")
    if bandwidth:
        rate = f"{bandwidth}kbit"
    else:
        # Priority 1 gets 80mbit, priority 5 gets 10mbit
        rates = {1: "80mbit", 2: "60mbit", 3: "40mbit", 4: "20mbit", 5: "10mbit"}
        rate = rates.get(priority, "40mbit")

    class_id = f"1:{10 + priority}"
    subprocess.run(
        ["tc", "class", "add", "dev", interface, "parent", "1:1",
         "classid", class_id, "htb", "rate", rate, "ceil", "100mbit"],
        capture_output=True
    )

    # Step 4: Add filter to match traffic to this class
    protocol = rule.get("protocol", "TCP").lower()
    dst_port = rule.get("dst_port")

    if dst_port:
        proto_num = "6" if protocol == "tcp" else "17"
        result = subprocess.run(
            ["tc", "filter", "add", "dev", interface, "protocol", "ip",
             "parent", "1:0", "prio", str(priority), "u32",
             "match", "ip", "protocol", proto_num, "0xff",
             "match", "ip", "dport", str(dst_port), "0xffff",
             "flowid", class_id],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"tc filter failed: {result.stderr}")
        else:
            logger.info(f"QoS rule applied on {interface}: {protocol}:{dst_port} → {rate}")

def clear_qos(interface: str):
    """Remove all tc rules from an interface."""
    subprocess.run(
        ["tc", "qdisc", "del", "dev", interface, "root"],
        capture_output=True
    )
    logger.info(f"QoS cleared on {interface}")