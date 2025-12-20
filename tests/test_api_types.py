import pytest

from pool_exporter.api_types import PoolOccupancyData, TemperatureData


@pytest.mark.parametrize(
    "raw_data,expected_uid,expected_name,expected_freespace,expected_maxspace,expected_currentfill",
    [
        # Valid data with string currentfill
        (
            {
                "uid": "SSD-1",
                "name": "Test Pool",
                "freespace": 50,
                "maxspace": 100,
                "currentfill": "50",
            },
            "SSD-1",
            "Test Pool",
            50,
            100,
            50,
        ),
        # Zero capacity edge case
        (
            {
                "uid": "SSD-2",
                "name": "Closed Pool",
                "freespace": 0,
                "maxspace": 0,
                "currentfill": "0",
            },
            "SSD-2",
            "Closed Pool",
            0,
            0,
            0,
        ),
        # Type conversion - int uid to string, string numbers to int
        (
            {
                "uid": 123,
                "name": "Test Pool",
                "freespace": "25",
                "maxspace": "100",
                "currentfill": 75,
            },
            "123",
            "Test Pool",
            25,
            100,
            75,
        ),
    ],
)
def test_pool_occupancy_data_from_dict(
    raw_data: dict,
    expected_uid: str,
    expected_name: str,
    expected_freespace: int,
    expected_maxspace: int,
    expected_currentfill: int,
) -> None:
    """Test PoolOccupancyData.from_dict with various valid inputs."""
    pool_data = PoolOccupancyData.from_dict(raw_data)

    assert pool_data.uid == expected_uid
    assert isinstance(pool_data.uid, str)
    assert pool_data.name == expected_name
    assert pool_data.freespace == expected_freespace
    assert isinstance(pool_data.freespace, int)
    assert pool_data.maxspace == expected_maxspace
    assert isinstance(pool_data.maxspace, int)
    assert pool_data.currentfill == expected_currentfill
    assert isinstance(pool_data.currentfill, int)


@pytest.mark.parametrize(
    "raw_data,expected_exception",
    [
        # Missing required fields
        (
            {"uid": "SSD-1", "name": "Test Pool"},
            KeyError,
        ),
        # Invalid type that can't be converted
        (
            {
                "uid": "SSD-1",
                "name": "Test Pool",
                "freespace": "not_a_number",
                "maxspace": 100,
                "currentfill": 50,
            },
            ValueError,
        ),
    ],
)
def test_pool_occupancy_data_from_dict_errors(
    raw_data: dict, expected_exception: type[Exception]
) -> None:
    """Test that PoolOccupancyData.from_dict raises appropriate exceptions for invalid data."""
    with pytest.raises(expected_exception):
        PoolOccupancyData.from_dict(raw_data)


def test_pool_occupancy_data_immutable() -> None:
    """Test that PoolOccupancyData is immutable (frozen dataclass)."""
    pool_data = PoolOccupancyData(
        uid="SSD-1",
        name="Test Pool",
        freespace=50,
        maxspace=100,
        currentfill=50,
    )

    with pytest.raises(AttributeError):
        pool_data.uid = "SSD-2"  # type: ignore[misc]


def test_temperature_data_creation() -> None:
    """Test TemperatureData creation with all fields."""
    temp_data = TemperatureData(
        pool_id="SSD-1",
        temperature=25.5,
        title="Test Pool",
        status="Open",
        last_updated="2025-01-01T12:00:00",
    )

    assert temp_data.pool_id == "SSD-1"
    assert temp_data.temperature == 25.5
    assert temp_data.title == "Test Pool"
    assert temp_data.status == "Open"
    assert temp_data.last_updated == "2025-01-01T12:00:00"


def test_temperature_data_optional_fields() -> None:
    """Test TemperatureData creation with optional fields as None."""
    temp_data = TemperatureData(
        pool_id="SSD-1",
        temperature=None,
        title=None,
        status=None,
        last_updated=None,
    )

    assert temp_data.pool_id == "SSD-1"
    assert temp_data.temperature is None
    assert temp_data.title is None
    assert temp_data.status is None
    assert temp_data.last_updated is None


def test_temperature_data_zero_temperature() -> None:
    """Test TemperatureData with zero temperature (edge case)."""
    temp_data = TemperatureData(
        pool_id="SSD-1",
        temperature=0.0,
        title="Frozen Pool",
    )

    assert temp_data.temperature == 0.0


def test_temperature_data_immutable() -> None:
    """Test that TemperatureData is immutable (frozen dataclass)."""
    temp_data = TemperatureData(
        pool_id="SSD-1",
        temperature=25.5,
        title="Test Pool",
    )

    with pytest.raises(AttributeError):
        temp_data.temperature = 30.0  # type: ignore[misc]


def test_temperature_data_default_status() -> None:
    """Test TemperatureData with default status value."""
    temp_data = TemperatureData(
        pool_id="SSD-1",
        temperature=25.5,
        title="Test Pool",
    )

    # Default value is None for status
    assert temp_data.status is None
