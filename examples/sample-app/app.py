import argparse
import time
import urllib.error
import urllib.request


HEALTHY_RESPONSE = "VORTEX-HEALTHY"


def main():
    parser = argparse.ArgumentParser(description="Vortex HTTP resilience workload")

    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=2.0)

    args = parser.parse_args()

    if args.requests < 1 or args.timeout <= 0:
        parser.error("Requests and timeout must be positive")

    successful = 0
    failed = 0
    latencies = []

    print("HTTP resilience workload started.")
    print(f"Target: {args.url}")
    print(f"Requests: {args.requests}")
    print()

    for index in range(1, args.requests + 1):
        started = time.perf_counter()

        try:
            with urllib.request.urlopen(
                args.url,
                timeout=args.timeout
            ) as response:
                body = response.read().decode(
                    "utf-8",
                    errors="replace"
                ).strip()

                elapsed = (time.perf_counter() - started) * 1000

                if response.status == 200 and body == HEALTHY_RESPONSE:
                    successful += 1
                    latencies.append(elapsed)

                    print(
                        f"Request {index}/{args.requests}: "
                        f"PASSED | HTTP {response.status} | "
                        f"{elapsed:.2f} ms"
                    )
                else:
                    failed += 1

                    print(
                        f"Request {index}/{args.requests}: "
                        f"FAILED | Unexpected response | "
                        f"HTTP {response.status}"
                    )

        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            failed += 1
            elapsed = (time.perf_counter() - started) * 1000

            print(
                f"Request {index}/{args.requests}: "
                f"FAILED | {elapsed:.2f} ms | {exc}"
            )

    print()
    print("========== WORKLOAD SUMMARY ==========")
    print(f"Successful requests : {successful}")
    print(f"Failed requests     : {failed}")

    if latencies:
        average = sum(latencies) / len(latencies)
        print(f"Average latency     : {average:.2f} ms")
    else:
        print("Average latency     : N/A")

    print("======================================")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
