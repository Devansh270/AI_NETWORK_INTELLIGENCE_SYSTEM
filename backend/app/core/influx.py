import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

_client = None
_write_api = None

def get_influx_write_api():
    global _client, _write_api
    if _write_api is None:
        _client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL", "http://influxdb:8086"),
            token=os.getenv("INFLUXDB_TOKEN"),
            org=os.getenv("INFLUXDB_ORG"),
        )
        _write_api = _client.write_api(write_options=SYNCHRONOUS)
    return _write_ap