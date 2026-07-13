import pytest
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.entity_extractor import EntityExtractor
from src.schema_generator import SchemaGenerator
from src.content_generator import ContentGenerator
from src.orchestrator import SEOGEOOrchestrator


class TestEntityKnowledgeGraph:
    """Tests the entity extraction, wikidata mapping, graph export, LSI logic, and orchestrator wiring."""

    def test_ner_fallback_extraction(self):
        extractor = EntityExtractor()
        text = "Google Cloud SQL and AlloyDB are running on Kubernetes GKE clusters in California."
        
        entities = extractor.extract_entities(text)
        assert len(entities) > 0
        
        # Verify specific entities matched by regex fallback
        entity_texts = [ent["text"] for ent in entities]
        assert "Google Cloud SQL" in entity_texts or "Cloud SQL" in [e.replace("Google ", "") for e in entity_texts]
        assert "AlloyDB" in entity_texts
        assert "Kubernetes GKE" in entity_texts or "GKE" in entity_texts

    def test_wikidata_mapping(self):
        extractor = EntityExtractor()
        entities = ["google", "alloydb", "kubernetes"]
        
        mapping = extractor.map_entities_to_wikidata(entities)
        assert mapping["google"] == "Q95"
        assert mapping["alloydb"] == "Q112224854"
        assert mapping["kubernetes"] == "Q21075058"

    def test_knowledge_graph_export(self):
        extractor = EntityExtractor()
        entities = ["Google", "AlloyDB", "GKE"]
        
        graph_json = extractor.export_knowledge_graph_json(entities)
        graph = json.loads(graph_json)
        
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) == 3
        assert len(graph["edges"]) == 3  # co-occurrence edges (3 * 2 / 2)

    def test_about_and_mentions_schemas(self):
        schema_entities = [
            {
                "type": "Thing",
                "name": "AlloyDB",
                "same_as": ["https://www.wikidata.org/wiki/Q112224854"]
            }
        ]
        
        about = SchemaGenerator.generate_about_page_schema(
            entities=schema_entities,
            page_url="https://example.com/alloydb",
            page_name="AlloyDB Details"
        )
        
        assert about["@type"] == "AboutPage"
        assert about["url"] == "https://example.com/alloydb"
        assert about["about"][0]["name"] == "AlloyDB"
        assert "Q112224854" in about["about"][0]["sameAs"][0]
        
        mentions = SchemaGenerator.generate_mentions_schema(schema_entities)
        assert len(mentions) == 1
        assert mentions[0]["name"] == "AlloyDB"

    def test_content_generator_lsi_prompt(self):
        # We verify that LSI entities are incorporated into the cache key / logic of ContentGenerator
        # We mock the LLM client to return a simple block and check parameters
        class MockLLM:
            def generate(self, prompt, **kwargs):
                self.last_prompt = prompt
                return 'Mocked content with AlloyDB and GKE.'
                
        llm = MockLLM()
        generator = ContentGenerator(llm_client=llm)
        
        block = generator.generate_content_block(
            h2="Deployment Strategy",
            context={},
            keywords=["deploy"],
            word_count=50,
            entities=["AlloyDB", "GKE"]
        )
        
        assert "AlloyDB" in llm.last_prompt
        assert "GKE" in llm.last_prompt
        assert block.content == 'Mocked content with AlloyDB and GKE.'

    @pytest.mark.asyncio
    async def test_orchestrator_phase_4_entities(self):
        orchestrator = SEOGEOOrchestrator()
        
        # Run Phase 4 content optimization
        phase_data = {
            "focus_keyword": "alloydb",
            "target_url": "Deploying AlloyDB Omni containers on GKE clusters."
        }
        
        result = await orchestrator.execute_phase(4, phase_data)
        
        assert result["status"] == "completed"
        assert "entities" in result
        assert "wikidata_mapping" in result
        assert "entity_graph" in result
        assert "about_page_schema" in result
        assert "mentions_schema" in result
        
        # Verify entity found and mapped
        found_alloydb = any("alloydb" in e.lower() for e in result["entities"])
        assert found_alloydb
        
        # Verify mapping maps to Q112224854
        alloydb_mapping = next((v for k, v in result["wikidata_mapping"].items() if "alloydb" in k.lower()), None)
        assert alloydb_mapping == "Q112224854"
        
        assert result["about_page_schema"]["@type"] == "AboutPage"
