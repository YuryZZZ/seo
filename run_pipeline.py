import asyncio
import os
import json
import logging
from src.orchestrator import SEOGEOOrchestrator
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    
    # We will use keys from the environment if present
    api_keys = {
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "google_cx": os.getenv("GOOGLE_CX"),
        "brave_api_key": os.getenv("BRAVE_SEARCH_API_KEY"),
        "tavily_api_key": os.getenv("TAVILY_API_KEY"),
        "perplexity_api_key": os.getenv("PERPLEXITY_API_KEY"),
        "glm_api_key": os.getenv("GLM_API_KEY"),
        "gsc_api_key": os.getenv("GSC_API_KEY"),
        "openai_api_key": os.getenv("OPENAI_API_KEY")
    }

    orchestrator = SEOGEOOrchestrator(api_keys=api_keys)

    initial_data = {
        "target_url": "https://auth0.com",
        "target_keywords": ["SEO Architecture", "Website Content Architecture", "Technical SEO Structure"],
        "geo_locations": ["Global"],
        "focus_keyword": "SEO Architecture"
    }

    logger.info(f"Starting production execution for: {initial_data['target_url']}")
    
    # Run the pipeline to get the blueprint
    results = await orchestrator.execute_full_pipeline(initial_data)
    
    # Save the output
    output_path = "pipeline_output.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Pipeline blueprint complete! Output saved to {output_path}")

    logger.info("Starting Phase 10: Waterfall Content Generation (Target ~6,000 words)")
    
    # Extract blueprint artifacts
    phase_3 = results.get("results", {}).get("phase_3", {})
    h2_sections = phase_3.get("h2_questions", [])
    citable_blocks = phase_3.get("citable_blocks", {})
    if not isinstance(citable_blocks, dict):
        citable_blocks = {}
    
    if not h2_sections:
        logger.warning("No H2 sections found in Phase 3. Falling back to default headers.")
        h2_sections = ["Introduction", "Core Concepts", "Implementation", "Best Practices", "Conclusion"]

    from src.prompts.dynamic_prompt_engine import DynamicPromptEngine, TopicContext
    from src.master_copywriter import MasterCopywriter
    from src.llm_client import LLMClient

    engine = DynamicPromptEngine()
    llm_client = LLMClient(provider="google", model="gemini-2.5-flash")
    copywriter = MasterCopywriter(config=api_keys, llm_client=llm_client)

    # We will waterfall generate section by section
    final_article = f"# {initial_data['target_keywords'][0]}\n\n"
    
    # Insert table of contents if available
    if phase_3.get('table_of_contents'):
        final_article += "## Table of Contents\n\n"
        final_article += phase_3.get('table_of_contents') + "\n\n"

    for i, h2 in enumerate(h2_sections):
        logger.info(f"Generating content for section {i+1}/{len(h2_sections)}: {h2}")
        
        # Build context for this specific section
        block_hint = citable_blocks.get(h2, {}).get("structure_suggestion", "")
        
        context = TopicContext(
            keyword=initial_data["focus_keyword"],
            topic=h2,  # Focus the AI on this specific H2 topic for the section
            service_or_product="",
            target_audience="Technical practitioners and advanced SEO professionals",
            user_intent="informational",
            min_word_count=5000,
            target_word_count=8000,
            tone="authoritative and highly actionable",
            expertise_level="advanced"
        )
        
        system_prompt = engine.generate_system_prompt(context)
        
        # Custom user prompt for step-by-step waterfall construction
        user_prompt = (
            f"You are writing a comprehensive, expert-level article.\n"
            f"Please write the content for the following H2 section ONLY: '{h2}'.\n\n"
            f"Requirements:\n"
            f"- Output at least 600-800 words for this section to ensure the final aggregated article hits our 8,000 word target.\n"
            f"- Use deep technical insights, avoid fluff.\n"
            f"- DO NOT write introductory greetings, closing conclusions, or repeat the H1 title.\n"
        )
        
        if block_hint:
             user_prompt += f"- Critical Requirement: {block_hint}\n"
             
        # Combine system prompt + user prompt directly (MasterCopywriter supports standard string prompts)
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        section_content = copywriter._generate_with_client(full_prompt, max_tokens=2000)
        
        if section_content:
            final_article += f"## {h2}\n\n{section_content}\n\n"
        else:
            final_article += f"## {h2}\n\n[Content Generation Failed - Verify OpenAI Key]\n\n"

    # Save to disk
    article_path = "final_article.md"
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(final_article)
        
    logger.info(f"Waterfall content generation complete! Full article saved to {article_path}")

if __name__ == "__main__":
    asyncio.run(main())
