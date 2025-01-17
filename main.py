from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from jobspy import scrape_jobs
import pandas as pd
from typing import Generator

# Initialize FastAPI app
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Explicitly list allowed methods
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
)

# Define fields to retrieve
FIELDS_TO_RETRIEVE = [
    "site", "title", "company", "location", "date_posted",
    "job_type", "interval", "emails", "min_amount", "max_amount", "currency",
    "job_url", "description", "company_logo", "company_description"
]

@app.post("/api/jobs/search")
async def search_jobs(
    search_term: str = Query(..., description="Job search term"),
    location: str = Query(..., description="Job location")
):
    try:
        # Define the number of results to fetch
        results_wanted = 600
        batch_size = 20  # Number of jobs per batch

        # Configure JobSpy parameters
        params = {
            "site_name": ["indeed"],
            "search_term": search_term,
            "location": location,
            "job_type": "internship",
            "results_wanted": results_wanted,
            "country_indeed": location,
        }

        # Scrape jobs
        jobs = scrape_jobs(**params)

        # Replace NaN or None values with appropriate defaults
        # Handle numeric fields
        numeric_fields = ["min_amount", "max_amount"]
        for field in numeric_fields:
            if field in jobs.columns:
                jobs[field] = pd.to_numeric(jobs[field], errors="coerce").fillna(0).astype(float)

        # Handle non-numeric fields
        non_numeric_columns = jobs.select_dtypes(exclude=["number"]).columns
        jobs[non_numeric_columns] = jobs[non_numeric_columns].fillna("")

        # Convert "date_posted" to string format (ISO 8601)
        if "date_posted" in jobs.columns:
            jobs["date_posted"] = pd.to_datetime(jobs["date_posted"], errors="coerce").dt.strftime("%Y-%m-%d")

        # Filter fields to retrieve
        jobs_filtered = jobs[FIELDS_TO_RETRIEVE]

        # Generator function to stream jobs in batches
        def job_stream() -> Generator[str, None, None]:
            total_jobs = len(jobs_filtered)
            for i in range(0, total_jobs, batch_size):
                batch = jobs_filtered[i:i + batch_size]
                yield batch.to_json(orient="records")  # Yield batch as JSON

        # Stream response
        return StreamingResponse(job_stream(), media_type="application/json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
