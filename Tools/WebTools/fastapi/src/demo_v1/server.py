
from requests import Request
from fastapi import FastAPI


app = FastAPI()


@app.post("/shadowhunter/verify")
async def shadowhunter_verify_route(request: Request):

    request_json = await request.json()


    return

# @app.get("/shadowhunter/verify")
# async def s

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)