import time
import threading
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI


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

    info("*** Running connectivity test\n")
    net.pingAll()

    info("*** Printing interface names (share with Rehan)\n")
    for iface in net.get("s1").intfNames():
        info(f"  Switch interface: {iface}\n")

    # Start all three traffic flows
    threads = [
        generate_http_traffic(net, duration=300),
        generate_db_traffic(net, duration=300),
        generate_bulk_transfer(net, duration=300),
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


if __name__ == "__main__":
    run_simulation(interactive=True)