from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class Engine(ABC):
    """采集引擎基类"""

    @abstractmethod
    async def collect(self, keyword: str, **kwargs) -> List[dict]:
        """采集数据"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """引擎名称"""
        ...