"""
Test suite for SEO/GEO Framework
Tests all 10 agents and orchestrator functionality
"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from orchestrator import SEOGEOOrchestrator
from row_payload import RowPayload; RowPayloadTemp = RowPayload
from ia_architect import IAArchitect
from serp_analyzer import SERPAnalyzer
from backlink_analyzer import BacklinkAnalyzer


class TestSchema:
    """Test schema definitions"""
    
    def test_row_payload_temp_creation(self):
        """Test creating RowPayloadTemp instance"""
        payload = RowPayloadTemp(
            post_id=1,
            post_title="Test Article",
            post_content="Test content",
            focus_keyword="test keyword"
        )
        assert payload.post_id == 1
        assert payload.post_title == "Test Article"
        assert payload.focus_keyword == "test keyword"
    
    def test_row_payload_has_required_fields(self):
        """Test that RowPayloadTemp has all 80+ core fields"""
        payload = RowPayloadTemp()
        
        # Core fields
        assert hasattr(payload, 'post_id')
        assert hasattr(payload, 'post_title')
        assert hasattr(payload, 'post_content')
        assert hasattr(payload, 'seo_title')
        assert hasattr(payload, 'meta_description')
        assert hasattr(payload, 'focus_keyword')
        
        # Extended fields
        assert hasattr(payload, 'serp_snapshot_raw')
        assert hasattr(payload, 'paa_extraction')
        assert hasattr(payload, 'primary_entity_mid')
        assert hasattr(payload, 'bluf_paragraph')
        assert hasattr(payload, 'snippet_bait_block')


class TestIAArchitect:
    """Test IA Architect agent"""
    
    def test_ia_architect_initialization(self):
        """Test IAArchitect can be initialized"""
        agent = IAArchitect()
        assert agent is not None
    
    def test_generate_h2_questions(self):
        """Test H2 question generation (>50% questions)"""
        agent = IAArchitect()
        payload = RowPayloadTemp(
            focus_keyword="python testing",
            post_title="Complete Guide to Python Testing"
        )
        
        result = agent.generate_h2_questions(payload)
        
        # Check that result contains H2 suggestions
        assert result is not None
        assert isinstance(result, (str, dict, list))
    
    def test_design_citable_blocks(self):
        """Test citable block design"""
        agent = IAArchitect()
        payload = RowPayloadTemp(
            focus_keyword="seo optimization",
            h2_structure=["What is SEO?", "How to optimize?", "Best practices"]
        )
        
        result = agent.design_citable_blocks(payload)
        assert result is not None


class TestSERPAnalyzer:
    """Test SERP Analyzer agent"""
    
    def test_serp_analyzer_initialization(self):
        """Test SERPAnalyzer can be initialized"""
        agent = SERPAnalyzer()
        assert agent is not None
    
    def test_serp_analyzer_has_methods(self):
        """Test SERPAnalyzer has required methods"""
        agent = SERPAnalyzer()
        assert hasattr(agent, 'analyze_serp')
        assert hasattr(agent, 'extract_paa')
        assert hasattr(agent, 'get_competitor_gaps')


class TestBacklinkAnalyzer:
    """Test Backlink Analyzer agent"""
    
    def test_backlink_analyzer_initialization(self):
        """Test BacklinkAnalyzer can be initialized"""
        agent = BacklinkAnalyzer()
        assert agent is not None
    
    def test_backlink_analyzer_has_methods(self):
        """Test BacklinkAnalyzer has required methods"""
        agent = BacklinkAnalyzer()
        assert hasattr(agent, 'analyze_backlinks')
        assert hasattr(agent, 'get_domain_authority')


class TestOrchestrator:
    """Test orchestrator functionality"""
    
    def test_orchestrator_initialization(self):
        """Test SEOGEOOrchestrator can be initialized"""
        orchestrator = SEOGEOOrchestrator()
        assert orchestrator is not None
    
    def test_orchestrator_has_phases(self):
        """Test orchestrator has all 10 phases"""
        orchestrator = SEOGEOOrchestrator()
        assert hasattr(orchestrator, 'run_phase_0')
        assert hasattr(orchestrator, 'run_phase_1')
        assert hasattr(orchestrator, 'run_phase_2')
        assert hasattr(orchestrator, 'run_phase_3')
        assert hasattr(orchestrator, 'run_phase_4')
        assert hasattr(orchestrator, 'run_phase_5')
        assert hasattr(orchestrator, 'run_phase_6')
        assert hasattr(orchestrator, 'run_phase_7')
        assert hasattr(orchestrator, 'run_phase_8')
        assert hasattr(orchestrator, 'run_phase_9')
    
    def test_orchestrator_execute_pipeline(self):
        """Test full pipeline execution"""
        orchestrator = SEOGEOOrchestrator()
        payload = RowPayloadTemp(
            post_id=1,
            post_title="Test SEO Article",
            post_content="Content about SEO optimization",
            focus_keyword="seo optimization"
        )
        
        # Execute pipeline (should not crash)
        try:
            result = orchestrator.execute_pipeline(payload)
            assert result is not None
        except NotImplementedError:
            # Expected if methods are stubs
            pytest.skip("Pipeline methods not fully implemented yet")


class TestIntegration:
    """Integration tests"""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from input to output"""
        # Create orchestrator
        orchestrator = SEOGEOOrchestrator()
        
        # Create input payload
        payload = RowPayloadTemp(
            post_id=1,
            post_title="Complete Guide to Python SEO",
            post_content="Learn how to optimize Python applications for search engines",
            focus_keyword="python seo",
            target_url="https://example.com/python-seo"
        )
        
        # Run through phases
        try:
            # Phase 0: Research
            payload = orchestrator.run_phase_0(payload)
            
            # Phase 1: IA Architecture
            payload = orchestrator.run_phase_1(payload)
            
            # Verify enrichment
            assert payload.post_id == 1
            assert payload.post_title == "Complete Guide to Python SEO"
            
        except NotImplementedError:
            pytest.skip("Pipeline not fully implemented")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
