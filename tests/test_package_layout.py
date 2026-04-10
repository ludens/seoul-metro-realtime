from seoul_metro_realtime.get_arrivals import main
from seoul_metro_realtime.station_lookup import normalize_station_name


def test_package_modules_are_importable():
    assert callable(main)
    assert normalize_station_name("서울역") == "서울"
