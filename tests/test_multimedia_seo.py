import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.video_seo import VideoSEOAnalyzer
from src.image_seo import ImageSEOAnalyzer
from src.orchestrator import SEOGEOOrchestrator
from src.schema_generator import SchemaGenerator


class TestMultimediaSEO:
    """Tests the advanced multimedia SEO optimizations for images and videos."""

    def test_video_transcript_chunking_and_optimization(self):
        analyzer = VideoSEOAnalyzer()
        
        # Test timestamped list transcript
        transcript_list = [
            {"start": 0.0, "end": 4.5, "text": "Welcome to our channel."},
            {"start": 4.5, "end": 9.0, "text": "In this video we talk about search engines."},
            {"start": 20.0, "end": 25.0, "text": "This is a new section after a long pause."}
        ]
        
        # Test time-gap chunking (threshold = 10.0s, gap is 11.0s)
        chunks = analyzer.chunk_and_optimize_transcript(
            transcript=transcript_list,
            keywords=["seo", "ranking"],
            max_chunk_words=150,
            time_gap_threshold=10.0
        )
        
        assert len(chunks) == 2
        assert chunks[0]["chunk_id"] == 1
        assert chunks[0]["start"] == 0.0
        assert chunks[0]["end"] == 9.0
        assert "seo" in chunks[0]["optimized_text"].lower()
        
        assert chunks[1]["chunk_id"] == 2
        assert chunks[1]["start"] == 20.0
        assert chunks[1]["end"] == 25.0

        # Test raw string transcript auto-chunking
        raw_text = "Welcome to our video tutorials. Today we will explain how to optimize content. It is important to structure headings correctly. We hope this helps you rank higher on search engines."
        chunks_str = analyzer.chunk_and_optimize_transcript(
            transcript=raw_text,
            keywords=["multimedia seo"],
            max_chunk_words=10  # Low threshold to trigger multiple chunks
        )
        assert len(chunks_str) > 1
        assert any("multimedia seo" in c["optimized_text"].lower() for c in chunks_str)

    def test_image_vision_alt_text_fallback(self):
        analyzer = ImageSEOAnalyzer()
        mock_img_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;" # 1x1 mock gif
        
        alt = analyzer.vision_api_alt_text(
            image_data=mock_img_bytes,
            context="a modern database structure",
            keyword="spanner"
        )
        
        # Should contain keyword or context or detected labels
        assert "depicting" in alt or "graphic showing" in alt or "spanner" in alt
        assert "spanner" in alt

    def test_image_compression_recommendations(self):
        analyzer = ImageSEOAnalyzer()
        mock_img_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        
        recs = analyzer.get_compression_recommendations(mock_img_bytes)
        assert "original_size_kb" in recs
        assert "webp_size_kb" in recs
        assert "savings_kb" in recs
        assert "recommendations" in recs
        assert len(recs["recommendations"]) > 0

    def test_image_metadata_generation(self):
        analyzer = ImageSEOAnalyzer()
        page_context = {
            "keyword": "alloydb omni",
            "primary_heading": "How to Run AlloyDB Omni in a Container"
        }
        
        meta = analyzer.generate_image_metadata(
            page_context=page_context,
            image_url="https://example.com/assets/container_run_illustration.png"
        )
        
        assert meta["seo_filename"] == "how-run-alloydb-omni-container.webp"
        assert "Alloydb Omni" in meta["title"]
        assert len(meta["alt_text"]) > 0
        assert len(meta["caption"]) > 0

    @pytest.mark.asyncio
    async def test_orchestrator_phase_4_multimedia_integration(self):
        # Instantiate orchestrator
        orchestrator = SEOGEOOrchestrator()
        
        # Mock payload with images and videos
        data = {
            "focus_keyword": "cloud sql",
            "title": "Cloud SQL PostgreSQL Guide",
            "target_url": "Here is an image <img src='https://example.com/sql-setup.jpg'> and a video https://youtube.com/watch?v=sql-video",
            "images": [{"url": "https://example.com/sql-setup.jpg"}],
            "videos": [{"url": "https://youtube.com/watch?v=sql-video", "transcript": "Setting up Cloud SQL is fast."}]
        }
        
        result = await orchestrator._phase_4_content_optimization(data)
        
        assert "multimedia_seo" in result
        multimedia = result["multimedia_seo"]
        
        # Verify images
        assert len(multimedia["images"]) == 1
        assert multimedia["images"][0]["url"] == "https://example.com/sql-setup.jpg"
        assert "seo_filename" in multimedia["images"][0]["metadata"]
        
        # Verify videos
        assert len(multimedia["videos"]) == 1
        assert multimedia["videos"][0]["url"] == "https://youtube.com/watch?v=sql-video"
        assert "optimized_transcript" in multimedia["videos"][0]["report"]
        
        # Verify schemas
        assert len(multimedia["schemas"]) == 2
        assert any(s.get("@type") == "ImageObject" for s in multimedia["schemas"])
        assert any(s.get("@type") == "VideoObject" for s in multimedia["schemas"])
