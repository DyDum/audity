import ipaddress
from scapy.all import ARP, Ether, srp

def is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False

def scan_network_private(network_range: str) -> list:
    arp = ARP(pdst=network_range)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp

    result = srp(packet, timeout=2, verbose=0)[0]
    hosts = []
    for sent, received in result:
        ip = received.psrc
        if is_private_ip(ip):
            hosts.append({'ip': ip, 'mac': received.hwsrc})
    return hosts