from fastapi import FastAPI, HTTPException, Query
from jobspy import scrape_jobs
import pandas as pd
from supabase import create_client, Client
import uuid  # For generating unique job IDs

# Initialize FastAPI app
app = FastAPI()

# Supabase credentials
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_key"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define fields to retrieve
FIELDS_TO_RETRIEVE = [
    "site", "title", "company", "location", "date_posted",
    "job_type", "interval", "emails", "min_amount", "max_amount", "currency",
    "job_url", "description", "company_logo", "company_description", "date_posted"
]

@app.post("/api/jobs/search")
async def search_jobs(
    search_term: str = Query(..., description="Job search term"),
    location: str = Query(..., description="Job location"),
    page: int = Query(1, description="Page number (each page contains 10 results)")
):
    try:
        # Calculate start index and end index for pagination
        results_wanted = 80
        start_index = (page - 1) * 10
        end_index = start_index + 10

        # Configure JobSpy parameters
        params = {
            "site_name": ["indeed"],
            "search_term": search_term,
            "location": location,
            "results_wanted": results_wanted,
            "country_indeed": location,
        }

        # Scrape jobs
        jobs = scrape_jobs(**params)

        # Replace NaN or None values with default values
        jobs.fillna("", inplace=True)

        # Filter fields to retrieve
        jobs_filtered = jobs[FIELDS_TO_RETRIEVE]

        # Paginate results
        jobs_paginated = jobs_filtered.iloc[start_index:end_index]

        # Add unique job IDs
        jobs_paginated["job_id"] = [str(uuid.uuid4()) for _ in range(len(jobs_paginated))]

        # Convert to list of dictionaries
        jobs_list = jobs_paginated.to_dict(orient="records")

        # Save results to Supabase
        for job in jobs_list:
            response = supabase.table("jobs_scraped").insert(job).execute()
            if response.status_code != 200:
                print(f"Failed to insert job: {job}")

        return {"jobs": jobs_list, "total_results": len(jobs_filtered), "page": page}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
