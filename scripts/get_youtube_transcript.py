#!/usr/bin/env python3
"""
YouTube Transcript Fetcher für n8n
Verwendung: python3 get_youtube_transcript.py <video_id>
Gibt das Transkript als Text aus (für n8n Execute Command Node)
"""

import sys
import json

def get_transcript(video_id: str) -> dict:
    """Hole YouTube-Transkript für eine Video-ID."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        api = YouTubeTranscriptApi()
        result = api.fetch(video_id)
        
        # Extrahiere nur den Text
        transcript = ' '.join([s.text for s in result.snippets])
        
        return {
            "success": True,
            "video_id": video_id,
            "transcript": transcript,
            "language": result.language,
            "length": len(transcript)
        }
    except Exception as e:
        return {
            "success": False,
            "video_id": video_id,
            "error": str(e),
            "transcript": ""
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Keine Video-ID angegeben"}))
        sys.exit(1)
    
    video_id = sys.argv[1]
    result = get_transcript(video_id)
    print(json.dumps(result))
