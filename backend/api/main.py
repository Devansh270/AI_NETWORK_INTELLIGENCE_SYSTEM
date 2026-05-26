from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Metric(BaseModel):

    src_ip: str
    dst_ip: str

    src_port: int
    dst_port: int

    protocol: str

    packet_length: int

    timestamp: str


@app.get("/")
async def root():

    return {"message": "FastAPI running"}


@app.post("/metrics", status_code=201)
async def ingest_metric(metric: Metric):

    print(metric.model_dump())

    return {"message": "metric received"}
