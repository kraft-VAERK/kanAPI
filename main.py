import http
from fastapi import FastAPI, Request
import logging
import uvicorn
import time
from contextlib import asynccontextmanager
from models import Case, CaseList
from faker import Faker
import sys
# Configure logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logging.info("FastAPI application startup complete - Application is ready to receive requests")
    yield
    # Shutdown logic
    logging.info("FastAPI application shutdown complete")

app = FastAPI(lifespan=lifespan)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logging.info(f"Endpoint: {request.method} {request.url.path} | Status: {response.status_code} | Time: {process_time:.4f}s")
    return response

@app.get("/fastapi")
async def read_root():
    return {"Hello": "World"}

@app.get("/fastapi/cases/{case_id}")
async def read_case(case_id: str):
    case = await get_case_by_id(case_id)
    if case:
        return case
    else:
        logging.warning(f"Case with id {case_id} not found")
        return {"error": "Case not found"}, 404
@app.get("/fastapi/health/startup")
async def startup_health():
    return http.HTTPStatus.OK
@app.get("/fastapi/health/ready")
async def readiness_check():
    return http.HTTPStatus.OK
@app.get("/fastapi/health/live")
async def liveness_check():
    return http.HTTPStatus.OK

fake = Faker()

cases = CaseList(
    cases=[
        Case(
            id=str(i),
            deleted=fake.boolean(chance_of_getting_true=20),
            responsible_person=fake.name(),
            status=fake.random_element(elements=('open', 'closed', 'pending')),
            customer=fake.company()
        )
        for i in range(1, 21)
    ]
)
async def get_case_by_id(case_id: str) -> Case | None:
    for case in cases:
        if case.id == case_id:
            return case
    return None

if __name__ == "__main__":
    logging.info("Starting FastAPI application...")
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "dev":
            # Run in watch mode for development
            uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info", reload=True)
        elif mode == "prod":
            # Run without watch mode for production
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
        else:
            logging.error("Invalid mode specified. Use 'dev' for development or 'prod' for production.")
            sys.exit(1)
    else:
        logging.error("No mode specified. Use 'dev' for development or 'prod' for production.")
        sys.exit(1)