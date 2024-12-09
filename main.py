from fastapi import FastAPI, HTTPException
from jobspy import scrape_jobs
import pandas as pd

app = FastAPI()

@app.post("/api/jobs/search")
async def search_jobs(
    search_term: str,
    location: str = None,
    results_wanted: int = 10
):
    try:
        # Configure JobSpy parameters
        params = {
            "site_name": ["indeed", "linkedin", "zip_recruiter", "glassdoor", "google"],
            "search_term": search_term,
            "location": location,
            "results_wanted": results_wanted,
            "country_indeed": location,
        }

        # Scrape jobs
        jobs = scrape_jobs(**params)

        # Replace NaN or None values with default values
        jobs.fillna("", inplace=True)

        # Convert to list of dictionaries
        jobs_list = jobs.to_dict(orient='records')

        return {"jobs": jobs_list, "total_results": len(jobs_list)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
