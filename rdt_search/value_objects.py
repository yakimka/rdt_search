import time
from dataclasses import dataclass


@dataclass
class Time:
    milliseconds: int

    @property
    def humanized(self) -> str:
        return time.strftime("%H:%M:%S", time.gmtime(self.seconds))

    @property
    def seconds(self) -> int:
        return self.milliseconds // 1000
