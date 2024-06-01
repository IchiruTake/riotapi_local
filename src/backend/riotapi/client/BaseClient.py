import inspect
import logging
import time
from typing import Callable

import httpx
from src.utils.utils import GetDurationOfPerfCounterInMs


# ==================================================================================================
_POOL: dict[tuple[str, str], httpx.AsyncClient | httpx.Client] = {}

def AddToPool(region: str, credential_name: str, client: httpx.AsyncClient | httpx.Client) -> None:
    _POOL[(region, credential_name)] = client


def GetFromPool(region: str, credential_name: str) -> httpx.AsyncClient | httpx.Client:
    return _POOL[(region, credential_name)]


def RemoveFromPool(region: str, credential_name: str) -> None:
    _POOL.pop((region, credential_name))

def Iterate() -> tuple[str, httpx.AsyncClient | httpx.Client]:
    for key, value in _POOL.items():
        yield key, value


def WrapCleanUpPool(func: Callable) -> Callable:
    async def _Func(*args, **kwargs) -> None:
        logging.info("Cleaning up the Riot client pool.")
        t = time.perf_counter()
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        # _POOL.clear()     # Don't enable this
        logging.debug(f"Cleaned up the Riot client pool in {GetDurationOfPerfCounterInMs(t):.2f} ms.")
        return result

    return _Func

def WrapGetRiotClient(func: Callable) -> Callable:
    def _Func(region: str, credential_name: str, *args, **kwargs) -> httpx.AsyncClient | httpx.Client:
        if (region, credential_name) in _POOL:
            logging.info(f"Found an existing Riot client for region: {region}")
            return _POOL[(region, credential_name)]

        logging.info(f"Creating a new Riot client for {region} region with {credential_name} credential.")
        t = time.perf_counter()
        client = func(region, credential_name, *args, **kwargs)
        AddToPool(region, credential_name, client)
        logging.debug(f"Created a new Riot {credential_name} client on region: {region} in "
                      f"{GetDurationOfPerfCounterInMs(t):.2f} ms.")
        return client

    return _Func
