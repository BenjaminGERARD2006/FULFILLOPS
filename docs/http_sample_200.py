import csv
import math
import time
from datetime import datetime, timezone
from urllib.request import urlopen
from urllib.error import HTTPError

URL = "http://fulfillops-api.fulfillops.svc.cluster.local:8000/api/v1/catalog"
SAMPLES = 200
results = []

for i in range(SAMPLES):
    started = time.perf_counter()
    status = 0

    try:
        with urlopen(URL, timeout=5) as response:
            status = response.status
            response.read()
    except HTTPError as error:
        status = error.code
    except Exception:
        status = 0

    latency = (time.perf_counter() - started) * 1000

    results.append({
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "http_status": status,
        "latency_ms": round(latency, 3)
    })

    time.sleep(0.05)

with open("/tmp/http_samples.csv", "w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

successful = sorted(
    row["latency_ms"] for row in results
    if row["http_status"] == 200
)

p95 = successful[math.ceil(0.95 * len(successful)) - 1] if successful else 0

print(f"Total samples: {len(results)}")
print(f"Successful requests: {len(successful)}")
print(f"Failed requests: {len(results) - len(successful)}")
print(f"Success rate: {len(successful) / len(results) * 100:.2f}%")
print(f"Observed p95 latency: {p95:.3f} ms")
