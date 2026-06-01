import os
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

_client = None
_write_api = None
_bucket = None


def influx_is_configured():
    return all(
        os.getenv(name)
        for name in ("INFLUXDB_TOKEN", "INFLUXDB_ORG", "INFLUXDB_BUCKET")
    )


def get_influx_bucket():
    return os.getenv("INFLUXDB_BUCKET", "network")


def get_influx_write_api():
    global _client, _write_api
    if _write_api is None:
        _client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
            token=os.getenv("INFLUXDB_TOKEN"),
            org=os.getenv("INFLUXDB_ORG"),
        )
        _write_api = _client.write_api(write_options=SYNCHRONOUS)
    return _write_api
