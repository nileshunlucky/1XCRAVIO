import os
import random
import time
import logging
import requests
import cloudinary
from cloudinary.search import Search
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Instagram Graph API credentials
IG_USER_ID = os.getenv("IG_USER_ID2")
ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN2")
CLOUDINARY_FOLDER = "1XCRAVIO"

# Instagram captions
CAPTIONS = [
    "Finally made it work 🔥 Cravio helped me create my first faceless video in 10 mins. No camera, no mic. Just results. Link in bio. #CravioAI #MadeWithCravio #facelesscontent #contentcreators #creatorlife #ai #fyp #explorepage #sidehustle #onlinebusiness",

    "It's actually working 💸 Cravio handles everything—script, voice, editing. I just hit upload. Link in bio. #CravioAI #MadeWithCravio #ai #facelessvideos #contenthacks #fyp #explorepage #digitalincome #onlinehustle",

    "This changed everything ✨ Thought it was hype, but Cravio gave me a full video in 2 mins—script and voice included. Link in bio. #CravioAI #MadeWithCravio #facelessgrind #aiforcreators #creatorlife #explorepage #onlinemoney #digitalhustle",

    "I don't feel stuck anymore 💫 Cravio made content creation fun again. No face, no mic, no stress. Link in bio. #CravioAI #MadeWithCravio #contentautomation #facelessbiz #sidehustleideas #ai #fyp #explorepage #onlinecreator #contentstrategy",

    "It finally feels easy 🔥 I made 5 faceless posts in one hour with Cravio and they actually perform better than my old content. Link in bio. #CravioAI #MadeWithCravio #aiapp #creatorjourney #passiveincome #explorepage #fyp #digitaltools #contentcreators",

    "Dream setup 💸 Making content in pajamas with no camera—Cravio does it all. Link in bio. #CravioAI #MadeWithCravio #nocamera #aicontent #facelesscontent #fyp #explorepage #creatorvibes #onlinebusiness",

    "Can't believe this is real 💫 I paste a script, Cravio builds a full reel. No editing. Link in bio. #CravioAI #MadeWithCravio #aiworkflow #facelessgrind #fyp #explorepage #sidehustle #digitalincome #solopreneurlife",

    "This saved me hours 🔥 Cravio did 3 hours of work in 2 minutes. If you're not using it, you're missing out. Link in bio. #CravioAI #MadeWithCravio #facelesscreator #aiautomation #onlineincome #contentcreators #fyp #explorepage #creatorlife",

    "Feels like I finally cracked it 💸 I used to overthink content. Now Cravio handles it. Link in bio. #CravioAI #MadeWithCravio #contentcreation #aiforcreators #explorepage #fyp #growthhacks #facelesscontent",

    "No editing skills? No problem ✨ Cravio makes me feel like a pro—everything's AI. Link in bio. #CravioAI #MadeWithCravio #ai4creators #onlinemoney #facelessvideos #explorepage #fyp #sidehustle #digitalbusiness"
]


def fetch_random_video_from_cloudinary():
    """Fetch a random video from the specified Cloudinary folder."""
    try:
        result = Search()\
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
            post_id = publish_data["id"]
            logger.info(f"Video published successfully! Post ID: {post_id}")

            # Step 4: Add a comment to the published video
            comment_url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
            comment_payload = {
                "message": "Cravio ai ✨ Link in bio 🔥",
                "access_token": ACCESS_TOKEN
            }
            comment_res = requests.post(comment_url, data=comment_payload)
            comment_data = comment_res.json()

            if "id" in comment_data:
                logger.info(f"Comment added successfully. Comment ID: {comment_data['id']}")
            else:
                logger.error(f"Failed to add comment: {comment_data}")
            return True
        else:
            logger.error(f"Failed to publish video: {publish_data}")
            return False
            
    except Exception as e:
        logger.error(f"Error during Instagram posting: {str(e)}")
        return False


def post_random_video():
    """Main function to post a random video with a random caption."""
    logger.info(f"Running Instagram post task at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get a random video
    video_url = fetch_random_video_from_cloudinary()
    if not video_url:
        return False
    
    # Get a random caption
    caption = random.choice(CAPTIONS)
    
    # Post to Instagram
    success = post_video_to_instagram(video_url, caption)
    
    if success:
        logger.info(f"Successfully posted video to Instagram: {video_url}")
        return True
    else:
        logger.error("Failed to post video to Instagram")
        return False