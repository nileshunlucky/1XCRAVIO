import os
import random
import logging
import time
import cloudinary
from cloudinary.search import Search
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import io
import tempfile
from datetime import datetime
import json
# Configure logging
logger = logging.getLogger(__name__)

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# YouTube API credentials
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", 
          "https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.force-ssl"]  # Added force-ssl scope for comments
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
YOUTUBE_CLIENT_SECRETS_JSON = os.getenv("YOUTUBE_CLIENT_SECRETS_JSON", "client_secret.json")
YOUTUBE_TOKEN_JSON = os.getenv("YOUTUBE_TOKEN_JSON", "youtube_token.json")
CLOUDINARY_FOLDER = "1XCRAVIO"

# YouTube video metadata
TITLES = [
    "How I Make Faceless Videos in Minutes with Cravio AI",
    "This AI Tool Changed My Content Creation Game Forever",
    "Creating High-Quality Faceless Videos Without Any Equipment",
    "How to Use AI to Automate Your Content Creation (Cravio Tutorial)",
    "The Ultimate AI Tool for Faceless Content Creators",
    "How I Make $1000/Week with AI-Generated Content",
    "Cravio AI: The Tool Every Content Creator Needs",
    "Automated Video Creation: From Script to Upload in 10 Minutes",
    "No Camera, No Problem: Create Professional Videos with AI",
    "Stop Struggling with Content Creation: Try This AI Tool"
]

DESCRIPTIONS = [
    """🔥 Discover how I create professional faceless videos with Cravio AI!

In this video, I show you my complete workflow for making high-quality content without showing my face or using my voice. Cravio handles everything from scripts to final edits.

✅ No camera needed
✅ No microphone needed
✅ No editing skills required
✅ Super easy to use

Try Cravio AI: cravioai.vercel.app

#CravioAI #FacelessContent #ContentCreation #AITools #PassiveIncome
    """,
    
    """💸 Want to create faceless videos that actually get views?

I've tried dozens of AI tools, but Cravio is the only one that consistently produces high-quality content that performs well. In this video, I'll show you exactly how I use it.

Try Cravio yourself: cravioai.vercel.app

#CravioAI #ContentCreation #AITools #FacelessYouTube #PassiveIncome
    """,
    
    """✨ The EASIEST way to create faceless videos in 2025!

Cravio AI has completely transformed my content creation process. In this video, I'll demonstrate how you can go from a simple idea to a fully produced video in minutes - no technical skills required!

🔗 Try Cravio: cravioai.vercel.app

#CravioAI #FacelessContent #AITools #ContentCreation #PassiveIncome
    """
]

# YouTube comment to add after upload
VIDEO_COMMENTS = [
    "Cravio AI ✨ http://cravioai.vercel.app",
    "Try Cravio AI for free today! ✨ http://cravioai.vercel.app",
    "Check out Cravio AI ✨ http://cravioai.vercel.app"
]

TAGS = [
    "CravioAI", "FacelessContent", "AITools", "ContentCreation", 
    "PassiveIncome", "SideHustle", "AIVideoCreation", "NoCamera", 
    "FacelessYouTube", "OnlineIncome", "DigitalMarketing"
]

CATEGORY_ID = "27"  # Education

def get_youtube_credentials():
    """Get or refresh YouTube API credentials."""
    creds = None
    
    # Check if YOUTUBE_TOKEN_JSON is a file path or JSON string
    if os.path.exists(YOUTUBE_TOKEN_JSON):
        # It's a file path
        with open(YOUTUBE_TOKEN_JSON, 'r') as f:
            token_data = f.read()
            try:
                creds = Credentials.from_authorized_user_info(
                    info=json.loads(token_data), scopes=SCOPES)
            except json.JSONDecodeError:
                # Try eval as fallback for string representation
                creds = Credentials.from_authorized_user_info(
                    info=eval(token_data), scopes=SCOPES)
    else:
        # It might be a JSON string directly
        try:
            creds = Credentials.from_authorized_user_info(
                info=json.loads(YOUTUBE_TOKEN_JSON), scopes=SCOPES)
        except (json.JSONDecodeError, TypeError):
            logger.error("YOUTUBE_TOKEN_JSON is neither a valid file path nor a valid JSON string")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Similar check for client secrets
            if os.path.exists(YOUTUBE_CLIENT_SECRETS_JSON):
                # It's a file path
                flow = InstalledAppFlow.from_client_secrets_file(
                    YOUTUBE_CLIENT_SECRETS_JSON, SCOPES)
            else:
                # Create a temporary file from the JSON string
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                    temp_file.write(YOUTUBE_CLIENT_SECRETS_JSON)
                    temp_secrets_path = temp_file.name
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    temp_secrets_path, SCOPES)
                os.unlink(temp_secrets_path)  # Clean up
                
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("youtube_token.json", 'w') as token:
            token.write(creds.to_json())
    
    return creds


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


def download_video_to_temp_file(video_url):
    """Download a video from URL to a temporary file."""
    try:
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        # Create a temporary file with .mp4 extension
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_filename = temp_file.name
        
        # Write the video content to the file
        with open(temp_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Video downloaded to temporary file: {temp_filename}")
        return temp_filename
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        return None


def add_comment_to_video(youtube, video_id):
    """Add a comment to the uploaded video."""
    try:
        # Choose a random comment from the list
        comment_text = random.choice(VIDEO_COMMENTS)
        
        # Create the comment
        comment = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": comment_text
                    }
                }
            }
        }
        
        # Insert the comment
        response = youtube.commentThreads().insert(
            part="snippet",
            body=comment
        ).execute()
        
        comment_id = response["id"]
        logger.info(f"Successfully added comment to video {video_id}. Comment ID: {comment_id}")
        return comment_id
    except Exception as e:
        logger.error(f"Error adding comment to video {video_id}: {str(e)}")
        return None


def upload_video_to_youtube(file_path):
    """Upload a video to YouTube using the YouTube Data API."""
    try:
        # Get authentication credentials
        credentials = get_youtube_credentials()
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
        
        # Prepare video metadata
        title = random.choice(TITLES)
        description = random.choice(DESCRIPTIONS)
        
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": TAGS,
                "categoryId": CATEGORY_ID
            },
            "status": {
                "privacyStatus": "public",  # or "private" or "unlisted"
                "selfDeclaredMadeForKids": False
            }
        }
        
        # Create upload request
        logger.info(f"Starting YouTube upload for file: {file_path}")
        
        media = MediaFileUpload(file_path, 
                                mimetype="video/mp4", 
                                resumable=True)
        
        # Execute the request
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        
        # Upload the video
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                logger.info(f"Upload progress: {percent}%")
        
        # Get the video ID from the response
        video_id = response["id"]
        logger.info(f"Video uploaded successfully! Video ID: {video_id}")
        
        # Add a comment to the video
        logger.info(f"Adding comment to video {video_id}...")
        # Add a small delay to ensure the video is fully processed before commenting
        time.sleep(5)
        comment_id = add_comment_to_video(youtube, video_id)
        
        return video_id
        
    except Exception as e:
        logger.error(f"Error uploading to YouTube: {str(e)}")
        return None
    finally:
        # Clean up - remove temporary file
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Temporary file removed: {file_path}")


def upload_random_video():
    """Main function to upload a random video to YouTube."""
    logger.info(f"Running YouTube upload task at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get a random video from Cloudinary
    video_url = fetch_random_video_from_cloudinary()
    if not video_url:
        return False
    
    # Download the video to a temporary file
    temp_file = download_video_to_temp_file(video_url)
    if not temp_file:
        return False
    
    # Upload the video to YouTube
    video_id = upload_video_to_youtube(temp_file)
    
    if video_id:
        logger.info(f"Successfully uploaded video to YouTube. Video ID: {video_id}")
        return True
    else:
        logger.error("Failed to upload video to YouTube")
        return False