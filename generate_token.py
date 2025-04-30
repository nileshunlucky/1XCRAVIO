from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the path to the token file from the environment variables
token_file = os.getenv("YOUTUBE_TOKEN_FILE")

# Define the scopes (you already set these during OAuth)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]

# Load credentials
creds = Credentials.from_authorized_user_file(token_file, SCOPES)

# Build the YouTube API client
youtube = build("youtube", "v3", credentials=creds)

# Fetch your channel data
response = youtube.channels().list(
    part="snippet,contentDetails,statistics",
    mine=True
).execute()

# Print the response (your channel info)
print("Channel Info:")
print(response)
