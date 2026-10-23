# Lork metrics and Grafana examples

Lork exposes Prometheus text metrics at **`GET /metrics`**, on its existing API port
(normally `5090`). Two importable Grafana dashboards are included:

- [Overview](grafana/dashboards/lork-overview.json): health, requests, authentication,
  Cion tokens, browser capacity, proxy availability and relay traffic.
- [Browsers and memory](grafana/dashboards/lork-browser-memory.json): Chrome process
  cleanup, Python and container memory, CPU, file descriptors, OOM events and work
  in progress.

Every dashboard has **Prometheus**, **Job** and **Instance** selectors. Ratios and
percentiles are computed separately for each selected instance. Credentials,
cookies, tokens, usernames and proxy addresses are not metric labels.

These templates build on the monitoring coverage proposed by **unseenmagik** in
[Lork-Releases PR #2](https://github.com/The-Treeline-Project/Lork-Releases/pull/2),
using native metrics in place of its exporters and log parsing.
No mtail, JSON exporter, blackbox exporter, cAdvisor, Docker socket or external
restart watchdog is needed. The optional stack starts only when explicitly run.

## Use the bundled stack

These examples require a Lork image with native `/metrics` support. Older images
that return HTTP 404 at that endpoint need a compatible release before these
dashboards can show data. Downloading these examples does not update Lork itself.

Start Lork first. From the repository root, find its Docker network and check
that metrics are available:

```bash
docker inspect "$(docker compose ps -q lork)" --format '{{json .NetworkSettings.Networks}}'
curl -fsS http://127.0.0.1:5090/metrics
```

Then enter the monitoring directory:

```bash
cd monitoring
export LORK_NETWORK=lork-releases_default
docker compose up -d
```

Before starting, set `LORK_NETWORK` to the network from the inspection output if
it differs. `lork-releases_default` is an example for a checkout named
`Lork-Releases`; the directory name or Compose project name can change it.
Keep the variable exported for later commands, or save `LORK_NETWORK=<network>`
in `monitoring/.env`. The scraper reaches `lork:5090` on that network. If the
service name or internal API port differs, edit `prometheus/prometheus.yml` first.

- Grafana: **http://127.0.0.1:3001**, initial login `admin` / `admin`; Grafana asks
  for a new password. Open the **Lork** folder to see both dashboards.
- Prometheus: **http://127.0.0.1:9091/targets**; the `lork` target should be **UP**.
- Override host ports with `GRAFANA_PORT` and `PROMETHEUS_PORT` when needed.
- Images are pinned to verified Prometheus **3.15.0** and Grafana **12.4.12**
  digests. The Prometheus volume retains 30 days of metrics; the Grafana volume
  retains users and settings.

Both ports bind to loopback. For a remote host, use an SSH tunnel:

```bash
ssh -L 3001:127.0.0.1:3001 -L 9091:127.0.0.1:9091 user@lork-host
```

Use `docker compose down` **from `monitoring/`** to stop this stack; it does not
stop Lork. Volumes are retained unless you explicitly remove them.

## Use existing Prometheus or vmagent and Grafana

1. Copy the job in [scrape-jobs.yml](scrape-jobs.yml) into the existing
   `scrape_configs` list. Choose an address reachable **from the scraper**:
   a container on Lork's network can use `lork:5090`; a scraper running on the host
   can use Lork's published `127.0.0.1:<port>`. Container loopback refers to that
   container. A host port bound only to loopback is not reachable through a Docker
   bridge's `host.docker.internal` address.
2. Keep distinct target addresses or `instance` labels for different Lork
   deployments. Validate the configuration with `promtool check config` or
   `vmagent -dryRun -promscrape.config=<path>`, then reload your scraper using its
   normal procedure.
3. In Grafana, choose **Dashboards → New → Import**, upload either JSON file, then
   select your Prometheus-compatible datasource in its **Prometheus** dropdown.
   Set that datasource's scrape interval to match your scraper (15s in the sample).
   The dashboards use `$__rate_interval` so rate windows adapt to the selected range.
4. Optionally load [alerts.yml](alerts.yml) under Prometheus `rule_files`, or use
   `vmalert` for VictoriaMetrics. vmagent does not evaluate alert rules. The bundled
   stack loads these rules but does not configure an Alertmanager or notifications.

The `LorkDown` and `LorkMetricsMissing` rules select `job="lork"`. Update those two
selectors if you rename the scrape job. Other rules select native `lork_*` metrics
and preserve `job` and `instance`. Missing scrape configuration itself cannot be
detected without a separate inventory of expected targets.

## Metric meanings

| Metric family | Meaning |
|---|---|
| `lork_http_requests_total`, `lork_http_request_duration_seconds`, `lork_http_requests_in_progress` | Completed requests by fixed endpoint/method/status, duration histogram and current request count. `/metrics` does not count itself; unknown paths share `other`. |
| `lork_auth_results_total`, `lork_auth_duration_seconds` | Authentication request outcomes and duration by `SUCCESS`, `INVALID`, `BANNED`, `TIMEOUT`, `ERROR`, `CANCELLED`. Internal retries are not extra endpoint outcomes. |
| `lork_cion_results_total`, `lork_cion_duration_seconds` | Batch outcomes/duration by `SUCCESS`, `EMPTY`, `BUSY`, `ERROR`, `CANCELLED`. |
| `lork_cion_tokens_total{action}` | Tokens actually returned, separated into `create` and `activate`. |
| `lork_uptime_seconds`, `lork_health_status` | App uptime and current health: 1 healthy, 0 degraded. Scrape reachability comes from Prometheus `up`. |
| `lork_browser_slots{state}` | Mutually exclusive auth-pool counts: `available`, `busy`, `quarantined`. Their sum is the pool size. |
| `lork_browser_instances{role}`, `lork_browser_running{role}`, `lork_browser_cleanup_failures{role}` | Configured logical slots, slots holding a Chrome driver and currently fenced slots, split into auth/Cion. Driver presence does not prove the OS process is healthy; compare Chrome process counts. Cleanup failures are a gauge, not a lifetime counter. |
| `lork_cion_busy` | Whether a Cion batch is in progress. |
| `lork_proxies_configured`, `lork_proxies_available`, `lork_proxies_queueable_in_flight` | Configured, currently usable and temporarily leased queueable routes. Availability includes backoff, cooldown, failure/usage limits and cleanup quarantine. |
| `lork_proxies_unavailable{reason}` | Bounded reasons for route unavailability. One route may have several reasons: do not sum these as a route total. |
| `lork_proxy_results{result}` | **Gauge** snapshot of aggregate persisted proxy successes/failures. State can be replaced/reset; never use `rate()`/`increase()` on it. |
| `lork_proxy_stats_valid` | Whether persisted success/failure counts are valid. Invalid outcome aggregates are omitted, while the rest of `/metrics` remains available. |
| `lork_relay_connections_total`, `lork_relay_connections_active`, `lork_relay_failures_total`, `lork_relay_bytes_total{direction}` | Owned relay connection counters, current open connections, failures and bytes up/down. They exclude traffic outside these relays. |
| `lork_process_resident_memory_bytes`, `lork_process_cpu_seconds_total`, `lork_process_open_fds` | Python process RSS, CPU time and open descriptors. |
| `lork_chrome_processes{state}`, `lork_chrome_resident_memory_bytes` | Chrome processes attributable to this Lork instance by parentage or ownership token, counted by running/zombie, plus summed live Chrome RSS. |
| `lork_container_memory_current_bytes`, `lork_container_memory_limit_bytes` | Linux cgroup v2 charged memory and finite limit. The limit is omitted for unlimited containers. |
| `lork_container_memory_anon_bytes`, `lork_container_memory_file_bytes`, `lork_container_memory_shmem_bytes` | cgroup memory breakdown. Shared memory is included in file memory; do not sum all three. |
| `lork_container_cpu_usage_seconds_total`, `lork_container_memory_events_total{event}` | cgroup CPU time and kernel memory-pressure/OOM counters. |

Duration histograms expose `_bucket`, `_sum` and `_count` samples. Counters reset
when their owner restarts; `rate()` and `increase()` account for resets between
observed samples. Data lost between scrapes cannot be recovered.
The HTTP counter uses status `499` for cancelled requests; this describes the
cancelled operation and does not mean Lork sent an HTTP 499 response.

Process, Chrome and cgroup values describe different scopes. Unrelated Chrome
sessions are excluded; an orphan zombie with neither attributable parentage nor a
readable ownership token cannot be identified as Lork's. Chrome RSS can count
shared pages multiple times; it is not unique physical RAM. Container memory also
includes reclaimable file cache, so memory remaining after Chrome exits does not
by itself prove a browser leak. Compare the process counts, anonymous memory and
file/cache panels. CPU charts use **cores**, where 1 is one fully utilized core.

Unavailable resource measurements are omitted rather than reported as zero.
Container metrics require readable Linux cgroup v2 files; they may be absent
outside a suitable container. On a host they describe the process's systemd scope
or other cgroup, rather than a Docker container. An unlimited memory limit or idle histogram can
legitimately show **No data**. A new deployment needs at least two scrapes before
rates appear. Auth success percentages include INVALID/BANNED outcomes and exclude
cancellation; they are not a pure server-reliability measure.

## Verify configurations, alerts and dashboards

From `monitoring/`, validate Compose and Prometheus config/rules:

```bash
docker compose config --quiet
docker compose run --rm --no-deps --entrypoint /bin/promtool prometheus check config /etc/prometheus/prometheus.yml
docker run --rm --network none -v "$PWD:/monitoring:ro" \
  --entrypoint /bin/promtool \
  prom/prometheus:v3.15.0@sha256:efd719c99d83b060d9daefdcf00360461adf279f45ef5391f8d111892118753e \
  test rules /monitoring/tests/alerts.test.yml
```

The rule tests cover all-failure traffic without a success series, independent
instances, low traffic, healthy idle operation, queueable proxies, cleanup fencing,
missing/unlimited memory limits, Cion errors, OOM kills and zombies.

With the stack running, check the live target, native metric query and provisioned
dashboards:

```bash
curl -fsS 'http://127.0.0.1:9091/api/v1/targets'
curl -fsSG 'http://127.0.0.1:9091/api/v1/query' \
  --data-urlencode 'query=lork_health_status{job="lork"}'
curl -fsS 'http://127.0.0.1:3001/api/health'
```

Expect an **UP** target, a successful Prometheus query with the intended instance,
and Grafana reporting a healthy database. Open both dashboards and select the
target; inspect any panel error through **Inspect → Query**. A passing JSON parse
alone does not verify PromQL or datasource access. Synthetic workloads can verify
outcome panels without submitting real account credentials. Finite container limits
are needed to verify memory-percentage panels.
