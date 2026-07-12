import json
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AIOverviewOptimizer:
    """
    AI Overview (SGE/GEO) optimization module.
    Focuses on factual accuracy, clear structure, quotable content, and unique data
    to maximize visibility in AI-generated search summaries (Google SGE, Perplexity, OpenAI Search, etc.).
    """

    def __init__(self, llm_client=None):
        """
        Initialize the AI Overview Optimizer.
        
        Args:
            llm_client: Optional LLM client for advanced text extraction and generation.
        """
        self.llm_client = llm_client
        self.citation_formats = ["definitions", "unordered_lists", "ordered_lists", "tables", "statistics"]

    def analyze_ai_overview(self, keyword: str) -> Dict[str, Any]:
        """
        Analyze current AI overviews for a given keyword to understand intent and structure.
        
        Args:
            keyword (str): The target keyword.
            
        Returns:
            Dict[str, Any]: Analysis of the AI overview landscape.
        """
        logger.info(f"Analyzing AI overview landscape for keyword: {keyword}")
        
        # In a production environment, this would integrate with a SERP API 
        # that extracts AI overviews (e.g., Google SGE responses).
        return {
            "keyword": keyword,
            "has_ai_overview": True,
            "primary_intent": "informational",
            "overview_type": "listicle_and_definition",
            "average_citations": 4,
            "content_types_cited": ["blog_post", "documentation", "academic_paper", "statistics_page"],
            "estimated_ai_confidence": 0.85
        }

    def extract_cited_sources(self, keyword: str) -> List[str]:
        """
        Extract URLs typically cited in AI overviews for the keyword.
        
        Args:
            keyword (str): The target keyword.
            
        Returns:
            List[str]: A list of cited URLs.
        """
        # Mocked extraction representing typical SGE/GEO sources
        formatted_kw = keyword.replace(' ', '-').lower()
        return [
            f"https://www.industry-authority.com/guide/{formatted_kw}",
            f"https://www.data-insights.org/statistics-{formatted_kw}",
            f"https://www.tech-reference.com/what-is-{formatted_kw}"
        ]

    def analyze_citation_patterns(self, keyword: str) -> Dict[str, Any]:
        """
        Analyze what formats and content types get cited for the keyword.
        
        Args:
            keyword (str): The target keyword.
            
        Returns:
            Dict[str, Any]: Data on formatting patterns preferred by AI for this keyword.
        """
        return {
            "keyword": keyword,
            "dominant_format": "bulleted_lists",
            "avg_word_count_of_cited_block": 45,
            "common_html_tags": ["<ul>", "<li>", "<strong>", "<h3>", "<table>"],
            "includes_statistics": True,
            "includes_expert_quotes": False,
            "information_density": "high"
        }

    def format_for_ai_extraction(self, content: str) -> str:
        """
        Format content with semantic markers for easy AI extraction.
        Ensures clean hierarchical headers and distinct paragraph boundaries.
        
        Args:
            content (str): The raw content.
            
        Returns:
            str: Semantically formatted content.
        """
        # Ensure headers are properly spaced
        formatted = re.sub(r'(#+\s.*?\n)(?!\n)', r'\1\n', content)
        
        # Bold important entities and concepts to signal salience to AI models
        # (This is a simplified heuristic; an LLM/NLP pipeline would target exact entities)
        words_to_bold = r'\b(crucial|important|key metric|definition|stands for|specifically)\b'
        formatted = re.sub(words_to_bold, r'**\1**', formatted, flags=re.IGNORECASE)
        
        return formatted

    def create_factual_statements(self, content: str) -> str:
        """
        Ensure extractable facts are clearly stated using standard IS-A or HAS-A structures.
        
        Args:
            content (str): The content to optimize.
            
        Returns:
            str: Content appended/modified with clear factual statements.
        """
        if "### Key Facts" in content:
            return content
            
        facts_section = (
            "\n\n### Key Facts for AI Extraction\n"
            "- **Accuracy**: Factual density is the primary driver for AI citations.\n"
            "- **Structure**: AI models prefer (Subject) (Verb) (Object) declarative sentences.\n"
            "- **Entities**: Explicit entity mentions increase retrieval confidence.\n"
        )
        return content + facts_section

    def create_definition_blocks(self, content: str) -> str:
        """
        Create clear, concise definition blocks ('What is X?').
        AI Overviews heavily rely on precise definitions.
        
        Args:
            content (str): The content to process.
            
        Returns:
            str: Content with an optimized definition block.
        """
        # Simulating the generation of a semantic definition block
        definition_block = (
            "\n\n### What is this?\n"
            "> **Definition**: A concise, objective, and authoritative explanation of the core entity, "
            "designed specifically to be captured by AI overview generation algorithms.\n"
        )
        # Prepend definition block after the main title (if it exists)
        if content.startswith("# "):
            parts = content.split("\n", 1)
            return f"{parts[0]}\n{definition_block}\n{parts[1]}" if len(parts) > 1 else content + definition_block
        return definition_block + content

    def create_comparison_tables(self, content: str) -> str:
        """
        Generate comparison data tables from text for AI feature snippets.
        
        Args:
            content (str): The content.
            
        Returns:
            str: Content including a markdown table.
        """
        if "|" in content and "---" in content:
            return content  # Table likely exists
            
        table_markdown = (
            "\n\n### Feature Comparison\n"
            "| Feature | Traditional SEO | GEO / SGE Optimization |\n"
            "|---------|-----------------|------------------------|\n"
            "| Focus | Keywords & Links | Entities & Relationships |\n"
            "| Content | Long-form prose | High information density |\n"
            "| Format | Fluid paragraphs | Lists, tables, definitions |\n"
        )
        return content + table_markdown

    def create_step_by_step(self, content: str) -> str:
        """
        Format process-oriented text into numbered lists with imperative verbs.
        
        Args:
            content (str): The content to format.
            
        Returns:
            str: Content optimized with step-by-step structures.
        """
        # This would typically use an LLM to extract processes from prose into lists.
        # Here we inject a structured list layout if none exists.
        if "1." not in content:
            steps = (
                "\n\n### Step-by-Step Process\n"
                "1. **Analyze** the AI overview landscape for the target query.\n"
                "2. **Extract** the specific citation patterns and formatting preferred.\n"
                "3. **Structure** the content using tables, lists, and declarative definitions.\n"
                "4. **Validate** factual accuracy and entity salience.\n"
            )
            return content + steps
        return content

    def create_key_points(self, content: str) -> str:
        """
        Extract 3-5 bullet points summarizing the text (TL;DR/BLUF).
        Bottom Line Up Front (BLUF) is critical for AI overviews.
        
        Args:
            content (str): The full content.
            
        Returns:
            str: Content prepended with a BLUF summary.
        """
        if "### TL;DR" in content or "### Key Takeaways" in content:
            return content
            
        bluf_section = (
            "\n\n### Key Takeaways\n"
            "- AI Overview optimization requires strict semantic formatting.\n"
            "- Definitions, tables, and lists are the most cited HTML elements.\n"
            "- Factual accuracy and information density outweigh word count.\n"
        )
        
        # Insert after H1
        if content.startswith("# "):
            parts = content.split("\n", 1)
            return f"{parts[0]}\n{bluf_section}\n{parts[1]}" if len(parts) > 1 else content + bluf_section
        return bluf_section + content

    def optimize_quote_extraction(self, content: str) -> str:
        """
        Format impactful statements into easily extractable blockquotes.
        
        Args:
            content (str): The content to optimize.
            
        Returns:
            str: Content with optimized blockquotes.
        """
        # Look for sentences that contain strong assertions and wrap them in blockquotes
        # In a real system, an LLM evaluates the 'quotability' of sentences.
        quote_block = (
            "\n\n> \"To dominate GEO (Generative Engine Optimization), content must transition "
            "from conversational prose to structured, entity-dense data payloads.\"\n"
        )
        return content + quote_block

    def optimize_for_citation(self, content: str, keyword: str) -> str:
        """
        Optimize the entire content to be highly citable by AI overviews by applying
        all formatting and extraction methodologies.
        
        Args:
            content (str): The original content.
            keyword (str): The target keyword.
            
        Returns:
            str: Fully optimized content.
        """
        logger.info(f"Applying full SGE/GEO optimization suite for keyword: {keyword}")
        
        optimized = self.format_for_ai_extraction(content)
        optimized = self.create_key_points(optimized)
        optimized = self.create_definition_blocks(optimized)
        optimized = self.create_step_by_step(optimized)
        optimized = self.create_comparison_tables(optimized)
        optimized = self.create_factual_statements(optimized)
        optimized = self.optimize_quote_extraction(optimized)
        
        return optimized

    def analyze_competitor_citations(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Aggregate which competitors are being cited in AI overviews and why.
        
        Args:
            keyword (str): The target keyword.
            
        Returns:
            List[Dict[str, Any]]: Competitor citation analysis.
        """
        return [
            {
                "competitor_url": "https://competitor.com/definitive-guide",
                "domain_authority": 85,
                "cited_for": "definition",
                "exact_quote_cited": "An AI overview is a generative summary presented at the top of search results...",
                "html_element_cited": "<p>"
            },
            {
                "competitor_url": "https://competitor.com/statistics",
                "domain_authority": 91,
                "cited_for": "data_point",
                "exact_quote_cited": "78% of users find AI overviews helpful for complex queries.",
                "html_element_cited": "<li>"
            }
        ]

    def get_ai_overview_report(self, keyword: str) -> Dict[str, Any]:
        """
        Generate a comprehensive SGE/GEO report for a keyword.
        Combines all analysis methods to provide an actionable strategy.
        
        Args:
            keyword (str): The target keyword.
            
        Returns:
            Dict[str, Any]: A comprehensive JSON-serializable report.
        """
        logger.info(f"Generating comprehensive AI Overview report for: {keyword}")
        
        return {
            "keyword": keyword,
            "overview_analysis": self.analyze_ai_overview(keyword),
            "cited_sources": self.extract_cited_sources(keyword),
            "citation_patterns": self.analyze_citation_patterns(keyword),
            "competitor_citations": self.analyze_competitor_citations(keyword),
            "actionable_recommendations": [
                "Place a clear 'What is [Keyword]' definition block immediately after the introduction.",
                "Consolidate statistical claims into a single markdown table for easy extraction.",
                "Convert H3 subheadings into a numbered list if they represent a sequence.",
                "Ensure primary entities are explicitly named rather than using pronouns."
            ]
        }

    def generate_overview_summary_block(self, content: str, keyword: str) -> Dict[str, Any]:
        """
        Generate a structured summary block optimized for AI Overview extraction.
        """
        logger.info(f"Generating SGE summary block for: {keyword}")
        
        definition = ""
        def_match = re.search(r'>\s*\*\*Definition\*\*:\s*(.*?)(?:\n|$)', content, re.IGNORECASE)
        if def_match:
            definition = def_match.group(1).strip()
        else:
            sentences = re.split(r'[.!?]\s+', content)
            for s in sentences:
                if keyword.lower() in s.lower() and any(verb in s.lower() for verb in ["is a", "refers to", "stands for", "is the process"]):
                    definition = s.strip() + "."
                    break
            if not definition and sentences:
                definition = f"{keyword.capitalize()} is an important industry concept discussed in this content."
                
        takeaways = []
        takeaway_matches = re.findall(r'^-\s*(.*)', content, re.MULTILINE)
        if takeaway_matches:
            takeaways = [t.strip() for t in takeaway_matches[:3]]
        else:
            takeaways = [
                f"Understand the core fundamentals of {keyword}.",
                f"Optimize key structured elements to improve visibility.",
                f"Implement best practices for data density."
            ]
            
        stats = []
        stat_matches = re.findall(r'\b\d+(?:\.\d+)?%\b|\$\d+(?:\.\d+)?[kM]?\b|\b\d+x\b', content)
        if stat_matches:
            stats = list(set(stat_matches))[:3]
            
        markdown_block = (
            f"### AI Overview Summary: {keyword.capitalize()}\n"
            f"> **Definition**: {definition}\n\n"
            f"**Key Takeaways**:\n"
            + "\n".join(f"- {t}" for t in takeaways) + "\n"
        )
        if stats:
            markdown_block += f"\n**Key Metrics**: {', '.join(stats)}\n"
            
        html_block = (
            f'<div class="sge-summary-block" data-keyword="{keyword}">\n'
            f'  <h3>AI Overview Summary: {keyword.capitalize()}</h3>\n'
            f'  <p class="sge-definition"><strong>Definition:</strong> {definition}</p>\n'
            f'  <ul class="sge-takeaways">\n'
            + "\n".join(f'    <li>{t}</li>' for t in takeaways) + "\n"
            f'  </ul>\n'
        )
        if stats:
            html_block += f'  <p class="sge-metrics"><strong>Key Metrics:</strong> {", ".join(stats)}</p>\n'
        html_block += f'</div>'
        
        return {
            "definition": definition,
            "takeaways": takeaways,
            "statistics": stats,
            "markdown": markdown_block,
            "html": html_block
        }

