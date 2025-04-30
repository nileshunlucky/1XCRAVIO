import os
import random
import time
import logging
import requests
import cloudinary
import cloudinary.api
import cloudinary.search
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Instagram Graph API credentials
IG_USER_ID = os.getenv("IG_USER_ID")
ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
CLOUDINARY_FOLDER = "1XCRAVIO"

# Initialize FastAPI
app = FastAPI(
    title="Instagram Automation API",
    description="Service that automatically posts Cloudinary videos to Instagram",
    version="1.0.0"
)

# Captions pool
CAPTIONS = [
    "🔥 Create faceless content with AI. Link in bio. #passiveincome #faceless",
    "🚀 This AI tool makes videos for you. #ai #contentcreator #moneyonline",
    "💰 Automate your content, grow fast. #facelesscontent #aiapp #makepassiveincome"
]

def fetch_random_video_from_cloudinary():
    """Fetch a random video from the specified Cloudinary folder."""
    try:
        result = cloudinary.Search()\
            .expression(f"resource_type:video AND folder:{CLOUDINARY_FOLDER}")\
            .sort_by("public_id", "desc")\
            .max_results(100)\
            .execute()

        videos = result.get("resources", [])
        if not videos:
            logger.error(f"No videos found in Cloudinary folder: {CLOUDINARY_FOLDER}")
            return None

        video = random.choice(videos)
        video_url = video.get("secure_url")
        
        if not video_url or not video_url.startswith("https://"):
            logger.error(f"Invalid video URL: {video_url}")
            return None
            
        return video_url
    except Exception as e:
        logger.error(f"Error fetching video from Cloudinary: {str(e)}")
        return None

def wait_for_video_processing(creation_id, max_attempts=10, delay=5):
    """Wait for Instagram to finish processing the video."""
    for attempt in range(max_attempts):
        try:
            status_res = requests.get(
                f"https://graph.facebook.com/v19.0/{creation_id}",
                params={"fields": "status_code", "access_token": ACCESS_TOKEN}
            )
            status_data = status_res.json()
            
            if "error" in status_data:
                logger.error(f"Error checking status: {status_data['error']}")
                return False
                
            status = status_data.get("status_code")
            logger.info(f"Video status: {status} (attempt {attempt+1}/{max_attempts})")
            
            if status == "FINISHED":
                return True
            if status in ["ERROR", "REJECTED"]:
                logger.error(f"Video processing failed with status: {status}")
                return False
                
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Error checking video status: {str(e)}")
            time.sleep(delay)
    
    logger.error("Video processing timed out")
    return False

def post_video_to_instagram(video_url, caption):
    """Post a video to Instagram using the Graph API."""
    if not IG_USER_ID or not ACCESS_TOKEN:
        logger.error("Missing Instagram credentials. Check environment variables.")
        return False

    logger.info("Starting Instagram video upload process...")

    try:
        # Step 1: Create container for the video
        create_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
        create_payload = {
            "video_url": video_url,
            "caption": caption,
            "media_type": "REELS",
            "access_token": ACCESS_TOKEN
        }

        create_res = requests.post(create_url, data=create_payload)
        create_data = create_res.json()

        if "id" not in create_data:
            logger.error(f"Failed to create media container: {create_data}")
            return False

        creation_id = create_data["id"]
        logger.info(f"Media container created with ID: {creation_id}")

        # Step 2: Wait for video processing
        if not wait_for_video_processing(creation_id):
            return False

        # Step 3: Publish the processed video
        publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": ACCESS_TOKEN
        }

        publish_res = requests.post(publish_url, data=publish_payload)
        publish_data = publish_res.json()

        if "id" in publish_data:
            logger.info(f"Video published successfully! Post ID: {publish_data['id']}")
            return True
        else:
            logger.error(f"Failed to publish video: {publish_data}")
            return False
            
    except Exception as e:
        logger.error(f"Error during Instagram posting: {str(e)}")
        return False

def post_random_video():
    """Main function to post a random video with a random caption."""
    logger.info(f"Running scheduled post task at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get a random video
    video_url = fetch_random_video_from_cloudinary()
    if not video_url:
        return
    
    # Get a random caption
    caption = random.choice(CAPTIONS)
    
    # Post to Instagram
    success = post_video_to_instagram(video_url, caption)
    
    if success:
        logger.info(f"Successfully posted video: {video_url}")
    else:
        logger.error("Failed to post video to Instagram")

# Initialize scheduler
def initialize_scheduler():
    """Set up the scheduler with cron jobs."""
    scheduler = BackgroundScheduler()
    
    # Schedule posts at 11:00 AM
    scheduler.add_job(
        post_random_video,
        CronTrigger(hour=11, minute=0),
        id="morning_post",
        name="Morning Instagram Post"
    )
    
    # Schedule posts at 7:00 PM
    scheduler.add_job(
        post_random_video,
        CronTrigger(hour=19, minute=0),
        id="evening_post",
        name="Evening Instagram Post"
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started with posts at 11:00 AM and 7:00 PM daily")
    return scheduler

# Create scheduler instance
scheduler = initialize_scheduler()

@app.get("/")
def root():
    """Root endpoint with service status."""
    next_runs = {job.id: job.next_run_time for job in scheduler.get_jobs()}
    return {
        "status": "active",
        "service": "Instagram Automation",
        "next_scheduled_posts": next_runs
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

@app.post("/post-now")
def manual_post():
    """Trigger an immediate post."""
    try:
        post_random_video()
        return {"status": "success", "message": "Manual post triggered successfully"}
    except Exception as e:
        logger.error(f"Error in manual post: {str(e)}")
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