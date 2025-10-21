from fastapi import FastAPI

app = FastAPI(title="Emergency Contact API", version="1.0")

@app.get("/")
def root():
    return {"message": "Emergency Contact backend Running Sucessfully!"}

@app.post("/emergency/alert")
async def emergency_alert(

)