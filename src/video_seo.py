import json
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

class VideoSEOAnalyzer:
    """
    Comprehensive Video SEO Module for the SEO/GEO Framework.
    Handles video analysis, schema generation, YouTube API payloads, and metadata optimization.
    """

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialize the Video SEO Analyzer.
        
        Args:
            api_keys: Optional dictionary of API keys (e.g., YouTube Data API, LLM API).
        """
        self.api_keys = api_keys or {}

    def analyze_video_seo(self, video_url: str) -> Dict[str, Any]:
        """
        Perform a full SEO analysis of an existing video url.
        
        Args:
            video_url: The URL of the video (e.g., YouTube, Vimeo).
            
        Returns:
            Dictionary containing the SEO score, missing elements, and optimization tips.
        """
        # Placeholder for actual scraping/API extraction logic
        return {
            "video_url": video_url,
            "seo_score": 75,
            "status": "Needs Optimization",
            "findings": [
                "Title length is optimal (under 60 characters).",
                "Description lacks timestamps/chapters.",
                "Missing exact match keyword in the first 25 words of the description.",
                "Tags are underutilized.",
            ],
            "recommendations": [
                "Add chapter markers (e.g., 00:00 Intro).",
                "Include primary keyword in the first sentence of the description.",
                "Add a clear Call-to-Action (CTA) and relevant links."
            ]
        }

    def generate_video_title(self, keyword: str) -> List[str]:
        """
        Generate optimized SEO titles for a video based on a target keyword.
        
        Args:
            keyword: The primary focus keyword.
            
        Returns:
            List of suggested video titles.
        """
        # In a fully integrated system, this would call an LLM (e.g., MasterCopywriter).
        # Returning rule-based templates for the framework.
        capitalized_kw = keyword.title()
        return [
            f"{capitalized_kw} Explained in {datetime.now().year}",
            f"How to Master {capitalized_kw} (Step-by-Step Guide)",
            f"The Ultimate Guide to {capitalized_kw}",
            f"{capitalized_kw}: Everything You Need to Know",
            f"Top 5 Secrets About {capitalized_kw} You Didn't Know"
        ]

    def generate_video_description(self, keyword: str, content: str) -> str:
        """
        Generate a fully optimized video description.
        
        Args:
            keyword: The target SEO keyword.
            content: A brief summary of the video content.
            
        Returns:
            Formatted description string including timestamps, keywords, and links section.
        """
        description = f"Looking to learn about {keyword}? In this video, we cover everything you need to know.\n\n"
        description += f"{content}\n\n"
        description += "⏱️ Timestamps:\n"
        description += "00:00 - Intro & Overview\n"
        description += f"01:30 - What is {keyword.title()}?\n"
        description += "03:45 - Key Benefits & Strategies\n"
        description += "06:20 - Conclusion & Next Steps\n\n"
        description += "🔗 Helpful Links:\n"
        description += "- Subscribe for more: [Insert Link]\n"
        description += "- Read the full article: [Insert Link]\n\n"
        description += f"#VideoSEO #{keyword.replace(' ', '')} #Tutorial"
        
        return description

    def generate_video_tags(self, keyword: str) -> List[str]:
        """
        Generate a list of SEO-optimized tags for the video.
        
        Args:
            keyword: The main topic or keyword.
            
        Returns:
            List of relevant tags (broad, exact, and long-tail).
        """
        base_keyword = keyword.lower()
        return [
            base_keyword,
            f"{base_keyword} tutorial",
            f"how to {base_keyword}",
            f"{base_keyword} for beginners",
            f"{base_keyword} {datetime.now().year}",
            "guide",
            "tips and tricks",
            "explained"
        ]

    def create_video_schema(self, video_data: Dict[str, Any]) -> str:
        """
        Generate JSON-LD VideoObject schema markup.
        
        Args:
            video_data: Dictionary containing video metadata (name, description, uploadDate, thumbnailUrls, contentUrl).
            
        Returns:
            String representation of the JSON-LD schema.
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": video_data.get("title", "Untitled Video"),
            "description": video_data.get("description", ""),
            "uploadDate": video_data.get("upload_date", datetime.now().isoformat()),
            "thumbnailUrl": video_data.get("thumbnails", []),
            "contentUrl": video_data.get("video_url", ""),
            "embedUrl": video_data.get("embed_url", ""),
            "duration": video_data.get("duration", "PT0M0S"),  # ISO 8601 format
        }
        
        # Add interaction statistics if available
        if "views" in video_data:
            schema["interactionStatistic"] = {
                "@type": "InteractionCounter",
                "interactionType": {"@type": "WatchAction"},
                "userInteractionCount": video_data["views"]
            }

        return json.dumps(schema, indent=2)

    def generate_srt_captions(self, transcript: List[Dict[str, Any]]) -> str:
        """
        Generate SRT formatted captions from a transcript list.
        
        Args:
            transcript: List of dicts with 'start' (float seconds), 'end' (float seconds), and 'text' (string).
            
        Returns:
            String containing the formatted SRT content.
        """
        def format_time(seconds: float) -> str:
            td = timedelta(seconds=seconds)
            # timedelta string format: 'H:MM:SS.mmmmmm'
            time_str = str(td)
            if '.' in time_str:
                base, ms = time_str.split('.')
                ms = ms[:3].ljust(3, '0')
            else:
                base = time_str
                ms = '000'
            # Ensure Hours is at least two digits
            if len(base.split(':')[0]) == 1:
                base = '0' + base
            return f"{base},{ms}"

        srt_lines = []
        for index, segment in enumerate(transcript, start=1):
            start_time = format_time(segment.get('start', 0.0))
            end_time = format_time(segment.get('end', 0.0))
            text = segment.get('text', '').strip()
            
            srt_lines.append(str(index))
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text)
            srt_lines.append("")  # Empty line between segments
            
        return "\n".join(srt_lines)

    def optimize_thumbnail(self, thumbnail_url: str) -> Dict[str, Any]:
        """
        Analyze and suggest optimizations for a video thumbnail.
        
        Args:
            thumbnail_url: URL or path of the thumbnail image.
            
        Returns:
            Dictionary with optimization feedback.
        """
        # Simulated analysis for the framework
        return {
            "thumbnail_url": thumbnail_url,
            "status": "Analyzed",
            "contrast_ratio": "High (Good)",
            "text_readability": "Needs Improvement",
            "recommendations": [
                "Ensure text takes up no more than 30% of the image.",
                "Use high-contrast colors (e.g., Yellow on Black) for text.",
                "Include a human face expressing emotion if applicable.",
                "Keep resolution at 1280x720 (16:9 aspect ratio)."
            ]
        }

    def analyze_video_serp(self, keyword: str) -> Dict[str, Any]:
        """
        Analyze Google Search Results (SERP) for Video Carousels on a given keyword.
        
        Args:
            keyword: The target keyword.
            
        Returns:
            Dictionary with SERP Video insights.
        """
        return {
            "keyword": keyword,
            "has_video_carousel": True,
            "average_video_length": "08:45",
            "top_ranking_channels": ["Channel A", "Channel B"],
            "key_moments_present": True,
            "opportunity": "High - Create an 8-10 minute video with clear chapters to rank in Key Moments."
        }

    def create_youtube_payload(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a payload compatible with the YouTube Data API v3 (videos.insert).
        
        Args:
            video_data: Dictionary containing normalized video metadata.
            
        Returns:
            Dictionary representing the YouTube API request body.
        """
        return {
            "snippet": {
                "title": video_data.get("title", "")[:100],  # YouTube title limit
                "description": video_data.get("description", "")[:5000],  # YouTube description limit
                "tags": video_data.get("tags", [])[:500],  # Character limit across all tags
                "categoryId": video_data.get("category_id", "22"),  # 22 = People & Blogs
                "defaultLanguage": "en"
            },
            "status": {
                "privacyStatus": video_data.get("privacy", "private"),
                "selfDeclaredMadeForKids": video_data.get("made_for_kids", False)
            }
        }

    def chunk_and_optimize_transcript(
        self, 
        transcript: Union[str, List[Dict[str, Any]]], 
        keywords: List[str],
        max_chunk_words: int = 150,
        time_gap_threshold: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Chunks a video transcript into semantic paragraphs (chapters)
        and optimizes them by inserting keywords or proposing keyword placements.
        """
        # Standardize format if transcript is a string
        if isinstance(transcript, str):
            words = transcript.split()
            mock_segments = []
            words_per_segment = 15
            for i in range(0, len(words), words_per_segment):
                seg_words = words[i:i + words_per_segment]
                mock_segments.append({
                    "start": float(i / words_per_segment) * 5.0,
                    "end": float(min(len(words), i + words_per_segment) / words_per_segment) * 5.0,
                    "text": " ".join(seg_words)
                })
            transcript = mock_segments

        if not transcript:
            return []
            
        chunks = []
        current_chunk = []
        current_words = 0
        
        for i, segment in enumerate(transcript):
            current_chunk.append(segment)
            current_words += len(segment.get("text", "").split())
            
            # Check for split conditions
            should_split = False
            if current_words >= max_chunk_words:
                should_split = True
            elif i < len(transcript) - 1:
                next_start = transcript[i+1].get("start", 0.0)
                curr_end = segment.get("end", 0.0)
                if next_start - curr_end >= time_gap_threshold:
                    should_split = True
                    
            if should_split or i == len(transcript) - 1:
                # Compile chunk
                chunk_text = " ".join([seg.get("text", "").strip() for seg in current_chunk])
                start_time = current_chunk[0].get("start", 0.0)
                end_time = current_chunk[-1].get("end", 0.0)
                
                missing_keywords = [kw for kw in keywords if kw.lower() not in chunk_text.lower()]
                optimized_text = chunk_text
                keyword_placements = []
                
                if missing_keywords:
                    primary_kw = missing_keywords[0]
                    if len(chunk_text) > 0:
                        optimized_text = f"Speaking of {primary_kw.lower()}, {chunk_text[0].lower() + chunk_text[1:]}"
                    else:
                        optimized_text = f"Speaking of {primary_kw.lower()}."
                    keyword_placements.append({
                        "keyword": primary_kw,
                        "type": "natural_insertion",
                        "context": f"Speaking of {primary_kw.lower()}..."
                    })
                    
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "start": start_time,
                    "end": end_time,
                    "original_text": chunk_text,
                    "optimized_text": optimized_text,
                    "keyword_placements": keyword_placements,
                    "missing_keywords": missing_keywords[1:] if len(missing_keywords) > 1 else []
                })
                
                current_chunk = []
                current_words = 0
                
        return chunks

    def get_video_seo_report(self, video_url: str, keyword: str = "", transcript: Optional[Union[str, List[Dict[str, Any]]]] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive Video SEO report by orchestrating multiple analyses.
        
        Args:
            video_url: The URL of the video.
            keyword: The target keyword (optional).
            transcript: Optional transcript input to optimize.
            
        Returns:
            A complete dictionary report combining all SEO facets.
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "video_url": video_url,
            "target_keyword": keyword,
            "base_analysis": self.analyze_video_seo(video_url)
        }
        
        if keyword:
            report["title_suggestions"] = self.generate_video_title(keyword)
            report["serp_analysis"] = self.analyze_video_serp(keyword)
            report["suggested_tags"] = self.generate_video_tags(keyword)
            
        if transcript and keyword:
            report["optimized_transcript"] = self.chunk_and_optimize_transcript(transcript, [keyword])
            
        report["thumbnail_analysis"] = self.optimize_thumbnail("mock_thumbnail.jpg")
        
        return report

# Example usage within the framework:
if __name__ == "__main__":
    seo_analyzer = VideoSEOAnalyzer()
    keyword = "Python Video SEO"
    
    # Generate description
    desc = seo_analyzer.generate_video_description(keyword, "Learn how to optimize your videos programmatically.")
    print("Generated Description:\n", desc)
    
    # Generate Schema
    schema = seo_analyzer.create_video_schema({
        "title": "Python Video SEO Mastery",
        "description": desc,
        "duration": "PT5M30S",
        "video_url": "https://youtube.com/watch?v=mock123"
    })
    print("\nVideo Schema:\n", schema)
    
    # Generate SRT
    srt = seo_analyzer.generate_srt_captions([
        {"start": 0.0, "end": 2.5, "text": "Welcome to the tutorial."},
        {"start": 2.5, "end": 5.0, "text": "Today we learn Video SEO."}
    ])
    print("\nSRT Output:\n", srt)
    
    # Full Report
    report = seo_analyzer.get_video_seo_report("https://youtube.com/watch?v=mock123", keyword)
    print("\nFull Report Keys:", list(report.keys()))
