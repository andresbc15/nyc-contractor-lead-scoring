from fastapi import FastAPI

from app.routers import licenses, permits, websites

app = FastAPI()
app.include_router(licenses.router)
app.include_router(permits.router)
app.include_router(websites.router)
app.include_router(data.router)
