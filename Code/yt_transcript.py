from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from youtube_transcript_api.formatters import TextFormatter
import re
from datetime import datetime
import os

def get_video_id(url):
    """Extract video ID from YouTube URL"""
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def merge_transcript_segments(transcript_list, max_gap_seconds=1.5):
    """
    Merge transcript segments into full sentences.
    Uses punctuation and small gaps between entries to detect sentence ends.
    """
    if not transcript_list:
        return []

    merged = []
    current_segment = {
        "start": transcript_list[0]['start'],
        "end": transcript_list[0]['end'],
        "text": transcript_list[0]['text'].strip()
    }

    sentence_end_punct = {'.', '?', '!', '"', "'", ')'}
    
    for entry in transcript_list[1:]:
        prev_text = current_segment['text']
        current_text = entry['text'].strip()

        # Check if previous segment ends with sentence-ending punctuation
        ends_with_sentence_end = len(prev_text) > 0 and prev_text[-1] in sentence_end_punct
        # Or check if there's a gap larger than threshold between entries
        starts_new = entry['start'] > current_segment['end'] + max_gap_seconds

        if ends_with_sentence_end or starts_new:
            # Finalize current segment
            merged.append(current_segment)
            # Start new segment
            current_segment = {
                "start": entry['start'],
                "end": entry['end'],
                "text": current_text
            }
        else:
            # Continue building segment
            current_segment['text'] += " " + current_text
            current_segment['end'] = entry['end']

    # Add the last one
    merged.append(current_segment)
    return merged


def get_clean_transcript(url):
    """Get clean transcript with full sentences and correct timestamps"""
    try:
        video_id = get_video_id(url)
        if not video_id:
            return "Error: Invalid YouTube URL"
        
        print(f"Fetching transcript for video ID: {video_id}")
        
        transcript_list = None
        error_message = None
        
        # First try: Direct English transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        except Exception as e:
            error_message = str(e)
            print(f"Could not get direct English transcript: {error_message}")
        
        # Second try: List and find available transcripts
        if not transcript_list:
            try:
                transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                available_langs = [t.language_code for t in transcripts]
                print(f"Available languages: {available_langs}")

                # Try English variants first
                english_variants = [lang for lang in available_langs if 'en' in lang.lower()]
                
                if english_variants:
                    print(f"Found English variants: {english_variants}")
                    # Try each English variant
                    for lang in english_variants:
                        try:
                            transcript = transcripts.find_transcript([lang])
                            transcript_list = transcript.fetch()
                            print(f"Successfully fetched transcript in {lang}")
                            break
                        except Exception as e:
                            print(f"Failed to fetch {lang} transcript: {str(e)}")
                            continue
                
                # If no English transcript worked, try auto-translate
                if not transcript_list and available_langs:
                    try:
                        print("Attempting to translate transcript to English...")
                        transcript = transcripts.find_transcript(available_langs)
                        transcript_list = transcript.translate('en').fetch()
                    except Exception as e:
                        print(f"Translation failed: {str(e)}")

            except Exception as e:
                error_message = str(e)
                print(f"Error listing transcripts: {error_message}")

        if not transcript_list:
            return f"Error: Could not fetch transcript. {error_message if error_message else 'No available transcripts.'}"

        # Add missing 'end' field where necessary
        for entry in transcript_list:
            if 'end' not in entry:
                entry['end'] = entry['start'] + entry.get('duration', 0)

        # Merge broken-up segments into full sentences
        cleaned_segments = merge_transcript_segments(transcript_list)
        
        if not cleaned_segments:
            return "Error: No transcript segments were generated."

        # Save to file
        os.makedirs('transcripts', exist_ok=True)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcripts/transcript_{video_id}_{current_time}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            for seg in cleaned_segments:
                start = format_time(seg['start'])
                end = format_time(seg['end'])
                text = seg['text'].strip()
                
                line = f"[{start} - {end}] {text}\n"
                print(line.strip())
                f.write(line)

        return f"\n✅ Transcript saved to '{filename}' successfully."

    except Exception as e:
        return f"❌ Error: {str(e)}"

# # Example usage
# if __name__ == "__main__":
#     youtube_url = "https://www.youtube.com/watch?v=HNpYAz_I4yY"
    
#     result = get_clean_transcript(youtube_url)
#     print(result)
