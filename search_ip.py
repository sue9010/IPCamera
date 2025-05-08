# ip_scanner.py
import socket
import concurrent.futures
import psutil

def check_port(ip, port, timeout=0.5):
    """IP와 포트가 연결 가능한지 확인"""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except:
        return False

def get_local_subnet_ips():
    """현재 PC의 인터페이스에서 유추 가능한 서브넷 대역 내 모든 IP 반환"""
    candidates = set()
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                try:
                    base = ip.rsplit('.', 1)[0]
                    for i in range(1, 255):
                        candidates.add(f"{base}.{i}")
                except:
                    continue
    return sorted(candidates)

def scan_thermal_hosts():
    print("[Scan] Searching all local subnet devices on port 60110...")
    thermal_hosts = []
    all_ips = get_local_subnet_ips()

    def check(ip):
        if check_port(ip, 60110):
            return ip
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        results = executor.map(check, all_ips)

    print("\n[Thermal TCP Devices]")
    for ip in results:
        if ip:
            thermal_hosts.append(ip)
            print(f" - {ip}")

if __name__ == "__main__":
    scan_thermal_hosts()