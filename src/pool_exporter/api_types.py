from dataclasses import dataclass


@dataclass(frozen=True)
class PoolOccupancyData:
    """Pool occupancy data with proper types."""

    uid: str
    name: str
    freespace: int
    maxspace: int
    currentfill: int

    @classmethod
    def from_dict(cls, data: dict[str, str | int]) -> "PoolOccupancyData":
        """Create PoolOccupancy from API data with type conversion."""
        return cls(
            uid=str(data["uid"]),
            name=str(data["name"]),
            freespace=int(data["freespace"]),
            maxspace=int(data["maxspace"]),
            currentfill=int(data["currentfill"]),  # Convert string to int
        )


@dataclass(frozen=True)
class TemperatureData:
    pool_id: str | None
    temperature: float | None
    title: str | None
    status: str | None = None
    last_updated: str | None = None
