from dotenv import load_dotenv
import os
from influxdb_client import InfluxDBClient

load_dotenv(os.path.join(os.getcwd(), '..', 'infra', '.env'))
url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
token = os.getenv('INFLUXDB_TOKEN')
org = os.getenv('INFLUXDB_ORG')
bucket = os.getenv('INFLUXDB_BUCKET')

print('URL', url)
print('ORG', org)
print('BUCKET', bucket)
client = InfluxDBClient(url=url, token=token, org=org)
print('ping', client.ping())
try:
    b = client.buckets_api().find_bucket_by_name(bucket)
    print('bucket ok', bool(b))
except Exception as e:
    print('bucket check failed:', repr(e))
client.close()