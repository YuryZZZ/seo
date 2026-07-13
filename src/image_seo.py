import os
import re
import json
import io
import logging
from typing import Dict, List, Optional, Union, Tuple, Any
from urllib.parse import urlparse

try:
    import requests
    from PIL import Image, ExifTags
except ImportError:
    logging.warning("Please install requests and Pillow: pip install requests Pillow")

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

logger = logging.getLogger(__name__)

class ImageSEOAnalyzer:
    """
    Comprehensive Image SEO Module for the SEO/GEO Framework.
    Handles image analysis, optimization, WebP conversion, EXIF injection,
    Schema markup, and Image Sitemaps.
    """
    
    def __init__(self, llm_client=None, serp_client=None):
        self.llm_client = llm_client
        self.serp_client = serp_client
        self.discover_min_width = 1200

    def analyze_image_seo(self, image_url: str) -> Dict:
        """
        Full image analysis checking size, dimensions, format, and filename.
        """
        report = {
            "url": image_url,
            "status": "success",
            "warnings": [],
            "passes": [],
            "metrics": {}
        }
        
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            content_length = len(response.content)
            report["metrics"]["size_kb"] = round(content_length / 1024, 2)
            
            if report["metrics"]["size_kb"] > 100:
                report["warnings"].append(f"Image size is large ({report['metrics']['size_kb']} KB). Consider compressing below 100KB.")
            else:
                report["passes"].append("Image file size is optimized (<100KB).")

            # Check filename
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path)
            report["metrics"]["filename"] = filename
            
            if not re.match(r'^[a-z0-9-]+[a-z0-9]\.[a-z]+$', filename.lower()):
                report["warnings"].append("Filename is not SEO-friendly (use lowercase alphanumeric and hyphens).")
            else:
                report["passes"].append("Filename is SEO-friendly.")

            # Image dimensions & format
            img = Image.open(io.BytesIO(response.content))
            width, height = img.size
            report["metrics"]["width"] = width
            report["metrics"]["height"] = height
            report["metrics"]["format"] = img.format

            if img.format not in ['WEBP', 'AVIF']:
                report["warnings"].append(f"Format is {img.format}. Consider next-gen formats like WebP or AVIF.")
            else:
                report["passes"].append("Using next-gen image format.")

            if width < self.discover_min_width:
                report["warnings"].append(f"Width ({width}px) is less than {self.discover_min_width}px required for Google Discover.")
            else:
                report["passes"].append("Width meets Google Discover requirements (>=1200px).")
                
        except Exception as e:
            report["status"] = "error"
            report["error_message"] = str(e)
            
        return report

    def generate_alt_text(self, image_url: str, context: str, keyword: str = "") -> str:
        """
        Generate SEO-friendly alt text based on context and keywords.
        Requires an LLM client for actual vision/context generation.
        """
        if self.llm_client:
            # Placeholder for actual LLM Vision prompt
            prompt = f"Write a descriptive, accessible, SEO-friendly alt text for this image under 125 characters. Context: {context}. Target keyword: {keyword}."
            return f"Generated Alt Text for {keyword} (Mocked LLM Response)"
        
        # Fallback heuristic
        clean_context = re.sub(r'[^a-zA-Z0-9\s]', '', context).strip()
        words = clean_context.split()[:10]
        base_alt = " ".join(words)
        if keyword and keyword.lower() not in base_alt.lower():
            return f"{base_alt} illustrating {keyword}".strip()
        return base_alt

    def generate_seo_filename(self, description: str, extension: str = "webp") -> str:
        """
        Converts a description into an SEO-friendly filename.
        Example: "A red fox jumping" -> "red-fox-jumping.webp"
        """
        # Remove stop words and special characters
        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'in', 'on', 'at', 'to', 'for', 'with'}
        words = [w.lower() for w in re.split(r'\W+', description) if w and w.lower() not in stop_words]
        
        clean_name = "-".join(words)
        return f"{clean_name}.{extension.strip('.')}"

    def optimize_image_size(self, image_data: bytes, target_width: int = 1200) -> bytes:
        """
        Resizes an image maintaining aspect ratio.
        Takes bytes, returns bytes.
        """
        img = Image.open(io.BytesIO(image_data))
        
        # Calculate new height
        w_percent = (target_width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        
        # Resize using LANCZOS for high quality
        resized_img = img.resize((target_width, h_size), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        resized_img.save(output, format=img.format or 'JPEG', quality=85, optimize=True)
        return output.getvalue()

    def convert_to_webp(self, image_data: bytes, quality: int = 80) -> bytes:
        """
        Converts any standard image format to WebP.
        Takes bytes, returns bytes.
        """
        img = Image.open(io.BytesIO(image_data))
        if img.mode in ('RGBA', 'LA'):
            # WebP supports alpha, but let's ensure compatibility
            background = Image.new('RGBA', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
            
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=quality, method=6)
        return output.getvalue()

    def add_exif_data(self, image_data: bytes, metadata: Dict[str, str]) -> bytes:
        """
        Injects EXIF metadata (Copyright, Description, Author) for Image SEO authority.
        Note: Works best with JPEGs. WebP EXIF is more complex.
        """
        try:
            import piexif
            img = Image.open(io.BytesIO(image_data))
            
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            # Map common string metadata to EXIF tags
            if "author" in metadata:
                exif_dict["0th"][piexif.ImageIFD.Artist] = metadata["author"].encode('utf-8')
            if "copyright" in metadata:
                exif_dict["0th"][piexif.ImageIFD.Copyright] = metadata["copyright"].encode('utf-8')
            if "description" in metadata:
                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = metadata["description"].encode('utf-8')
                
            exif_bytes = piexif.dump(exif_dict)
            output = io.BytesIO()
            img.save(output, format=img.format or 'JPEG', exif=exif_bytes)
            return output.getvalue()
        except ImportError:
            logging.warning("piexif library not installed. EXIF injection skipped.")
            return image_data
        except Exception as e:
            logging.error(f"Error injecting EXIF: {e}")
            return image_data

    def create_image_schema(self, images: List[Dict]) -> Dict:
        """
        Generates JSON-LD ImageObject schema for a list of images.
        Expected input format: [{"url": "...", "caption": "...", "author": "..."}]
        """
        schemas = []
        for img in images:
            schema = {
                "@context": "https://schema.org",
                "@type": "ImageObject",
                "contentUrl": img.get("url"),
                "caption": img.get("caption", ""),
                "description": img.get("description", img.get("caption", "")),
                "inLanguage": "en-US"
            }
            if "author" in img:
                schema["creator"] = {
                    "@type": "Person",
                    "name": img["author"]
                }
            if "license" in img:
                schema["license"] = img["license"]
                
            schemas.append(schema)
            
        if len(schemas) == 1:
            return schemas[0]
        return schemas

    def analyze_image_serp(self, keyword: str) -> Dict:
        """
        Analyzes Image SERP features for a given keyword to find gaps.
        Requires SERP API client.
        """
        if self.serp_client:
            # Mock implementation calling external API
            return {"status": "success", "dominant_colors": ["blue", "white"], "common_entities": ["graph", "chart"]}
        
        return {"status": "skipped", "message": "SERP Client not configured."}

    def generate_image_sitemap(self, images: List[Dict], page_url: str) -> str:
        """
        Generates a Google Image Sitemap XML string.
        Input images format: [{"loc": "...", "title": "...", "caption": "...", "license": "..."}]
        """
        urlset = Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        urlset.set("xmlns:image", "http://www.google.com/schemas/sitemap-image/1.1")
        
        url_tag = SubElement(urlset, "url")
        loc_tag = SubElement(url_tag, "loc")
        loc_tag.text = page_url
        
        for img in images:
            img_tag = SubElement(url_tag, "image:image")
            
            img_loc = SubElement(img_tag, "image:loc")
            img_loc.text = img.get("loc")
            
            if "title" in img:
                img_title = SubElement(img_tag, "image:title")
                img_title.text = img.get("title")
                
            if "caption" in img:
                img_caption = SubElement(img_tag, "image:caption")
                img_caption.text = img.get("caption")
                
            if "license" in img:
                img_license = SubElement(img_tag, "image:license")
                img_license.text = img.get("license")

        xml_str = tostring(urlset, 'utf-8')
        reparsed = minidom.parseString(xml_str)
        return reparsed.toprettyxml(indent="  ")

    def validate_discover_images(self, images: List[str]) -> Dict:
        """
        Validates if images meet Google Discover requirements (width >= 1200px).
        Returns a map of URL to validation status.
        """
        results = {"passed": [], "failed": [], "errors": []}
        
        for url in images:
            try:
                response = requests.get(url, stream=True, timeout=10)
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content))
                
                if img.size[0] >= self.discover_min_width:
                    results["passed"].append({"url": url, "width": img.size[0]})
                else:
                    results["failed"].append({"url": url, "width": img.size[0]})
            except Exception as e:
                results["errors"].append({"url": url, "error": str(e)})
                
        return results

    def get_image_seo_report(self, image_urls: List[str]) -> Dict:
        """
        Generates a comprehensive Image SEO report for multiple URLs.
        """
        report = {
            "total_images": len(image_urls),
            "discover_eligible": 0,
            "next_gen_formats": 0,
            "size_optimized": 0,
            "details": []
        }
        
        for url in image_urls:
            analysis = self.analyze_image_seo(url)
            report["details"].append(analysis)
            
            if analysis["status"] == "success":
                metrics = analysis.get("metrics", {})
                if metrics.get("width", 0) >= self.discover_min_width:
                    report["discover_eligible"] += 1
                if metrics.get("format") in ['WEBP', 'AVIF']:
                    report["next_gen_formats"] += 1
                if metrics.get("size_kb", 0) < 100:
                    report["size_optimized"] += 1
                    
        return report

    def vision_api_alt_text(self, image_data: bytes, context: str, keyword: str = "") -> str:
        """
        Attempts to call the Google Cloud Vision API to analyze an image's content 
        and generate a descriptive, accessible, SEO-friendly Alt text.
        Falls back gracefully if not authenticated, API is disabled, or library is missing.
        """
        try:
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=image_data)
            
            response = client.label_detection(image=image)
            labels = response.label_annotations
            
            if labels:
                label_descriptions = [label.description for label in labels[:4]]
                inferred = ", ".join(label_descriptions)
                alt = f"Image depicting {inferred}"
                if keyword:
                    alt += f" in relation to {keyword}"
                if len(alt) > 125:
                    alt = alt[:122] + "..."
                return alt
        except Exception as e:
            logger.info(f"Vision API call failed or not configured: {str(e)}. Using fallback heuristic.")
            
        try:
            img = Image.open(io.BytesIO(image_data))
            w, h = img.size
            fmt = img.format
            orientation = "vertical" if h > w else "horizontal"
            alt = f"A {orientation} {fmt.lower()} graphic showing {context}"
            if keyword and keyword.lower() not in alt.lower():
                alt += f" for {keyword}"
            if len(alt) > 125:
                alt = alt[:122] + "..."
            return alt
        except Exception:
            return f"Image for {keyword}" if keyword else "Relevant context image"

    def get_compression_recommendations(self, image_data: bytes) -> Dict[str, Any]:
        """
        Calculates file size savings from WebP conversion and produces compression recommendations.
        """
        try:
            original_size = len(image_data)
            original_size_kb = round(original_size / 1024, 2)
            
            webp_data = self.convert_to_webp(image_data)
            webp_size = len(webp_data)
            webp_size_kb = round(webp_size / 1024, 2)
            
            savings_kb = round(original_size_kb - webp_size_kb, 2)
            savings_percent = round((savings_kb / original_size_kb) * 100, 2) if original_size_kb > 0 else 0.0
            
            recommendations = []
            if original_size_kb > 100:
                recommendations.append("Image is over 100KB. WebP compression is strongly recommended.")
            if savings_percent > 15:
                recommendations.append(f"Convert to WebP to save {savings_percent}% in bandwidth.")
                
            return {
                "original_size_kb": original_size_kb,
                "webp_size_kb": webp_size_kb,
                "savings_kb": max(0.0, savings_kb),
                "savings_percent": max(0.0, savings_percent),
                "recommendations": recommendations if recommendations else ["Image is already well-optimized."]
            }
        except Exception as e:
            return {
                "error": f"Failed to compute compression metrics: {str(e)}",
                "original_size_kb": round(len(image_data) / 1024, 2),
                "webp_size_kb": 0.0,
                "savings_kb": 0.0,
                "savings_percent": 0.0,
                "recommendations": ["Ensure Pillow is installed properly."]
            }

    def generate_image_metadata(self, page_context: Dict[str, Any], image_url: str) -> Dict[str, str]:
        """
        Deduces optimal metadata (filename, alt, title, caption) for an image 
        based on the page headings, target keyword, and image context.
        """
        keyword = page_context.get("keyword", "")
        heading = page_context.get("primary_heading", "") or page_context.get("h1", "")
        
        parsed_url = urlparse(image_url)
        raw_filename = os.path.basename(parsed_url.path)
        base_name, ext = os.path.splitext(raw_filename)
        
        description = heading or keyword or base_name
        seo_filename = self.generate_seo_filename(description, extension="webp")
        
        alt_text = self.generate_alt_text(image_url, context=heading, keyword=keyword)
        
        title = f"{keyword.title()} - {heading}" if keyword and heading else heading or keyword.title() or "SEO Visual Asset"
        caption = f"Figure: Detailed representation of {description.lower()}."
        
        return {
            "seo_filename": seo_filename,
            "alt_text": alt_text,
            "title": title,
            "caption": caption
        }

# Example Usage
if __name__ == "__main__":
    analyzer = ImageSEOAnalyzer()
    print("ImageSEOAnalyzer initialized successfully.")
