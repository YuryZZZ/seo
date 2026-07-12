import re
import math
import html
import unicodedata
from collections import Counter
from typing import Any, List, Dict

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

