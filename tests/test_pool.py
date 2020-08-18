import datetime
import unittest

from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock
from pyfreenas import Machine

# from pyfreenas.disk import Disk, DiskType
from pyfreenas.pool import Pool, PoolStatus, PoolScanState
from tests.fakes.fakeserver import (
    FreeNASServer,
    TDiskQueryResult,
    TDiskTemperaturesResult,
    TPoolQueryResult,
    TVmQueryResult,
)
from typing import (
    Any,
    Dict,
    List,
    Union,
)


class TestPool(IsolatedAsyncioTestCase):
    _server: FreeNASServer
    _machine: Machine

    def setUp(self):
        self._server = FreeNASServer()
        self._server.register_method_handler(
            "disk.query", lambda *args: [],
        )
        self._server.register_method_handler(
            "vm.query", lambda *args: [],
        )

    async def asyncSetUp(self):
        self._machine = await Machine.create(
            self._server.host,
            username=self._server.username,
            password=self._server.password,
            secure=False,
        )

    async def asyncTearDown(self):
        await self._machine.close()
        await self._server.stop()

    async def test_pool_data_interpretation(self) -> None:
        ENCRYPT = 0
        GUID = "1234ABCD"
        ID = 100
        IS_DECRYPTED = True
        NAME = "testpool"
        self._server.register_method_handler(
            "pool.query",
            lambda *args: [
                {
                    "encrypt": ENCRYPT,
                    "encryptkey": "",
                    "guid": GUID,
                    "id": ID,
                    "is_decrypted": IS_DECRYPTED,
                    "name": NAME,
                    "scan": {
                        "bytes_issued": 90546145402880,
                        "bytes_processed": 90902589915136,
                        "bytes_to_process": 90546369048576,
                        "end_time": datetime.datetime(
                            2020, 8, 16, 5, 43, 3, tzinfo=datetime.timezone.utc
                        ),
                        "errors": 0,
                        "function": "SCRUB",
                        "pause": None,
                        "percentage": 99.60788488388062,
                        "start_time": datetime.datetime(
                            2020, 8, 14, 16, 0, 34, tzinfo=datetime.timezone.utc
                        ),
                        "state": "FINISHED",
                    },
                    "status": "ONLINE",
                    "state": "FINISHED",
                    "topology": {},
                },
            ],
        )

        await self._machine.refresh()

        self.assertEqual(len(self._machine.pools), 1)
        pool = self._machine.pools[0]
        self.assertEqual(pool.encrypt, ENCRYPT)
        self.assertEqual(pool.guid, GUID)
        self.assertEqual(pool.id, ID)
        self.assertEqual(pool.is_decrypted, IS_DECRYPTED)
        self.assertEqual(pool.name, NAME)
        self.assertEqual(pool.status, PoolStatus.ONLINE)
        # Need to work on the return type of scan.state
        # self.assertEqual(pool.scan["state"], PoolScanState.FINISHED)

    async def test_availability(self) -> None:
        ENCRYPT = 0
        GUID = "1234ABCD"
        ID = 100
        IS_DECRYPTED = True
        NAME = "testpool"
        self._server.register_method_handler(
            "pool.query",
            lambda *args: [
                {
                    "encrypt": ENCRYPT,
                    "encryptkey": "",
                    "guid": GUID,
                    "id": ID,
                    "is_decrypted": IS_DECRYPTED,
                    "name": NAME,
                    "scan": {
                        "bytes_issued": 90546145402880,
                        "bytes_processed": 90902589915136,
                        "bytes_to_process": 90546369048576,
                        "end_time": datetime.datetime(
                            2020, 8, 16, 5, 43, 3, tzinfo=datetime.timezone.utc
                        ),
                        "errors": 0,
                        "function": "SCRUB",
                        "pause": None,
                        "percentage": 99.60788488388062,
                        "start_time": datetime.datetime(
                            2020, 8, 14, 16, 0, 34, tzinfo=datetime.timezone.utc
                        ),
                        "state": "FINISHED",
                    },
                    "status": "ONLINE",
                    "topology": {},
                },
            ],
        )

        await self._machine.refresh()

        pool = self._machine.pools[0]
        self.assertTrue(pool.available)

        self._server.register_method_handler(
            "pool.query", lambda *args: [], override=True,
        )
        await self._machine.refresh()
        self.assertFalse(pool.available)
        self.assertEqual(len(self._machine._disks), 0)

    async def test_unavailable_caching(self) -> None:
        """Certain properites have caching even if no longer available"""
        ENCRYPT = 0
        GUID = "1234ABCD"
        ID = 100
        IS_DECRYPTED = True
        NAME = "testpool"
        self._server.register_method_handler(
            "pool.query",
            lambda *args: [
                {
                    "encrypt": ENCRYPT,
                    "encryptkey": "",
                    "guid": GUID,
                    "id": ID,
                    "is_decrypted": IS_DECRYPTED,
                    "name": NAME,
                    "scan": {
                        "bytes_issued": 90546145402880,
                        "bytes_processed": 90902589915136,
                        "bytes_to_process": 90546369048576,
                        "end_time": datetime.datetime(
                            2020, 8, 16, 5, 43, 3, tzinfo=datetime.timezone.utc
                        ),
                        "errors": 0,
                        "function": "SCRUB",
                        "pause": None,
                        "percentage": 99.60788488388062,
                        "start_time": datetime.datetime(
                            2020, 8, 14, 16, 0, 34, tzinfo=datetime.timezone.utc
                        ),
                        "state": "FINISHED",
                    },
                    "status": "ONLINE",
                    "topology": {},
                },
            ],
        )
        await self._machine.refresh()
        pool = self._machine.pools[0]
        assert pool is not None
        self._server.register_method_handler(
            "pool.query", lambda *args: [], override=True,
        )
        await self._machine.refresh()

        self.assertEqual(pool.encrypt, ENCRYPT)
        self.assertEqual(pool.guid, GUID)
        self.assertEqual(pool.id, ID)
        self.assertEqual(pool.is_decrypted, IS_DECRYPTED)
        self.assertEqual(pool.name, NAME)
        self.assertEqual(pool.status, PoolStatus.ONLINE)

    async def test_same_instance_after_refresh(self) -> None:
        self._server.register_method_handler(
            "pool.query", lambda *args: [{"id": 500, "name": "test_pool",},],
        )
        await self._machine.refresh()
        original_pool = self._machine.pools[0]
        await self._machine.refresh()
        new_pool = self._machine.pools[0]
        self.assertIs(original_pool, new_pool)

    def test_eq_impl(self) -> None:
        self._machine._state["pools"] = {200: {"id": 200, "name": "test_pool",}}
        a = Pool(self._machine, 200)
        b = Pool(self._machine, 200)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()