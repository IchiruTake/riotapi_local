from pydantic import Field
from typing import Annotated
import random

class CredentialItem:

    __slots__ = ['_loads']

    def __init__(self) -> None:
        self._loads: list[tuple[int, int]] = []

    def AddLoad(self, max_requests: Annotated[int, Field(description="The maximum requests per second.", ge=1)],
                time_in_second: Annotated[int, Field(description="The time in second.", ge=1)]) -> None:
        self._loads.append((max_requests, time_in_second))

    def GetMinLoad(self) -> tuple[tuple[int, int], float]:
        self._loads.sort(key=lambda x: x[0] / x[1])
        return self._loads[0], self._loads[0][0] / self._loads[0][1]

    def GetMaxLoad(self) -> tuple[tuple[int, int], float]:
        self._loads.sort(key=lambda x: x[0] / x[1], reverse=True)
        return self._loads[0], self._loads[0][0] / self._loads[0][1]


class WeightedCredentialLoadBalancing:

    __slots__ = ['_credentials', '_scaler', '_random_seed']

    def __init__(self, scaler: Annotated[int, Field(ge=1, le=100)] = 10,
                 random_seed: Annotated[int, Field(ge=1)] = 42) -> None:
        self._credentials: dict[str, CredentialItem] = {}
        self._scaler = scaler
        self._random_seed = random_seed
        random.seed(self._random_seed)

    def AddCredItem(self, credential_name: str, max_requests: int, time_in_second: int = 1) -> None:
        if credential_name not in self._credentials:
            self._credentials[credential_name] = CredentialItem()
        self._credentials[credential_name].AddLoad(max_requests, time_in_second)

    def LoadBalance(self) -> CredentialItem:
        if not self._credentials:
            raise ValueError("No credentials are provided.")
        # Obtain the minimum load rate for each credential
        names = []
        min_loads = []
        for name, cred_item in self._credentials.items():
            _, min_load_rate = cred_item.GetMinLoad()
            names.append(name)
            min_loads.append(min_load_rate)

        # Normalize the minimum load rate
        total_load = sum(min_loads)
        for i, load in enumerate(min_loads):
            min_loads[i] = round(load / total_load * 100)
            assert min_loads[i] > 0, "The minimum load rate must be greater than 0."
            assert min_loads[i] <= 100, "The minimum load rate must be less than or equal to 100."
            assert isinstance(min_loads[i], int), "The minimum load rate must be an integer."

        # Generate the list of items based on the minimum load rate and obtain the credential
        lst_items = []
        for i, name in enumerate(names):
            lst_items.extend([name] * min_loads[i] * self._scaler)
        return self._credentials[random.sample(lst_items, k=1)[0]]
