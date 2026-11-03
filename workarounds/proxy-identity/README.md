# Authenticated proxies sharing a gateway

This is an **opt-in compatibility workaround for v0.0.5-testing** (application
commit `0c09cab`). It does not modify the default image or Compose example.
A native fix in Lork's core is preferable; remove this adapter once a release
provides credential-specific proxy identity.

## Problem

Some proxy services expose multiple independent credentials or sessions through
the same gateway. For example, these two synthetic entries are distinct routes:

```text
http://account-a:password-a@gateway.example:8080
http://account-b:password-b@gateway.example:8080
```

In the affected release, both `Proxy.key` values are `gateway.example:8080`.
Statistics and cooldowns therefore collide: marking the first route rate-limited
also makes the second route unusable. A large configured pool can appear to have
one proxy and become entirely unavailable after one rate limit.

## Behavior

The adapter replaces `Proxy.key` before starting the existing application.
Authenticated keys are `auth:` followed by SHA-256 of an unambiguous JSON tuple:
scheme, host, port, username and password. Host and scheme are case-normalized;
credentials remain case-sensitive. Keys contain no plaintext credentials.
Connection URLs, relay configuration and authentication behavior are unchanged.
Unauthenticated and LOCAL routes retain their existing keys.

The hash cache is bounded to avoid unlimited growth. Upstream still scans the
configured pool; this adapter does not change pool-selection complexity.

## Enable

From the repository root, first prepare `config.yaml`, `proxies.txt` and
`docker-compose.yml` as described in the main README. Back up your proxy statistics
file and configuration before switching.

```sh
docker compose -f docker-compose.yml \
  -f workarounds/proxy-identity/compose.override.yaml up -d --build
curl -fsS http://127.0.0.1:5090/api/v1/health
```

The build runs regression tests without a browser, network requests or real
credentials. Its base is pinned to the tested multi-architecture image digest.
Runtime verification was performed on `linux/amd64`; other architectures still
need validation. A new base release requires rebuilding and rerunning the tests.

Existing authenticated statistics use the old shared key. They remain in the
statistics file but are not attributed to any new credential-specific key:
there is no reliable way to assign an aggregated failure to one credential.
Authenticated statistics and cooldowns start afresh under their new keys.
In-flight sessions are interrupted when Compose recreates the container.

## Regression checks

Run the checks explicitly after building:

```sh
docker run --rm --network none --entrypoint /opt/venv/bin/python3 \
  lork-proxy-identity:local -m test_proxy_identity_compat
```

To reproduce the collision in the pinned upstream release, run the same tests
with the adapter disabled. Several identity and cooldown assertions are expected
to fail:

```sh
docker run --rm --network none --entrypoint /opt/venv/bin/python3 \
  lork-proxy-identity:local -m test_proxy_identity_compat --unpatched
```

Tests cover distinct credentials, deterministic identities, scheme/host/port,
credential case and delimiter boundaries, unchanged URLs, legacy unauthenticated
keys, independent cooldowns and concurrent reservations.

## Rollback

Run Compose without the optional override:

```sh
docker compose -f docker-compose.yml up -d
```

This selects the image in your original Compose file. The historical shared-key
statistics were preserved, so their old cooldown may still apply after rollback.
Keep the statistics backup rather than attempting to merge credential-specific
counters back into the shared entry.

## Native fix

The application sources are not present in this release repository, so this
contribution cannot change the core implementation directly. The desired core
invariant is that credentials identifying independent routes must be included
in the statistics/cooldown identity, while transport URLs remain unchanged.
The adapter and regression tests provide an executable reference for that change.
The production implementation should also document statistics migration and
assess key consumers such as API output, monitoring labels and reservations.
