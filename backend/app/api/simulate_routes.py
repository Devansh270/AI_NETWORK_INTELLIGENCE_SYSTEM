from fastapi import APIRouter
import subprocess

router = APIRouter()


@router.post("/simulate/congestion")
async def simulate_congestion():
    try:
        subprocess.Popen(
            ["mnexec", "-a", "1", "iperf", "-c", "10.0.0.2", "-t", "15", "-b", "100M"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return {
            "status": "mininet not available in this environment",
            "duration_sec": 15,
        }
    return {"status": "congestion simulation started", "duration_sec": 15}


@router.post("/simulate/attack")
async def simulate_attack():
    try:
        subprocess.Popen(
            ["mnexec", "-a", "1", "hping3", "-S", "--flood", "10.0.0.2"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return {
            "status": "mininet not available in this environment",
        }
    return {"status": "attack simulation started"}