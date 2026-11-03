import asyncio
import hashlib
import sys
import tempfile
import unittest

from lork.proxy.dispenser import ProxyDispenser
from lork.proxy.distributor import ProxyDistributor
from lork.proxy.models import Proxy
from lork.proxy.stats import ProxyStatsStore

from proxy_identity_compat import install

_original_key = Proxy.key.fget

if "--unpatched" in sys.argv:
    sys.argv.remove("--unpatched")
else:
    install()


def proxy(username="synthetic-a", password="synthetic-secret", **kwargs):
    result = Proxy(
        host=kwargs.pop("host", "gateway.example"),
        port=kwargs.pop("port", 8080),
        username=username,
        password=password,
        **kwargs,
    )
    result.original_uri_sha256 = hashlib.sha256(result.full_url.encode()).hexdigest()
    return result


class IdentityTests(unittest.TestCase):
    def test_distinct_credentials_have_distinct_keys(self):
        self.assertNotEqual(proxy().key, proxy("synthetic-b").key)
        self.assertNotEqual(proxy().key, proxy(password="different").key)

    def test_same_configuration_has_stable_identity(self):
        self.assertEqual(proxy().key, proxy().key)
        self.assertEqual(proxy().key, proxy(host="GATEWAY.EXAMPLE", scheme="HTTP").key)

    def test_scheme_host_and_port_are_part_of_identity(self):
        for options in ({"scheme": "socks5"}, {"host": "other.example"}, {"port": 8081}):
            with self.subTest(options=options):
                self.assertNotEqual(proxy().key, proxy(**options).key)

    def test_credential_case_and_boundaries_are_preserved(self):
        self.assertNotEqual(proxy("A", "b").key, proxy("a", "b").key)
        self.assertNotEqual(proxy("a", "B").key, proxy("a", "b").key)
        self.assertNotEqual(proxy("a:b", "c").key, proxy("a", "b:c").key)

    def test_urls_are_unchanged_and_keys_do_not_contain_credentials(self):
        p = proxy()
        self.assertEqual(p.url, "gateway.example:8080")
        self.assertEqual(p.full_url, "http://synthetic-a:synthetic-secret@gateway.example:8080")
        self.assertNotIn("synthetic-a", p.key)
        self.assertNotIn("synthetic-secret", p.key)

    def test_unauthenticated_and_local_keys_keep_upstream_behavior(self):
        for p in (Proxy("gateway.example", 8080), Proxy(None, None)):
            self.assertEqual(p.key, _original_key(p))


class AvailabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.stats = ProxyStatsStore(self.directory.name + "/stats.json")
        self.distributor = ProxyDistributor(None, self.stats)
        self.a, self.b = proxy(), proxy("synthetic-b")
        self.pool = ProxyDispenser([self.a, self.b], self.distributor)

    async def asyncTearDown(self):
        self.directory.cleanup()

    async def test_cooldown_is_isolated(self):
        self.distributor.mark_rate_limited(self.a)
        self.assertFalse(self.distributor.is_proxy_usable(self.a))
        self.assertTrue(self.distributor.is_proxy_usable(self.b))
        availability = await self.pool.authentication_availability()
        self.assertEqual(availability["available"], 1)
        lease = await asyncio.wait_for(self.pool.acquire_auth_proxy(), 2)
        try:
            self.assertEqual(lease.proxy.key, self.b.key)
        finally:
            self.pool.release_auth_proxy(lease, cleanup_confirmed=True)

    async def test_two_credentials_can_be_reserved_concurrently(self):
        first = await asyncio.wait_for(self.pool.acquire_auth_proxy(), 2)
        try:
            second = await asyncio.wait_for(self.pool.acquire_auth_proxy(), 2)
            try:
                self.assertNotEqual(first.route_id, second.route_id)
                self.assertNotEqual(first.proxy.key, second.proxy.key)
            finally:
                self.pool.release_auth_proxy(second, cleanup_confirmed=True)
        finally:
            self.pool.release_auth_proxy(first, cleanup_confirmed=True)


if __name__ == "__main__":
    unittest.main()
