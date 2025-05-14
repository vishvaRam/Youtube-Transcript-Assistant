from youtube_transcript_api import YouTubeTranscriptApi
import re
from datetime import datetime
import os

def get_video_id(url):
    """Extract video ID from YouTube URL"""
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript_with_timestamps(url):
    """Get transcript with timestamps from YouTube URL, grouped in 30-second intervals"""
    try:
        video_id = get_video_id(url)
        if not video_id:
            return "Error: Invalid YouTube URL"
        
        print(f"Attempting to get transcript for video ID: {video_id}")
        
        # Get the transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as transcript_error:
            print(f"Failed to get transcript. Error details: {str(transcript_error)}")
            # Check if captions are available in other languages
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                available_transcripts = [t.language_code for t in transcript_list]
                return f"No English transcript found. Available languages: {', '.join(available_transcripts)}"
            except Exception as e:
                return f"Error: Could not get transcript. Video might be private, unavailable, or have no captions. Details: {str(e)}"
        
        # Group transcript entries into 30-second intervals
        interval = 30  # seconds
        grouped_transcript = {}
        
        for entry in transcript_list:
            # Determine which 30-second interval this entry belongs to
            interval_start = (int(entry['start']) // interval) * interval
            
            if interval_start not in grouped_transcript:
                grouped_transcript[interval_start] = []
            
            grouped_transcript[interval_start].append(entry['text'])
        
        # Format transcript with timestamps
        formatted_transcript = ""
        for start_time in sorted(grouped_transcript.keys()):
            # Convert seconds to HH:MM:SS format
            hours = start_time // 3600
            minutes = (start_time % 3600) // 60
            seconds = start_time % 60
            timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
            
            # Combine all text entries for this interval
            combined_text = " ".join(grouped_transcript[start_time])
            
            # Add timestamp and text
            formatted_transcript += f"{timestamp} {combined_text}\n\n"
        
        # Create transcripts directory if it doesn't exist
        if not os.path.exists('transcripts'):
            os.makedirs('transcripts')
        
        # Save to file with timestamp in filename
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcripts/transcript_{video_id}_{current_time}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(formatted_transcript)
        
        return f"Transcript saved successfully to {filename}"
        
    except Exception as e:
        return f"Error: {str(e)}"

# Example usage
if __name__ == "__main__":
    # Test with a video that definitely has English captions
    youtube_url = "https://www.youtube.com/watch?v=HNpYAz_I4yY&t=815s"  # "Me at the zoo" - First YouTube video
    
    print("Extracting transcript...")
    print(f"Processing URL: {youtube_url}")
    result = get_transcript_with_timestamps(youtube_url)
    print(result)