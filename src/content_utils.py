import re
import math
import html
import unicodedata
from collections import Counter
from typing import Any, List, Dict, Optional

# Basic stop words for English to aid in keyword extraction
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", 
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", 
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", 
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", 
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", 
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", 
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", 
    "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", 
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", 
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", 
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", 
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", 
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", 
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}

def word_count(text: str) -> int:
    """Accurately count words in a text block."""
    if not text:
        return 0
    # Use regex to find alphabetic/numeric sequences as words
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def reading_time(text: str, wpm: int = 200) -> int:
    """Calculate reading time in minutes."""
    words = word_count(text)
    if words == 0:
        return 0
    return math.ceil(words / wpm)

def _count_syllables(word: str) -> int:
    """Helper function to count syllables in a word for readability scoring."""
    word = word.lower()
    if len(word) <= 3:
        return 1
    # Remove endings that shouldn't be counted as syllables
    word = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', word)
    word = re.sub(r'^y', '', word)
    # Count vowel groups
    matches = re.findall(r'[aeiouy]{1,2}', word)
    return max(1, len(matches))

def flesch_reading_ease(text: str) -> float:
    """Calculate the Flesch Reading Ease score."""
    if not text:
        return 0.0
    
    # Split into sentences roughly by punctuation
    sentences = max(1, len(re.split(r'[.!?]+', text)) - 1)
    words = re.findall(r'\b\w+\b', text)
    word_ct = max(1, len(words))
    
    syllable_ct = sum(_count_syllables(w) for w in words)
    
    # Flesch Reading Ease formula
    score = 206.835 - 1.015 * (word_ct / sentences) - 84.6 * (syllable_ct / word_ct)
    return round(score, 2)

def extract_keywords(text: str, n: int = 10) -> List[str]:
    """
    Extract top N keywords using a basic term frequency approach.
    Acts as a proxy for TF-IDF on a single document.
    """
    if not text:
        return []
    
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    filtered_words = [w for w in words if w not in STOP_WORDS and not w.isdigit()]
    
    word_counts = Counter(filtered_words)
    return [word for word, count in word_counts.most_common(n)]

def slugify(text: str) -> str:
    """Convert a string into a URL-safe slug."""
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    # Remove non-alphanumeric characters except spaces and hyphens
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace spaces and multiple hyphens with a single hyphen
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def truncate(text: str, max_chars: int, suffix: str = "...") -> str:
    """Smart truncation that doesn't cut words in half."""
    if len(text) <= max_chars:
        return text
    
    # Cut down to the max size minus the suffix length
    truncated = text[:max_chars - len(suffix)]
    # Split by the last space and drop the cut word
    truncated = truncated.rsplit(' ', 1)[0]
    return truncated + suffix

def html_to_text(html_content: str) -> str:
    """Strip HTML tags and return plain text."""
    if not html_content:
        return ""
    
    # Remove scripts and styles
    text = re.sub(r'<style.*?>.*?</style>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script.*?>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Unescape HTML entities (e.g., &amp; -> &)
    text = html.unescape(text)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_headings(html_content: str) -> Dict[str, List[str]]:
    """Extract H2 and H3 headings from HTML content."""
    if not html_content:
        return {"h2": [], "h3": []}
    
    h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', html_content, re.IGNORECASE | re.DOTALL)
    h3_matches = re.findall(r'<h3[^>]*>(.*?)</h3>', html_content, re.IGNORECASE | re.DOTALL)
    
    return {
        "h2": [html_to_text(h) for h in h2_matches],
        "h3": [html_to_text(h) for h in h3_matches]
    }

def count_questions(text: str) -> int:
    """Count the number of question marks in a text."""
    if not text:
        return 0
    return len(re.findall(r'\?', text))

def detect_language(text: str) -> str:
    """
    Detect the primary language of the text.
    Uses 'langdetect' if installed, otherwise falls back to a naive heuristic.
    """
    if not text:
        return 'en'
    
    try:
        from langdetect import detect
        return detect(text)
    except ImportError:
        # Fallback naive heuristic based on character sets and common short words
        text_lower = text.lower()
        if re.search(r'[а-яА-Я]', text_lower):
            return 'ru'
        
        # Check for specific characters common in languages
        if re.search(r'[éàèùâêîôûç]', text_lower) and " et " in text_lower:
            return 'fr'
        if re.search(r'[áéíóúñ]', text_lower) and " y " in text_lower:
            return 'es'
        if re.search(r'[äöüß]', text_lower) and " und " in text_lower:
            return 'de'
            
        return 'en'  # Default to English


def extract_faq_from_headings(html_content: str) -> List[Dict[str, str]]:
    """Extract FAQ pairs from question-format H2/H3 headings and their following paragraphs.
    
    Finds headings that end with '?' and pairs them with the first paragraph
    that follows. Returns a list suitable for FAQPage schema generation.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        List of {"question": str, "answer": str} dicts
    """
    if not html_content:
        return []
    
    # Match question headings (h2 or h3) followed by content
    pattern = r'<h[23][^>]*>(.*?\?)</h[23]>\s*<p[^>]*>(.*?)</p>'
    matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    faqs = []
    for question, answer in matches:
        q = html_to_text(question).strip()
        a = html_to_text(answer).strip()
        if q and a:
            faqs.append({"question": q, "answer": a})
    
    return faqs


def suggest_canonical_url(title: str, base_url: str = "") -> str:
    """Generate a SEO-friendly canonical URL slug from a title.
    
    Args:
        title: Article or page title
        base_url: Optional base URL to prepend
        
    Returns:
        Canonical URL path or full URL
    """
    if not title:
        return base_url or "/"
    
    # Normalize unicode
    slug = unicodedata.normalize("NFKD", title.lower())
    # Remove non-alphanumeric (except hyphens and spaces)
    slug = re.sub(r'[^\w\s-]', '', slug)
    # Replace whitespace with hyphens
    slug = re.sub(r'[\s_]+', '-', slug.strip())
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug).strip('-')
    # Truncate to reasonable URL length
    if len(slug) > 80:
        slug = slug[:80].rsplit('-', 1)[0]
    
    if base_url:
        return f"{base_url.rstrip('/')}/{slug}"
    return f"/{slug}"


def generate_meta_description(html_content: str, max_length: int = 160) -> str:
    """Auto-generate a meta description from HTML content.
    
    Extracts the first readable paragraph, removes HTML tags, and truncates
    to the recommended SEO length (usually 155-160 characters) without
    cutting off words in the middle.
    
    Args:
        html_content: Raw HTML content
        max_length: Maximum allowed length for the description
        
    Returns:
        A clean meta description string
    """
    if not html_content:
        return ""
        
    # Extract paragraphs
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html_content, re.DOTALL | re.IGNORECASE)
    
    text = ""
    for p in paragraphs:
        # Strip HTML and normalize whitespace
        clean_p = html_to_text(p).strip()
        if clean_p and len(clean_p) > 20:  # Skip very short paragraphs or empty ones
            text = clean_p
            break
            
    if not text:
        # Fallback if no <p> tags with sufficient content exist
        text = html_to_text(html_content).strip()
        
    if len(text) <= max_length:
        return text
        
    # Truncate to max_length
    truncated = text[:max_length].strip()
    
    # Try to cut at the last space to avoid breaking words
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
        
    # Add ellipsis if we actually truncated the word
    if not text.startswith(truncated) or len(text) > len(truncated):
        # Only add ellipsis if it doesn't already end with punctuation
        if truncated and truncated[-1] not in ['.', '!', '?']:
            truncated += "..."
            
    return truncated



def estimate_content_quality_score(text: str) -> Dict[str, Any]:
    """Estimate a content quality score based on multiple signals.
    
    Returns a dict with individual scores and an overall score (0-100).
    """
    if not text:
        return {"overall": 0, "details": {}}
    
    words = word_count(text)
    questions = count_questions(text)
    
    # Length score (target: 2000-4000 words)
    if words >= 2000:
        length_score = min(100, 50 + (words - 2000) / 40)
    elif words >= 1000:
        length_score = 30 + (words - 1000) / 50
    else:
        length_score = words / 33.3
    
    # Structure score (presence of headers)
    h2_count = len(re.findall(r'<h2', text, re.IGNORECASE))
    h3_count = len(re.findall(r'<h3', text, re.IGNORECASE))
    structure_score = min(100, (h2_count * 15) + (h3_count * 5))
    
    # Question ratio (higher = more engaging)
    question_score = min(100, questions * 15)
    
    # Link density
    internal_links = len(re.findall(r'<a\s+[^>]*href="/', text, re.IGNORECASE))
    external_links = len(re.findall(r'<a\s+[^>]*href="https?://', text, re.IGNORECASE))
    link_score = min(100, (internal_links * 10) + (external_links * 15))
    
    overall = round(
        length_score * 0.3 +
        structure_score * 0.25 +
        question_score * 0.2 +
        link_score * 0.25
    )
    
    return {
        "overall": min(100, overall),
        "details": {
            "length_score": round(length_score),
            "structure_score": round(structure_score),
            "question_score": round(question_score),
            "link_score": round(link_score),
            "word_count": words,
            "h2_count": h2_count,
            "h3_count": h3_count,
            "question_count": questions,
            "internal_links": internal_links,
            "external_links": external_links,
        }
    }

def calculate_keyword_density(text: str, top_n: int = 10, stop_words: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Calculate keyword density/frequency (TF) for a given text.
    
    Args:
        text: Plain text content
        top_n: Number of top keywords to return
        stop_words: Optional list of stop words to ignore
        
    Returns:
        List of dicts containing keyword, count, and density percentage
    """
    if not text:
        return []
        
    if stop_words is None:
        stop_words = list(STOP_WORDS)
        
    # Lowercase and extract alphanumeric words
    words = re.findall(r'\b[a-z0-9]+\b', text.lower())
    
    # Filter stop words and short words
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    total_filtered = len(filtered_words)
    
    if total_filtered == 0:
        return []
        
    counts = Counter(filtered_words)
    top_keywords = counts.most_common(top_n)
    
    results = []
    for word, count in top_keywords:
        results.append({
            "keyword": word,
            "count": count,
            "density": round((count / total_filtered) * 100, 2)
        })
        
    return results

def estimate_information_gain_score(text: str, reference_texts: List[str]) -> Dict[str, Any]:
    """
    Estimate the Information Gain (IG) score of a text compared to a set of reference texts.
    Information Gain measures the uniqueness and value delta of the content.
    """
    if not text:
        return {"overall": 0, "details": {}}
    
    if not reference_texts:
        reference_texts = []
        
    def get_ngrams(t: str, n: int) -> set:
        txt = html_to_text(t).lower()
        words = re.findall(r'\b[a-z]{3,}\b', txt)
        filtered = [w for w in words if w not in STOP_WORDS]
        if len(filtered) < n:
            return set()
        return set(tuple(filtered[i:i+n]) for i in range(len(filtered) - n + 1))

    def get_stats(t: str) -> set:
        txt = html_to_text(t)
        patterns = [
            r'\b\d+(?:\.\d+)?%',
            r'\$\d+(?:\.\d+)?[kM]?',
            r'\b\d+x\b',
            r'\b\d{4,}\b'
        ]
        stats = []
        for p in patterns:
            stats.extend(re.findall(p, txt, re.IGNORECASE))
        return set(stats)

    def get_entities(t: str) -> set:
        txt = html_to_text(t)
        words = re.findall(r'\b[A-Z][a-zA-Z0-9-]+\b', txt)
        return set(words)

    target_unigrams = get_ngrams(text, 1)
    target_bigrams = get_ngrams(text, 2)
    target_trigrams = get_ngrams(text, 3)
    target_stats = get_stats(text)
    target_entities = get_entities(text)
    
    ref_unigrams = set()
    ref_bigrams = set()
    ref_trigrams = set()
    ref_stats = set()
    ref_entities = set()
    
    for ref in reference_texts:
        ref_unigrams.update(get_ngrams(ref, 1))
        ref_bigrams.update(get_ngrams(ref, 2))
        ref_trigrams.update(get_ngrams(ref, 3))
        ref_stats.update(get_stats(ref))
        ref_entities.update(get_entities(ref))
        
    unique_unigrams = target_unigrams - ref_unigrams
    unique_bigrams = target_bigrams - ref_bigrams
    unique_trigrams = target_trigrams - ref_trigrams
    unique_stats = target_stats - ref_stats
    unique_entities = target_entities - ref_entities
    
    unigram_ratio = len(unique_unigrams) / len(target_unigrams) if target_unigrams else 0.0
    bigram_ratio = len(unique_bigrams) / len(target_bigrams) if target_bigrams else 0.0
    trigram_ratio = len(unique_trigrams) / len(target_trigrams) if target_trigrams else 0.0
    
    ngram_uniqueness = (unigram_ratio * 0.2 + bigram_ratio * 0.4 + trigram_ratio * 0.4) * 100
    
    if target_stats:
        stats_uniqueness = (len(unique_stats) / len(target_stats)) * 100
    else:
        stats_uniqueness = 0.0
        
    if target_entities:
        entity_uniqueness = (len(unique_entities) / len(target_entities)) * 100
    else:
        entity_uniqueness = 0.0
        
    if not reference_texts:
        words = max(1, word_count(text))
        stat_density = min(100, (len(target_stats) / words) * 1000)
        entity_density = min(100, (len(target_entities) / words) * 100)
        ngram_richness = min(100, (len(target_trigrams) / words) * 200)
        
        overall = round(stat_density * 0.3 + entity_density * 0.3 + ngram_richness * 0.4)
        return {
            "overall": overall,
            "details": {
                "stat_density": round(stat_density, 2),
                "entity_density": round(entity_density, 2),
                "ngram_richness": round(ngram_richness, 2),
                "is_baseline_comparison": False
            }
        }

    weights = {"ngram": 0.5, "stats": 0.3, "entities": 0.2}
    
    if not target_stats:
        weights["ngram"] += 0.2
        weights["entities"] += 0.1
        stats_uniqueness = 0.0
        
    if not target_entities:
        weights["ngram"] += weights.get("entities", 0.0)
        weights["entities"] = 0.0
        
    overall = round(
        ngram_uniqueness * weights["ngram"] +
        stats_uniqueness * (weights.get("stats", 0) if target_stats else 0) +
        entity_uniqueness * weights["entities"]
    )
    
    return {
        "overall": min(100, max(0, overall)),
        "details": {
            "ngram_uniqueness": round(ngram_uniqueness, 2),
            "stats_uniqueness": round(stats_uniqueness, 2),
            "entity_uniqueness": round(entity_uniqueness, 2),
            "unique_unigrams_count": len(unique_unigrams),
            "unique_bigrams_count": len(unique_bigrams),
            "unique_trigrams_count": len(unique_trigrams),
            "unique_stats_count": len(unique_stats),
            "unique_entities_count": len(unique_entities),
            "is_baseline_comparison": True
        }
    }
