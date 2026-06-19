#!/usr/bin/env python3
"""
Proxy updater – fast, strict timeouts, no hanging.
"""

import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

TEST_TIMEOUT = 5
TEST_URL = "http://google.com"

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
        except Exception as e:
            print(f"Source error: {e}")
    return list(proxies)

def test_proxy(proxy):
    try:
        # Only test latency – faster and more reliable
        start = time.time()
        resp = requests.get(TEST_URL, proxies={"http": proxy}, timeout=TEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        latency = (time.time() - start) * 1000

        ip = proxy.split('://')[1].split(':')[0]
        flag, country = get_country(ip)

        return {
            'proxy': proxy,
            'ip': ip,
            'country_flag': flag,
            'country': country,
            'latency_ms': round(latency, 1),
            'speed_mbps': 0.0,  # Skip speed test to avoid hanging
            'last_checked': datetime.now().isoformat()
        }
    except Exception as e:
        return None

def main():
    print("Fetching proxies...")
    proxies = fetch_proxies()
    print(f"Got {len(proxies)} raw proxies, testing...")

    # Limit to first 200 proxies to avoid timeout
    proxies = proxies[:200]
    results = []

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(test_proxy, p): p for p in proxies}
        for i, future in enumerate(as_completed(futures), 1):
            if i % 10 == 0:
                print(f"Tested {i}/{len(proxies)}...")
            result = future.result()
            if result:
                results.append(result)

    print(f"Found {len(results)} working proxies.")

    # Sort by latency (fastest first)
    results.sort(key=lambda x: x['latency_ms'])

    with open("proxies.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Saved {len(results)} proxies to proxies.json")

if __name__ == "__main__":
    main()
