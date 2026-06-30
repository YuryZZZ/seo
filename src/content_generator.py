"""
AI Content Generator for SEO/GEO Framework
Generates SEO-optimized content with E-E-A-T signals
"""
import os
import re
import json
import logging
from dataclasses import asdict, dataclass
from typing import List, Dict, Any, Optional

# New prompts module imports
from .prompts import DynamicPromptEngine, TopicContext, BaseSystemInstruction
from .prompts.eeat_enforcement import EEATEnforcer

try:
    from .cache import cache
except ImportError:
    from cache import cache

logger = logging.getLogger(__name__)


@dataclass
class ContentBlock:
    """A content block (paragraph, list, etc.)"""
    type: str  # 'paragraph', 'list', 'table', 'quote'
    heading: str  # H2 or H3
    content: str
    keywords_used: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetaTags:
    """SEO meta tags"""
    title: str
    description: str
    keywords: List[str]
    canonical_url: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    twitter_card: str = "summary_large_image"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# E-E-A-T Signal Templates
EEAT_PROMPTS = {
    "expertise": "Demonstrate deep knowledge with specific examples, data, and technical details.",
    "experience": "Include first-hand experience, case studies, or practical applications.",
    "authoritativeness": "Reference credible sources, studies, or industry standards.",
    "trustworthiness": "Be transparent about limitations, cite sources, and provide balanced views."
}

# AI Tell Words to Avoid
AI_TELL_WORDS = [
    "delve", "uncover", "unlock", "mastering", "realm", "tapestry",
    "ever-evolving", "in today's digital landscape", "game-changer",
    "revolutionize", "cutting-edge", "leverage", "synergy",
    "comprehensive guide", "ultimate guide", "everything you need to know",
    "at the end of the day", "low-hanging fruit", "paradigm shift"
]


class ContentGenerator:
    """
    AI Content Generator with SEO/GEO optimization.
    
    Generates:
    - H2 outlines from research data
    - BLUF (Bottom Line Up Front) paragraphs
    - Content blocks with E-E-A-T signals
    - Meta tags optimized for CTR
    """
    
    def __init__(self, llm_client=None, provider: str = "openai", **llm_kwargs):
        """
        Initialize content generator.
        
        Args:
            llm_client: Pre-configured LLMClient instance
            provider: LLM provider (if llm_client not provided)
            **llm_kwargs: Additional LLM client options
        """
        if llm_client:
            self.llm = llm_client
        else:
            from .llm_client import LLMClient
            self.llm = LLMClient(provider=provider, **llm_kwargs)

        provider_name = getattr(self.llm, "provider", provider)
        logger.info(f"ContentGenerator initialized with {provider_name}")
    
    def generate_h2_outline(self, research_data: Dict[str, Any], topic: str,
                           num_h2s: int = 7) -> List[str]:
        """
        Generate H2 outline from research data.
        
        Args:
            research_data: Research data from ResearchService
            topic: Main topic
            num_h2s: Number of H2s to generate
            
        Returns:
            List of H2 headings (50%+ should be questions)
        """
        cache_key = f"content:outline:{topic}:{num_h2s}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"H2 Outline Cache HIT for topic: {topic}")
            return cached

        # Extract context from research
        serp_results = research_data.get('serp_results', [])
        paa_questions = research_data.get('paa_questions', [])
        competitor_h2s = []
        
        for comp in research_data.get('competitors', []):
            competitor_h2s.extend(comp.get('h2_tags', []))
        
        prompt = f"""Generate {num_h2s} H2 headings for an article about "{topic}".

REQUIREMENTS:
1. At least 50% ({num_h2s // 2}+) must be QUESTIONS
2. Cover the topic comprehensively
3. Use engaging, click-worthy phrasing
4. Include semantic variations

CONTEXT FROM RESEARCH:
- PAA Questions to Address: {[q.get('question', '') for q in paa_questions[:5]]}
- Competitor H2s: {competitor_h2s[:10]}

OUTPUT FORMAT:
Return ONLY a JSON array of {num_h2s} strings, no other text.
Example: ["What is AI Marketing?", "How AI Transforms Content Strategy", ...]
"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.7, max_tokens=1000)
            
            # Parse JSON response
            h2s = json.loads(response.strip())
            
            # Validate format
            if isinstance(h2s, list) and all(isinstance(h, str) for h in h2s):
                # Ensure 50%+ questions
                question_count = sum(1 for h in h2s if '?' in h)
                if question_count < num_h2s // 2:
                    # Convert some to questions
                    for i in range(len(h2s)):
                        if '?' not in h2s[i]:
                            h2s[i] = f"What About {h2s[i]}?"
                            question_count += 1
                            if question_count >= num_h2s // 2:
                                break
                
                result = h2s[:num_h2s]
                cache.set(cache_key, result)
                return result
            
        except Exception as e:
            logger.error(f"Failed to generate H2 outline: {e}")
        
        # Fallback outline
        fallback = self._generate_fallback_outline(topic, num_h2s)
        cache.set(cache_key, fallback)
        return fallback
    
    def _generate_fallback_outline(self, topic: str, num_h2s: int) -> List[str]:
        """Generate fallback H2 outline"""
        templates = [
            f"What is {topic}?",
            f"Why {topic} Matters in 2025",
            f"How Does {topic} Work?",
            f"Key Benefits of {topic}",
            f"Common {topic} Mistakes to Avoid",
            f"Best Practices for {topic}",
            f"Getting Started with {topic}",
            f"What's Next for {topic}?",
            f"Who Should Use {topic}?",
            f"When to Implement {topic}"
        ]
        return templates[:num_h2s]
    
    def generate_bluf_paragraph(self, topic: str, keywords: List[str],
                               max_sentences: int = 3) -> str:
        """
        Generate BLUF (Bottom Line Up Front) paragraph.
        
        Args:
            topic: Main topic
            keywords: Target keywords
            max_sentences: Maximum sentences
            
        Returns:
            BLUF paragraph string
        """
        cache_key = f"content:bluf:{topic}:{','.join(sorted(keywords))}:{max_sentences}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"BLUF Cache HIT for topic: {topic}")
            return cached

        prompt = f"""Write a BLUF (Bottom Line Up Front) paragraph for an article about "{topic}".

REQUIREMENTS:
1. Maximum {max_sentences} sentences
2. Include primary keyword naturally
3. State the main takeaway/value proposition
4. Be direct and actionable
5. Avoid these AI-tell words: {', '.join(AI_TELL_WORDS[:5])}

KEYWORDS TO INCLUDE: {keywords[:3]}

OUTPUT: Only the paragraph, no quotes or labels.
"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.6, max_tokens=200)
            
            # Clean response
            bluf = response.strip().strip('"').strip("'")
            
            # Check for AI tells
            bluf = self._remove_ai_tells(bluf)
            
            # Ensure not too long
            sentences = re.split(r'[.!?]+', bluf)
            if len(sentences) > max_sentences + 1:
                bluf = '. '.join(sentences[:max_sentences]) + '.'
            
            cache.set(cache_key, bluf)
            return bluf
            
        except Exception as e:
            logger.error(f"Failed to generate BLUF: {e}")
            return f"{topic} delivers measurable results when implemented correctly. This guide shows you exactly how to get started."
    
    def generate_content_block(self, h2: str, context: Dict[str, Any],
                               keywords: List[str], word_count: int = 200) -> ContentBlock:
        """
        Generate a content block for an H2 section.
        
        Args:
            h2: The H2 heading
            context: Research context
            keywords: Target keywords
            word_count: Target word count
            
        Returns:
            ContentBlock object
        """
        cache_key = f"content:block:{h2}:{','.join(sorted(keywords))}:{word_count}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"Content Block Cache HIT for h2: {h2}")
            return cached

        is_question = '?' in h2
        
        prompt = f"""Write content for the section: "{h2}"

REQUIREMENTS:
1. {'Answer the question directly in the first sentence' if is_question else 'Start with a strong opening statement'}
2. Approximately {word_count} words
3. Include E-E-A-T signals: demonstrate expertise, experience, authoritativeness, trustworthiness
4. Use 2-3 of these keywords naturally: {keywords[:5]}
5. Include specific examples, data, or actionable advice
6. Avoid AI-tell words: {', '.join(AI_TELL_WORDS)}
7. Write in an engaging, human tone

ADDITIONAL CONTEXT:
{json.dumps(context.get('content_gaps', [])[:3], indent=2)}

OUTPUT: Only the content, no quotes or labels.
"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.7, max_tokens=word_count * 2)
            
            content = response.strip().strip('"').strip("'")
            content = self._remove_ai_tells(content)
            
            # Find which keywords were used
            keywords_used = []
            content_lower = content.lower()
            for kw in keywords:
                if kw.lower() in content_lower:
                    keywords_used.append(kw)
            
            block = ContentBlock(
                type='paragraph',
                heading=h2,
                content=content,
                keywords_used=keywords_used
            )
            cache.set(cache_key, block)
            return block
            
        except Exception as e:
            logger.error(f"Failed to generate content block for {h2}: {e}")
            return ContentBlock(
                type='paragraph',
                heading=h2,
                content=f"Content for {h2} would go here.",
                keywords_used=[]
            )
    
    def generate_snippet_bait(self, topic: str, keywords: List[str]) -> str:
        """
        Generate featured snippet bait content.
        
        Args:
            topic: Main topic
            keywords: Target keywords
            
        Returns:
            Snippet-optimized content
        """
        cache_key = f"content:snippet_bait:{topic}:{','.join(sorted(keywords))}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"Snippet Bait Cache HIT for topic: {topic}")
            return cached

        prompt = f"""Create featured snippet bait for "{topic}".

REQUIREMENTS:
1. Direct, concise answer (40-60 words)
2. Structured as a definition or step-by-step
3. Include primary keyword in first 10 words
4. No fluff - just valuable information

OUTPUT: Only the snippet content.
"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.5, max_tokens=150)
            result = self._remove_ai_tells(response.strip())
            cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Failed to generate snippet bait: {e}")
            return f"{topic} refers to the strategic approach of..."
    
    def generate_meta_tags(self, content_summary: str, topic: str,
                          keywords: List[str]) -> MetaTags:
        """
        Generate SEO meta tags.
        
        Args:
            content_summary: Summary of the content
            topic: Main topic
            keywords: Target keywords
            
        Returns:
            MetaTags object
        """
        cache_key = f"content:meta_tags:{topic}:{','.join(sorted(keywords))}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"Meta Tags Cache HIT for topic: {topic}")
            return cached

        prompt = f"""Generate SEO meta tags for an article about "{topic}".

CONTENT SUMMARY: {content_summary[:500]}
PRIMARY KEYWORDS: {keywords[:3]}

Generate:
1. Title (50-60 characters, include primary keyword)
2. Description (150-160 characters, compelling, include keywords)

OUTPUT as JSON:
{{"title": "...", "description": "..."}}
"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.5, max_tokens=200)
            data = json.loads(response.strip())
            
            title = data.get('title', f"{topic}: Complete Guide for 2025")
            description = data.get('description', f"Learn about {topic} with our comprehensive guide.")
            
            # Validate lengths
            if len(title) > 60:
                title = title[:57] + "..."
            if len(description) > 160:
                description = description[:157] + "..."
            
            meta = MetaTags(
                title=title,
                description=description,
                keywords=keywords,
                og_title=title,
                og_description=description,
                twitter_card="summary_large_image"
            )
            cache.set(cache_key, meta)
            return meta
            
        except Exception as e:
            logger.error(f"Failed to generate meta tags: {e}")
            return MetaTags(
                title=f"{topic}: Complete Guide",
                description=f"Learn about {topic} with practical tips and strategies.",
                keywords=keywords
            )
    
    def generate_faq_section(self, topic: str, questions: List[str],
                            keywords: List[str]) -> List[Dict[str, str]]:
        """
        Generate FAQ section.
        
        Args:
            topic: Main topic
            questions: List of questions to answer
            keywords: Target keywords
            
        Returns:
            List of Q&A dictionaries
        """
        cache_key = f"content:faq:{topic}:{','.join(sorted(questions))}:{','.join(sorted(keywords))}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"FAQ Cache HIT for topic: {topic}")
            return cached

        faqs = []
        
        for question in questions[:5]:
            prompt = f"""Answer this question about {topic}: "{question}"

REQUIREMENTS:
1. 2-3 sentences maximum
2. Be direct and helpful
3. Include relevant keywords naturally

OUTPUT: Only the answer, no quotes.
"""
            
            try:
                answer = self.llm.generate(prompt, temperature=0.6, max_tokens=100)
                answer = self._remove_ai_tells(answer.strip())
                
                faqs.append({
                    'question': question,
                    'answer': answer
                })
            except Exception as e:
                logger.warning(f"Failed to generate FAQ answer: {e}")
                continue
        
        cache.set(cache_key, faqs)
        return faqs
    
    def _remove_ai_tells(self, text: str) -> str:
        """Remove AI-tell phrases from text"""
        for word in AI_TELL_WORDS:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            text = pattern.sub('', text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def detect_ai_tells(self, text: str) -> List[str]:
        """Detect AI-tell words in text"""
        found = []
        text_lower = text.lower()
        
        for word in AI_TELL_WORDS:
            if word.lower() in text_lower:
                found.append(word)
        
        return found


# Convenience function
def generate_article(topic: str, keywords: List[str], 
                    provider: str = "openai") -> Dict[str, Any]:
    """
    Generate a complete article structure.
    
    Args:
        topic: Article topic
        keywords: Target keywords
        provider: LLM provider
        
    Returns:
        Article structure dictionary
    """
    from .research_service import research_topic
    
    # Get research data
    research = research_topic(topic, keywords)
    
    # Initialize generator
    generator = ContentGenerator(provider=provider)
    
    # Generate components
    h2_outline = generator.generate_h2_outline(research, topic)
    bluf = generator.generate_bluf_paragraph(topic, keywords)
    
    content_blocks = []
    for h2 in h2_outline:
        block = generator.generate_content_block(h2, research, keywords)
        content_blocks.append(asdict(block))
    
    meta = generator.generate_meta_tags(bluf, topic, keywords)
    
    return {
        'topic': topic,
        'keywords': keywords,
        'h2_outline': h2_outline,
        'bluf': bluf,
        'content_blocks': content_blocks,
        'meta_tags': asdict(meta),
        'research_data': {
            'content_gaps': research.get('content_gaps', []),
            'paa_questions': [q.get('question') for q in research.get('paa_questions', [])]
        }
    }


if __name__ == "__main__":
    import sys
    
    topic = sys.argv[1] if len(sys.argv) > 1 else "AI Content Marketing"
    keywords = sys.argv[2].split(',') if len(sys.argv) > 2 else ["AI", "content", "marketing"]
    
    print(f"Generating article for: {topic}")
    article = generate_article(topic, keywords)
    
    print(f"\nH2 Outline ({len(article['h2_outline'])} sections):")
    for h2 in article['h2_outline']:
        print(f"  - {h2}")
    
    print(f"\nBLUF:\n{article['bluf']}")
    
    print(f"\nMeta Title: {article['meta_tags']['title']}")
    print(f"Meta Description: {article['meta_tags']['description']}")


