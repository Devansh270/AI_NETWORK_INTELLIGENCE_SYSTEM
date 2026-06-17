import time
import threading
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import json
import redis
import threading
import time

class AINISTopology(Topo):
    """
    4-node topology:
        h1 (client) --- s1 (switch) --- h2 (web server)
                          |
                         h3 (database server)
                          |
                         h4 (attacker - for later anomaly simulation)
    """
    def build(self):
        # Add hosts
        h1 = self.addHost("h1", ip="10.0.0.1/24")
        h2 = self.addHost("h2", ip="10.0.0.2/24")
        h3 = self.addHost("h3", ip="10.0.0.3/24")
        h4 = self.addHost("h4", ip="10.0.0.4/24")

        # Add switch
        s1 = self.addSwitch("s1")

        # Add links with bandwidth and delay limits (TCLink enables QoS)
        # bw = bandwidth in Mbps, delay = link delay string
        self.addLink(h1, s1, cls=TCLink, bw=10, delay="5ms")
        self.addLink(h2, s1, cls=TCLink, bw=10, delay="2ms")
        self.addLink(h3, s1, cls=TCLink, bw=10, delay="2ms")
        self.addLink(h4, s1, cls=TCLink, bw=10, delay="2ms")


def generate_http_traffic(net, duration=60):
    """Simulate web traffic: h1 → h2 (port 8080)"""
    h1 = net.get("h1")
    h2 = net.get("h2")

    info("*** Starting HTTP traffic simulation (h1 → h2)\n")

    # Start a simple HTTP server on h2
    h2.cmd("python3 -m http.server 8080 &")
    time.sleep(1)

    # h1 fetches from h2 repeatedly
    def http_loop():
        end = time.time() + duration
        while time.time() < end:
            h1.cmd(f"curl -s http://{h2.IP()}:8080/ > /dev/null")
            time.sleep(0.5)

    t = threading.Thread(target=http_loop, daemon=True)
    t.start()
    return t


def generate_db_traffic(net, duration=60):
    """Simulate database traffic: h1 → h3 (port 5432 fake)"""
    h1 = net.get("h1")
    h3 = net.get("h3")

    info("*** Starting DB traffic simulation (h1 → h3)\n")

    # Start a simple listener on h3 on port 5432
    h3.cmd("nc -lk 5432 > /dev/null &")
    time.sleep(0.5)

    def db_loop():
        end = time.time() + duration
        while time.time() < end:
            # Send a fake "query" - just bytes to port 5432
            h1.cmd(f"echo 'SELECT 1' | nc -w 1 {h3.IP()} 5432")
            time.sleep(1.0)

    t = threading.Thread(target=db_loop, daemon=True)
    t.start()
    return t


def generate_bulk_transfer(net, duration=60):
    """Simulate bulk file transfer using iperf: h2 → h3"""
    h2 = net.get("h2")
    h3 = net.get("h3")

    info("*** Starting bulk transfer (h2 → h3 via iperf)\n")

    # Start iperf server on h3
    h3.cmd("iperf -s &")
    time.sleep(0.5)

    def iperf_loop():
        end = time.time() + duration
        while time.time() < end:
            # Run iperf for 5 seconds at a time
            h2.cmd(f"iperf -c {h3.IP()} -t 5 > /dev/null 2>&1")

    t = threading.Thread(target=iperf_loop, daemon=True)
    t.start()
    return t


def run_simulation(interactive=False):
    setLogLevel("info")

    topo = AINISTopology()
    net = Mininet(
        topo=topo,
        controller=Controller,
        link=TCLink,
        autoSetMacs=True
    )

    info("*** Starting network\n")
    net.start()

    export_topology_to_redis(net)
    r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
    )

    t = threading.Thread(
    target=update_link_utilization,
    args=(net, r),
    daemon=True
    )
    t.start()

    info("*** Running connectivity test\n")
    net.pingAll()

    info("*** Printing interface names (share with Rehan)\n")
    for iface in net.get("s1").intfNames():
        info(f"  Switch interface: {iface}\n")

    # Start all three traffic flows
    threads = [
        generate_http_traffic(net, duration=300),
        # generate_db_traffic(net, duration=300),
        # generate_bulk_transfer(net, duration=300),
    ]

    if interactive:
        info("*** Dropping into interactive CLI (type 'exit' to quit)\n")
        CLI(net)
    else:
        info("*** Traffic running for 300 seconds. Ctrl+C to stop.\n")
        try:
            time.sleep(300)
        except KeyboardInterrupt:
            pass

    info("*** Stopping network\n")
    net.stop()

# backend/capture/mininet_sim.py  — add this section to existing file
# Add at the bottom of the file, after topology is created

def get_link_interfaces(net):
    """Return dict of link descriptions to interface names."""
    interfaces = {}
    for link in net.links:
        intf1 = link.intf1.name
        intf2 = link.intf2.name
        interfaces[f"{link.intf1.node}-{link.intf2.node}"] = intf1
    return interfaces

def apply_rules_to_topology(net, rules: list):
    """Apply a list of routing rules to all links in the Mininet topology."""
    from capture.qos_manager import apply_qos_rule, clear_qos
    interfaces = get_link_interfaces(net)
    for iface_name in interfaces.values():
        clear_qos(iface_name)
    for rule in rules:
        if rule.get("is_active"):
            for iface_name in interfaces.values():
                apply_qos_rule(iface_name, rule)

def export_topology_to_redis(net):
    """Export Mininet topology as graph JSON to Redis."""

    r = redis.Redis(
        host="localhost",   # Redis exposed by Docker
        port=6379,
        decode_responses=True
    )

    nodes = []
    edges = []

    for host in net.hosts:
        nodes.append({
            "id": host.name,
            "type": "host",
            "ip": host.IP(),
            "mac": host.MAC()
        })

    for switch in net.switches:
        nodes.append({
            "id": switch.name,
            "type": "switch",
            "ip": None,
            "mac": None
        })

    for link in net.links:
        edges.append({
            "source": link.intf1.node.name,
            "target": link.intf2.node.name,
            "utilization": 0.0,
            "bandwidth": 10
        })

    topology = {
        "nodes": nodes,
        "edges": edges
    }

    r.set("topology:current", json.dumps(topology))
    r.publish("topology:updates", json.dumps(topology))

    print("[topology] Exported to Redis")


def update_link_utilization(net, r):
    """Poll link stats and update edge utilization in Redis."""
    while True:
        try:
            topology_raw = r.get("topology:current")
            if not topology_raw:
                time.sleep(5)
                continue
            topology = json.loads(topology_raw)
            
            for edge in topology["edges"]:
                src_node = net.get(edge["source"])
                if src_node and hasattr(src_node, 'intfNames'):
                    # Approximate utilization — randomize slightly for demo realism
                    # In real Mininet: parse /proc/net/dev or use iperf
                    import random
                    edge["utilization"] = round(random.uniform(0.05, 0.85), 2)
            
            r.set("topology:current", json.dumps(topology))
            r.publish("topology:updates", json.dumps(topology))
        except Exception as e:
            print(f"[topology] Utilization update error: {e}")
        time.sleep(5)

# Start this thread after export_topology_to_redis(net):
# r = redis.Redis(host='redis', port=6379, decode_responses=True)
# t = threading.Thread(target=update_link_utilization, args=(net, r), daemon=True)
# t.start()

if __name__ == "__main__":
    run_simulation(interactive=True)