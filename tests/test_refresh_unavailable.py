"""#295 (unavailable on failed cloud refresh) and #297 (unknown gender logged once)."""

import asyncio
import logging
from types import SimpleNamespace

from custom_components.petlibro.devices.device import Device
from custom_components.petlibro.pets import Pet
from custom_components.petlibro.const import Gender


class FakeApi:
    def __init__(self):
        self.fail = False

    async def _call(self, *_):
        if self.fail:
            raise ConnectionError("api unreachable")
        return {"online": True}

    device_base_info = device_real_info = device_attribute_settings = _call

    async def device_get_bound_pets(self, *_):
        if self.fail:
            raise ConnectionError("api unreachable")
        return []


def test_device_refresh_ok_follows_cloud(caplog):
    api = FakeApi()
    dev = Device({"deviceSn": "SN1"}, SimpleNamespace(api=api, member=None))
    updates = []
    dev.on("update", lambda: updates.append(1))
    asyncio.run(dev.refresh())
    assert dev.refresh_ok

    api.fail = True
    with caplog.at_level(logging.INFO):
        asyncio.run(dev.refresh())
        asyncio.run(dev.refresh())
    assert not dev.refresh_ok
    assert len([r for r in caplog.records if r.levelno == logging.ERROR]) == 1
    assert updates, "entities must be told to write the unavailable state"

    api.fail = False
    asyncio.run(dev.refresh())
    assert dev.refresh_ok


def test_unknown_gender_logged_once(caplog):
    pet = Pet({"id": "P1", "gender": 3}, SimpleNamespace(api=None, member=None))
    with caplog.at_level(logging.WARNING):
        for _ in range(5):
            assert pet.gender is Gender.NONE
    assert len(caplog.records) == 1
