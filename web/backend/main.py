from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {
        "message": "Juniper Network Management API is running!"
    }


@app.get("/switch/status")
def switch_status():
    return {
        "hostname": "switch-1",
        "ip": "192.168.1.1",
        "status": "connected"
    }