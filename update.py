#!/usr/bin/env python3
"""
Proxy updater – fetches, tests, writes proxies.json.
Runs in GitHub Actions.
"""

import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

TEST_TIMEOUT = 5
TEST_URL = "http://google.com"
SPEED_URL = "http://speedtest.tele2.net/1MB.zip"

_country_cache = {}
def get_country(ip):
    if ip in _country_cache:
        return _country_cache[ip]
    try:
        resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            country = data.get('country', 'Unknown')
            code = data.get('country', '').upper()
            flag = ''
            if len(code) == 2:
                flag = chr(ord(code[0]) + 0x1F1E6 - ord('A')) + chr(ord(code[1]) + 0x1F1E6 - ord('A'))
            _country_cache[ip] = (flag, country)
            return _country_cache[ip]
    except:
        pass
    _country_cache[ip] = ('', 'Unknown')
    return _country_cache[ip]

def fetch_proxies():
    sources = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://proxy-list.download/api/v1/get?type=http",
    ]
    proxies = set()
    for url in sources:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip()
                    if ':' in line:
                        parts = line.split(':')
                        if len(parts) == 2 and parts[1].isdigit():
                            proxies.add(f"http://{parts[0]}:{parts[1]}")
        except:
            pass
    return list(proxies)

def test_proxy(proxy):
    try:
        start = time.time()
        resp = requests.get(TEST_URL, proxies={"http": proxy}, timeout=TEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        latency = (time.time() - start) * 1000

        start = time.time()
        resp = requests.get(SPEED_URL, proxies={"http": proxy}, timeout=TEST_TIMEOUT)
        if resp.status_code == 200 and len(resp.content) > 0:
            elapsed = time.time() - start
            speed_mbps = (len(resp.content) * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
        else:
            speed_mbps = 0.0

        ip = proxy.split('://')[1].split(':')[0]
        flag, country = get_country(ip)

        return {
            'proxy': proxy,
            'ip': ip,
            'country_flag': flag,
            'country': country,
            'latency_ms': round(latency, 1),
            'speed_mbps': round(speed_mbps, 2),
            'last_checked': datetime.now().isoformat()
        }
    except:
        return None

def main():
    print("Fetching proxies...")
    proxies = fetch_proxies()
    print(f"Got {len(proxies)} raw proxies, testing...")
    results = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(test_proxy, p): p for p in proxies}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    print(f"Found {len(results)} working proxies.")
    with open("proxies.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
