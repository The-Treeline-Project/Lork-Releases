"""Compatibility adapter for authenticated proxies sharing a gateway."""

import hashlib
import json
import runpy
from functools import lru_cache

from lork.proxy.models import Proxy

_original_key = Proxy.key.fget


@lru_cache(maxsize=262144)
def _authenticated_key(configuration: tuple) -> str:
    canonical = json.dumps(configuration, ensure_ascii=True, separators=(",", ":"))
    return "auth:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def proxy_key(proxy: Proxy) -> str:
    if proxy.username is None and proxy.password is None:
        return _original_key(proxy)
    return _authenticated_key((
        proxy.scheme.lower(),
        proxy.host.lower() if proxy.host else None,
        proxy.port,
        proxy.username,
        proxy.password,
    ))


def install() -> None:
    Proxy.key = property(proxy_key)


if __name__ == "__main__":
    install()
    print("Credential-specific proxy identity workaround enabled", flush=True)
    runpy.run_module("lork", run_name="__main__", alter_sys=True)
