import os
import logging
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Import platform-specific modules
from instagram import post_random_video as instagram_post
from youtube import upload_random_video as youtube_upload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Social Media Automation API",
    description="Service that automatically posts content to Instagram and YouTube",
    version="1.0.0"
)

# Initialize scheduler
def initialize_scheduler():
    """Set up the scheduler with cron jobs."""
    scheduler = BackgroundScheduler()
    
    # Instagram schedules
    scheduler.add_job(
        instagram_post,
        CronTrigger(hour=11, minute=0),
        id="instagram_morning_post",
        name="Morning Instagram Post"
    )
    
    scheduler.add_job(
        instagram_post,
        CronTrigger(hour= 21, minute=15),
        id="instagram_evening_post",
        name="Evening Instagram Post"
    )

    # YouTube schedules
    scheduler.add_job(
        youtube_upload,
        CronTrigger(hour=21, minute=15),
        id="youtube_daily_post",
        name="Daily YouTube Upload" 
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started with all social media posting jobs")
    return scheduler

# Create scheduler instance
scheduler = initialize_scheduler()

@app.get("/")
def root():
    """Root endpoint with service status."""
    next_runs = {job.id: job.next_run_time for job in scheduler.get_jobs()}
    return {
        "status": "active",
        "service": "Social Media Automation",
        "next_scheduled_posts": next_runs
    }

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

@app.get("/instagram/post-now")
def manual_instagram_post():
    """Trigger an immediate Instagram post."""
    try:
        instagram_post()
        return {"status": "success", "message": "Manual Instagram post triggered successfully"}
    except Exception as e:
        logger.error(f"Error in manual Instagram post: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/youtube/upload-now")
def manual_youtube_upload():
    """Trigger an immediate YouTube upload."""
    try:
        youtube_upload()
        return {"status": "success", "message": "Manual YouTube upload triggered successfully"}
    except Exception as e:
        logger.error(f"Error in manual YouTube upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
def list_jobs():
    """List all scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
        })
    return {"jobs": jobs}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)