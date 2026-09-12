import socket
import threading
import psutil
import ipaddress
import time

from config import get

class NetworkScanner:
    def __init__(self, port=None, timeout=None):
        self.port = port if port is not None else get('network', 'discovery_port')
        self.timeout = timeout if timeout is not None else get('scanner', 'timeout')
        self.active_hosts = []
        self.stop_scan_flag = False

    def stop_scan(self):
        """
        Signal to stop the current scan.
        """
        self.stop_scan_flag = True

    def _default_route_ip(self):
        """Return the local IP used to reach the internet (the active connection, usually Wi-Fi)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None

    def _is_wifi(self, name):
        n = name.lower()
        return any(k in n for k in ('wlan', 'wifi', 'wl', 'wireless', 'airport', '无线', 'wlp'))

    def _is_vpn_interface(self, name):
        n = name.lower()
        return any(k in n for k in ('utun', 'tun', 'tap', 'ppp', 'wg', 'docker', 'vbox', 'vmnet', 'virbr', 'bridge'))

    def _is_real_lan_ip(self, ip_str):
        """Only accept real private-LAN addresses (excludes VPN fake ranges like 198.18.0.0/15)."""
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        return any(ip in net for net in (
            ipaddress.ip_network('10.0.0.0/8'),
            ipaddress.ip_network('172.16.0.0/12'),
            ipaddress.ip_network('192.168.0.0/16'),
        ))

    def _best_local_ip(self):
        """Pick the most likely LAN IP: real private address, non-VPN, default-route preferred."""
        default_ip = self._default_route_ip()
        candidates = []
        for name, addrs in psutil.net_if_addrs().items():
            if self._is_vpn_interface(name):
                continue
            for addr in addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip = addr.address
                if not self._is_real_lan_ip(ip):
                    continue
                candidates.append((name, ip, ip == default_ip))
        if not candidates:
            return default_ip or "127.0.0.1"
        candidates.sort(key=lambda c: (
            0 if c[2] else 1,                  # default-route IP preferred
            0 if self._is_wifi(c[0]) else 1,   # Wi-Fi preferred
            c[0],
        ))
        return candidates[0][1]

    def get_interfaces(self):
        """
        Get available LAN interfaces (real private IPv4, non-VPN). The best one is
        marked 'is_default' and sorted first for the UI to auto-select.
        Returns a list of dicts: [{'name','ip','cidr','is_default'}, ...]
        """
        best_ip = self._best_local_ip()
        interfaces_list = []
        for interface_name, addrs in psutil.net_if_addrs().items():
            if self._is_vpn_interface(interface_name):
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    netmask = addr.netmask
                    if ip == '127.0.0.1':
                        continue
                    if not self._is_real_lan_ip(ip):
                        continue
                    if netmask:
                        try:
                            network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                            interfaces_list.append({
                                'name': interface_name,
                                'ip': ip,
                                'cidr': str(network),
                                'is_default': (ip == best_ip),
                            })
                        except ValueError:
                            pass

        # Default route first, then Wi-Fi-looking names, then the rest.
        interfaces_list.sort(key=lambda item: (
            0 if item['is_default'] else 1,
            0 if self._is_wifi(item['name']) else 1,
            item['name'],
        ))
        return interfaces_list

    def get_local_ip_and_network(self):
        """
        Get the local LAN IP address and the network (CIDR).
        """
        local_ip = self._best_local_ip()

        network_cidr = None
        # Try to match found local_ip with interfaces
        interfaces = self.get_interfaces()
        for iface in interfaces:
            if iface['ip'] == local_ip:
                network_cidr = iface['cidr']
                break

        return local_ip, network_cidr

    def scan_host(self, ip):
        """
        Try to connect to the host on the specific port.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout) # Short timeout for speed
        try:
            result = s.connect_ex((str(ip), self.port))
            if result == 0:
                # Connection successful
                try:
                    # Optional: Handshake to verify it's our chat app
                    s.send(b"CHAT_DISCOVERY")
                    response = s.recv(1024)
                    if b"CHAT_ACK" in response:
                        # Extract nickname if present: CHAT_ACK:Nickname
                        nickname = "Unknown"
                        try:
                            decoded = response.decode('utf-8')
                            if ":" in decoded:
                                nickname = decoded.split(":", 1)[1]
                        except:
                            pass
                            
                        self.active_hosts.append({'ip': str(ip), 'nickname': nickname})
                except:
                    # Even if handshake fails, if port is open, we might list it
                    # But we prefer only those who speak our protocol
                    # self.active_hosts.append({'ip': str(ip), 'nickname': 'Unknown'})
                    pass
            s.close()
        except:
            pass

    def scan_network(self, target_cidr=None):
        """
        Scan the network for active hosts.
        If target_cidr is provided, scan that network.
        Otherwise, scan the default detected network.
        """
        local_ip = "127.0.0.1"
        network_cidr = target_cidr

        # Determine all local IPs to exclude them
        local_ips = set()
        for interface in self.get_interfaces():
            local_ips.add(interface['ip'])

        if not network_cidr:
            local_ip, network_cidr = self.get_local_ip_and_network()
        
        if not network_cidr:
            print("Could not determine network.")
            return []

        print(f"Scanning network: {network_cidr}")
        
        self.stop_scan_flag = False
        self.active_hosts = []
        try:
            network = ipaddress.IPv4Network(network_cidr)
        except ValueError:
             print(f"Invalid CIDR: {network_cidr}")
             return []

        threads = []

        for ip in network.hosts():
            if self.stop_scan_flag:
                break
            
            ip_str = str(ip)
            
            # Exclude local IPs
            if ip_str in local_ips:
                continue

            t = threading.Thread(target=self.scan_host, args=(ip,))
            threads.append(t)
            t.start()
            
            # Batch threads to avoid "Too many open files"
            if len(threads) > 50:
                for t in threads:
                    t.join()
                threads = []
                
        # Wait for remaining threads
        for t in threads:
            t.join()

        return self.active_hosts

if __name__ == "__main__":
    scanner = NetworkScanner()
    print("Interfaces:", scanner.get_interfaces())
    hosts = scanner.scan_network()
    print(f"Active hosts found: {hosts}")
