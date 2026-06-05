from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
import os
import sys

load_dotenv(os.path.join(os.getcwd(), "..", "infra", ".env"))

url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
token = os.getenv("INFLUXDB_TOKEN")
org = os.getenv("INFLUXDB_ORG")
bucket = os.getenv("INFLUXDB_BUCKET")

print(f"URL: {url}")
print(f"ORG: {org}")
print(f"BUCKET: {bucket}")

try:
    client = InfluxDBClient(url=url, token=token, org=org)

    print("Ping:", client.ping())

    query_api = client.query_api()

    # Count records
    count_query = f'''
    from(bucket: "{bucket}")
      |> range(start: -30d)
      |> count()
    '''

    count_tables = query_api.query(org=org, query=count_query)

    total_count = 0
    for table in count_tables:
        for record in table.records:
            try:
                total_count += int(record.get_value())
            except Exception:
                pass

    print(f"\nTotal records: {total_count}")

    # Latest 5 records
    latest_query = f'''
    from(bucket: "{bucket}")
      |> range(start: -30d)
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 5)
    '''

    latest_tables = query_api.query(org=org, query=latest_query)

    rows = []
    for table in latest_tables:
        for record in table.records:
            rows.append(record)

    print("\nLatest 5 records:")

    if not rows:
        print("Bucket is empty.")
    else:
        for i, r in enumerate(rows, start=1):
            print(
                f"{i}. time={r.get_time()} "
                f"measurement={r.get_measurement()} "
                f"field={r.get_field()} "
                f"value={r.get_value()}"
            )

    client.close()
    sys.exit(0)

except Exception as e:
    print("InfluxDB check failed:", repr(e))
    sys.exit(1)