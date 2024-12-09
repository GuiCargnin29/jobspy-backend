from fastapi import FastAPI, HTTPException, Query
from jobspy import scrape_jobs  # Assuming this is a valid library for scraping jobs
import pandas as pd
from supabase import create_client, Client

# Initialize FastAPI app
app = FastAPI()

# Supabase credentials
SUPABASE_URL = "https://sxltlggzfhouiwlwtlnx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4bHRsZ2d6ZmhvdWl3bHd0bG54Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMTM4OTcwNSwiZXhwIjoyMDQ2OTY1NzA1fQ.0DUeqlawLgm9UQ6KErzfFplGe_R_nvTtn3Cd3bsRAhM"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

        # Convert to list of dictionaries
        jobs_list = jobs_filtered.to_dict(orient="records")

        # Save all job postings to Supabase (batch insertion for better performance)
        response = supabase.table("jobs_scraped").insert(jobs_list).execute()

        # Log response for debugging
        print("Supabase Response:", response)

        # Validate insertion response
        if not hasattr(response, "data") or response.data is None:
            raise Exception(f"Failed to insert job postings. Response: {response}")

        return {"jobs": jobs_list, "total_results": len(jobs_filtered)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
