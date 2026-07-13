import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

class SchemaGenerator:
    """
    A comprehensive utility class for generating Schema.org JSON-LD structured data.
    Provides methods for generating various schema types, merging them into graphs,
    validating schemas, and recommending schemas based on content.
    """

    @staticmethod
    def _base_schema(schema_type: str) -> Dict[str, Any]:
        """Creates the base schema dictionary with context and type."""
        return {
            "@context": "https://schema.org",
            "@type": schema_type
        }

    @staticmethod
    def generate_article_schema(data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        """Generates Article or BlogPosting schema."""
        data = {**(data or {}), **kwargs}
        if "title" in data and "headline" not in data:
            data["headline"] = data["title"]
        if "author" in data and isinstance(data["author"], str):
            data["author"] = {"name": data["author"]}
        if "date_published" in data and "datePublished" not in data:
            data["datePublished"] = data["date_published"]
        schema_type = data.get('type', 'Article')
        schema = SchemaGenerator._base_schema(schema_type)
        
        schema["headline"] = data.get("headline", "")
        if "description" in data:
            schema["description"] = data["description"]
        if "image" in data:
            schema["image"] = data["image"]  # Can be string or list of strings
        if "datePublished" in data:
            schema["datePublished"] = data["datePublished"]
        if "dateModified" in data:
            schema["dateModified"] = data["dateModified"]
            
        if "author" in data:
            schema["author"] = {
                "@type": data.get("author_type", "Person"),
                "name": data["author"].get("name", "") if isinstance(data["author"], dict) else data["author"]
            }
            if isinstance(data["author"], dict) and "url" in data["author"]:
                schema["author"]["url"] = data["author"]["url"]

        if "publisher" in data:
            schema["publisher"] = {
                "@type": "Organization",
                "name": data["publisher"].get("name", "") if isinstance(data["publisher"], dict) else data["publisher"]
            }
            if isinstance(data["publisher"], dict) and "logo" in data["publisher"]:
                schema["publisher"]["logo"] = {
                    "@type": "ImageObject",
                    "url": data["publisher"]["logo"]
                }
                
        if "mainEntityOfPage" in data:
            schema["mainEntityOfPage"] = {
                "@type": "WebPage",
                "@id": data["mainEntityOfPage"]
            }

        if "speakable" in data:
            schema["speakable"] = data["speakable"]

        return schema

    @staticmethod
    def generate_about_page_schema(entities: List[Dict[str, Any]], page_url: str, page_name: str) -> Dict[str, Any]:
        """Generates AboutPage schema containing sameAs links for entities."""
        schema = SchemaGenerator._base_schema("AboutPage")
        schema["url"] = page_url
        schema["name"] = page_name
        
        about_list = []
        for ent in entities:
            about_list.append({
                "@type": ent.get("type", "Thing"),
                "name": ent.get("name", ""),
                "sameAs": ent.get("same_as", [])
            })
        schema["about"] = about_list
        return schema

    @staticmethod
    def generate_mentions_schema(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generates Mentions schema list (sameAs references) for entities."""
        mentions = []
        for ent in entities:
            mentions.append({
                "@type": ent.get("type", "Thing"),
                "name": ent.get("name", ""),
                "sameAs": ent.get("same_as", [])
            })
        return mentions

    @staticmethod
    def generate_faq_schema(questions: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generates FAQPage schema from a list of question/answer dicts."""
        schema = SchemaGenerator._base_schema("FAQPage")
        main_entity = []
        
        for qa in questions:
            if "question" in qa and "answer" in qa:
                main_entity.append({
                    "@type": "Question",
                    "name": qa["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": qa["answer"]
                    }
                })
                
        schema["mainEntity"] = main_entity
        return schema

    @staticmethod
    def generate_howto_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates HowTo schema."""
        schema = SchemaGenerator._base_schema("HowTo")
        schema["name"] = data.get("name", "")
        
        if "description" in data:
            schema["description"] = data["description"]
        if "totalTime" in data:
            schema["totalTime"] = data["totalTime"] # ISO 8601 format like PT30M
        if "image" in data:
            schema["image"] = data["image"]
            
        if "supply" in data:
            schema["supply"] = [{"@type": "HowToSupply", "name": item} for item in data["supply"]]
        if "tool" in data:
            schema["tool"] = [{"@type": "HowToTool", "name": item} for item in data["tool"]]
            
        steps = []
        for i, step in enumerate(data.get("steps", [])):
            step_data = {
                "@type": "HowToStep",
                "text": step.get("text", "")
            }
            if "name" in step:
                step_data["name"] = step["name"]
            if "url" in step:
                step_data["url"] = step["url"]
            if "image" in step:
                step_data["image"] = step["image"]
            steps.append(step_data)
            
        schema["step"] = steps
        return schema

    @staticmethod
    def generate_review_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates Review or AggregateRating schema."""
        if data.get("is_aggregate", False):
            schema = SchemaGenerator._base_schema("AggregateRating")
            schema["ratingValue"] = data.get("ratingValue", "")
            schema["reviewCount"] = data.get("reviewCount", "")
            if "bestRating" in data:
                schema["bestRating"] = data["bestRating"]
            if "worstRating" in data:
                schema["worstRating"] = data["worstRating"]
            return schema
            
        schema = SchemaGenerator._base_schema("Review")
        if "itemReviewed" in data:
            schema["itemReviewed"] = {
                "@type": data["itemReviewed"].get("type", "Thing"),
                "name": data["itemReviewed"].get("name", "")
            }
        
        schema["reviewRating"] = {
            "@type": "Rating",
            "ratingValue": data.get("ratingValue", ""),
        }
        if "bestRating" in data:
            schema["reviewRating"]["bestRating"] = data["bestRating"]
            
        schema["author"] = {
            "@type": data.get("author_type", "Person"),
            "name": data.get("author", "")
        }
        
        if "reviewBody" in data:
            schema["reviewBody"] = data["reviewBody"]
        if "datePublished" in data:
            schema["datePublished"] = data["datePublished"]
            
        return schema

    @staticmethod
    def generate_product_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates Product schema."""
        schema = SchemaGenerator._base_schema("Product")
        schema["name"] = data.get("name", "")
        
        if "image" in data:
            schema["image"] = data["image"]
        if "description" in data:
            schema["description"] = data["description"]
        if "sku" in data:
            schema["sku"] = data["sku"]
        if "mpn" in data:
            schema["mpn"] = data["mpn"]
            
        if "brand" in data:
            schema["brand"] = {
                "@type": "Brand",
                "name": data["brand"].get("name", "") if isinstance(data["brand"], dict) else data["brand"]
            }
            
        if "offers" in data:
            schema["offers"] = {
                "@type": "Offer",
                "url": data["offers"].get("url", ""),
                "priceCurrency": data["offers"].get("priceCurrency", "USD"),
                "price": data["offers"].get("price", ""),
                "itemCondition": f"https://schema.org/{data['offers'].get('itemCondition', 'NewCondition')}",
                "availability": f"https://schema.org/{data['offers'].get('availability', 'InStock')}"
            }
            if "priceValidUntil" in data["offers"]:
                schema["offers"]["priceValidUntil"] = data["offers"]["priceValidUntil"]
                
        if "aggregateRating" in data:
            schema["aggregateRating"] = SchemaGenerator.generate_review_schema(
                {**data["aggregateRating"], "is_aggregate": True}
            )
            del schema["aggregateRating"]["@context"]
            
        return schema

    @staticmethod
    def generate_local_business_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates LocalBusiness schema."""
        schema = SchemaGenerator._base_schema(data.get("type", "LocalBusiness"))
        schema["name"] = data.get("name", "")
        
        if "image" in data:
            schema["image"] = data["image"]
        if "@id" in data:
            schema["@id"] = data["@id"]
        if "url" in data:
            schema["url"] = data["url"]
        if "telephone" in data:
            schema["telephone"] = data["telephone"]
        if "priceRange" in data:
            schema["priceRange"] = data["priceRange"]
            
        if "address" in data:
            schema["address"] = {
                "@type": "PostalAddress",
                "streetAddress": data["address"].get("streetAddress", ""),
                "addressLocality": data["address"].get("addressLocality", ""),
                "addressRegion": data["address"].get("addressRegion", ""),
                "postalCode": data["address"].get("postalCode", ""),
                "addressCountry": data["address"].get("addressCountry", "")
            }
            
        if "geo" in data:
            schema["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": data["geo"].get("latitude", ""),
                "longitude": data["geo"].get("longitude", "")
            }
            
        if "openingHoursSpecification" in data:
            schema["openingHoursSpecification"] = []
            for hours in data["openingHoursSpecification"]:
                schema["openingHoursSpecification"].append({
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": hours.get("dayOfWeek", []),
                    "opens": hours.get("opens", ""),
                    "closes": hours.get("closes", "")
                })
                
        return schema

    @staticmethod
    def generate_person_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates Person schema."""
        schema = SchemaGenerator._base_schema("Person")
        schema["name"] = data.get("name", "")
        
        if "url" in data:
            schema["url"] = data["url"]
        if "image" in data:
            schema["image"] = data["image"]
        if "jobTitle" in data:
            schema["jobTitle"] = data["jobTitle"]
        if "sameAs" in data:
            schema["sameAs"] = data["sameAs"]
            
        if "worksFor" in data:
            schema["worksFor"] = {
                "@type": "Organization",
                "name": data["worksFor"].get("name", "") if isinstance(data["worksFor"], dict) else data["worksFor"]
            }
            
        return schema

    @staticmethod
    def generate_organization_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates Organization schema."""
        schema = SchemaGenerator._base_schema("Organization")
        schema["name"] = data.get("name", "")
        schema["url"] = data.get("url", "")
        
        if "logo" in data:
            schema["logo"] = data["logo"]
        if "sameAs" in data:
            schema["sameAs"] = data["sameAs"]
            
        if "contactPoint" in data:
            contacts = data["contactPoint"] if isinstance(data["contactPoint"], list) else [data["contactPoint"]]
            schema["contactPoint"] = []
            for contact in contacts:
                schema["contactPoint"].append({
                    "@type": "ContactPoint",
                    "telephone": contact.get("telephone", ""),
                    "contactType": contact.get("contactType", "customer service"),
                    "areaServed": contact.get("areaServed", "US"),
                    "availableLanguage": contact.get("availableLanguage", "English")
                })
                
        return schema

    @staticmethod
    def generate_breadcrumb_schema(items: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generates BreadcrumbList schema."""
        schema = SchemaGenerator._base_schema("BreadcrumbList")
        item_list = []
        
        for i, item in enumerate(items, 1):
            list_item = {
                "@type": "ListItem",
                "position": i,
                "name": item.get("name", "")
            }
            if "item" in item:
                list_item["item"] = item["item"]
            item_list.append(list_item)
            
        schema["itemListElement"] = item_list
        return schema

    @staticmethod
    def generate_video_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates VideoObject schema."""
        schema = SchemaGenerator._base_schema("VideoObject")
        schema["name"] = data.get("name", "")
        schema["description"] = data.get("description", "")
        schema["thumbnailUrl"] = data.get("thumbnailUrl", [])
        schema["uploadDate"] = data.get("uploadDate", "")
        
        if "duration" in data:
            schema["duration"] = data["duration"] # ISO 8601 e.g. PT1M33S
        if "contentUrl" in data:
            schema["contentUrl"] = data["contentUrl"]
        if "embedUrl" in data:
            schema["embedUrl"] = data["embedUrl"]
        if "interactionStatistic" in data:
            schema["interactionStatistic"] = {
                "@type": "InteractionCounter",
                "interactionType": { "@type": "WatchAction" },
                "userInteractionCount": data["interactionStatistic"]
            }
            
        return schema

    @staticmethod
    def generate_image_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates ImageObject schema for licensing."""
        schema = SchemaGenerator._base_schema("ImageObject")
        schema["contentUrl"] = data.get("contentUrl", "")
        
        if "license" in data:
            schema["license"] = data["license"]
        if "acquireLicensePage" in data:
            schema["acquireLicensePage"] = data["acquireLicensePage"]
        if "creditText" in data:
            schema["creditText"] = data["creditText"]
            
        if "creator" in data:
            schema["creator"] = {
                "@type": data["creator"].get("type", "Person"),
                "name": data["creator"].get("name", "")
            }
            
        if "copyrightNotice" in data:
            schema["copyrightNotice"] = data["copyrightNotice"]
            
        return schema

    @staticmethod
    def generate_speakable_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates Speakable schema (usually appended to Article or WebPage)."""
        schema = SchemaGenerator._base_schema("SpeakableSpecification")
        if "cssSelector" in data:
            schema["cssSelector"] = data["cssSelector"]
        elif "xpath" in data:
            schema["xpath"] = data["xpath"]
        else:
            # Default content selectors if none provided
            schema["cssSelector"] = ["headline", "summary"]
            
        return schema

    @staticmethod
    def generate_event_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates Event schema."""
        schema = SchemaGenerator._base_schema("Event")
        schema["name"] = data.get("name", "")
        schema["startDate"] = data.get("startDate", "")
        
        if "endDate" in data:
            schema["endDate"] = data["endDate"]
        if "eventAttendanceMode" in data:
            schema["eventAttendanceMode"] = f"https://schema.org/{data['eventAttendanceMode']}"
        if "eventStatus" in data:
            schema["eventStatus"] = f"https://schema.org/{data['eventStatus']}"
        if "image" in data:
            schema["image"] = data["image"]
        if "description" in data:
            schema["description"] = data["description"]
            
        if "location" in data:
            loc = data["location"]
            schema["location"] = {
                "@type": loc.get("type", "Place"),
                "name": loc.get("name", "")
            }
            if "address" in loc:
                schema["location"]["address"] = {
                    "@type": "PostalAddress",
                    "streetAddress": loc["address"].get("streetAddress", ""),
                    "addressLocality": loc["address"].get("addressLocality", ""),
                    "postalCode": loc["address"].get("postalCode", ""),
                    "addressRegion": loc["address"].get("addressRegion", ""),
                    "addressCountry": loc["address"].get("addressCountry", "")
                }
                
        if "offers" in data:
            schema["offers"] = {
                "@type": "Offer",
                "url": data["offers"].get("url", ""),
                "price": data["offers"].get("price", ""),
                "priceCurrency": data["offers"].get("priceCurrency", "USD"),
                "availability": f"https://schema.org/{data['offers'].get('availability', 'InStock')}",
                "validFrom": data["offers"].get("validFrom", "")
            }
            
        if "performer" in data:
            schema["performer"] = {
                "@type": data["performer"].get("type", "Person"),
                "name": data["performer"].get("name", "")
            }
            
        return schema

    @staticmethod
    def generate_recipe_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates Recipe schema."""
        schema = SchemaGenerator._base_schema("Recipe")
        schema["name"] = data.get("name", "")
        schema["image"] = data.get("image", [])
        
        if "author" in data:
            schema["author"] = {
                "@type": "Person",
                "name": data["author"]
            }
            
        if "datePublished" in data:
            schema["datePublished"] = data["datePublished"]
        if "description" in data:
            schema["description"] = data["description"]
        if "prepTime" in data:
            schema["prepTime"] = data["prepTime"]
        if "cookTime" in data:
            schema["cookTime"] = data["cookTime"]
        if "totalTime" in data:
            schema["totalTime"] = data["totalTime"]
        if "recipeYield" in data:
            schema["recipeYield"] = data["recipeYield"]
        if "recipeCategory" in data:
            schema["recipeCategory"] = data["recipeCategory"]
        if "recipeCuisine" in data:
            schema["recipeCuisine"] = data["recipeCuisine"]
            
        if "nutrition" in data:
            schema["nutrition"] = {
                "@type": "NutritionInformation",
                "calories": data["nutrition"].get("calories", "")
            }
            
        if "recipeIngredient" in data:
            schema["recipeIngredient"] = data["recipeIngredient"]
            
        if "recipeInstructions" in data:
            instructions = []
            for step in data["recipeInstructions"]:
                instructions.append({
                    "@type": "HowToStep",
                    "name": step.get("name", ""),
                    "text": step.get("text", ""),
                    "url": step.get("url", ""),
                    "image": step.get("image", "")
                })
            schema["recipeInstructions"] = instructions
            
        return schema

    @staticmethod
    def merge_schemas(schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combines multiple schema dictionaries into a single @graph JSON-LD structure.
        """
        if not schemas:
            return {}
            
        graph = []
        for schema in schemas:
            # Remove individual contexts when merging into a graph
            clean_schema = {k: v for k, v in schema.items() if k != "@context"}
            graph.append(clean_schema)
            
        return {
            "@context": "https://schema.org",
            "@graph": graph
        }

    @staticmethod
    def validate_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs basic validation on a schema dictionary.
        Returns a dict with 'is_valid' boolean and 'errors' list.
        """
        errors = []
        
        if "@context" not in schema:
            errors.append("Missing @context property.")
        elif schema["@context"] not in ["https://schema.org", "http://schema.org"]:
            errors.append("Invalid @context. Must be https://schema.org.")
            
        if "@graph" in schema:
            for i, node in enumerate(schema["@graph"]):
                if "@type" not in node:
                    errors.append(f"Node at index {i} in @graph is missing @type.")
        else:
            if "@type" not in schema:
                errors.append("Missing @type property.")
                
        # Some type-specific mandatory checks
        schema_type = schema.get("@type", "")
        if schema_type in ["Article", "BlogPosting", "NewsArticle"]:
            if "headline" not in schema: errors.append(f"{schema_type} missing headline.")
            if "image" not in schema: errors.append(f"{schema_type} missing image.")
            
        if schema_type == "FAQPage":
            if "mainEntity" not in schema or not schema["mainEntity"]:
                errors.append("FAQPage missing mainEntity (questions).")
                
        if schema_type == "Product":
            if "name" not in schema: errors.append("Product missing name.")
            if "review" not in schema and "aggregateRating" not in schema and "offers" not in schema:
                errors.append("Product should have offers, review, or aggregateRating.")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    @staticmethod
    def get_schema_report(content: str) -> Dict[str, Any]:
        """
        Analyzes text content and recommends schema types that might be applicable.
        """
        recommendations = ["Article", "BreadcrumbList", "Organization"] # Always recommended for standard web pages
        
        content_lower = content.lower()
        
        # Heuristics for FAQ
        question_count = len(re.findall(r'\?[\s\n]*[A-Z]', content))
        if question_count >= 2 or "frequently asked questions" in content_lower or "faq" in content_lower:
            recommendations.append("FAQPage")
            
        # Heuristics for HowTo
        if "how to" in content_lower or re.search(r'step\s+[1-9]', content_lower):
            recommendations.append("HowTo")
            
        # Heuristics for Product/Review
        price_patterns = len(re.findall(r'\$\d+(?:\.\d{2})?', content))
        if price_patterns > 0 and ("buy" in content_lower or "price" in content_lower or "add to cart" in content_lower):
            recommendations.append("Product")
            
        if "review" in content_lower and ("stars" in content_lower or "rating" in content_lower or re.search(r'[1-5]/5', content_lower)):
            recommendations.append("Review")
            
        # Heuristics for Recipe
        if "ingredients" in content_lower and ("cook" in content_lower or "bake" in content_lower or "prep time" in content_lower):
            recommendations.append("Recipe")
            
        # Heuristics for Event
        if "ticket" in content_lower and ("venue" in content_lower or "register" in content_lower or "location" in content_lower):
            date_matches = re.findall(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:st|nd|rd|th)?(?:, \d{4})?', content_lower, re.IGNORECASE)
            if date_matches:
                recommendations.append("Event")
                
        # Heuristics for LocalBusiness
        if re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', content) or "opening hours" in content_lower or "address" in content_lower:
            recommendations.append("LocalBusiness")
            
        # Video heuristics
        if "youtube.com" in content_lower or "vimeo.com" in content_lower or "<video" in content_lower:
            recommendations.append("VideoObject")

        return {
            "analyzed_length": len(content),
            "recommended_schemas": list(set(recommendations)),
            "detected_signals": {
                "questions_found": question_count,
                "prices_found": price_patterns
            }
        }

    @staticmethod
    def batch_generate_schemas(batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimized batch processing for generating schemas.
        Takes a list of dictionaries where each dict has a 'schema_type' key
        (e.g., 'Article', 'FAQPage', 'Product') and the 'data' to pass to the generator.
        
        Args:
            batch_data: List of dicts, e.g., [{"schema_type": "Article", "data": {...}}]
            
        Returns:
            List of generated schemas.
        """
        # Map of schema types to generator methods
        generators = {
            "Article": SchemaGenerator.generate_article_schema,
            "BlogPosting": SchemaGenerator.generate_article_schema,
            "FAQPage": SchemaGenerator.generate_faq_schema,
            "HowTo": SchemaGenerator.generate_howto_schema,
            "Review": SchemaGenerator.generate_review_schema,
            "AggregateRating": SchemaGenerator.generate_review_schema,
            "Product": SchemaGenerator.generate_product_schema,
            "LocalBusiness": SchemaGenerator.generate_local_business_schema,
            "Person": SchemaGenerator.generate_person_schema,
            "Organization": SchemaGenerator.generate_organization_schema,
            "BreadcrumbList": SchemaGenerator.generate_breadcrumb_schema,
            "VideoObject": SchemaGenerator.generate_video_schema,
            "ImageObject": SchemaGenerator.generate_image_schema,
            "SpeakableSpecification": SchemaGenerator.generate_speakable_schema,
            "Event": SchemaGenerator.generate_event_schema,
            "Recipe": SchemaGenerator.generate_recipe_schema,
        }
        
        results = []
        for item in batch_data:
            stype = item.get("schema_type")
            data = item.get("data", {})
            
            generator = generators.get(stype)
            if generator:
                # FAQPage expects a list of questions, others expect dict
                if stype == "FAQPage" and isinstance(data, list):
                    results.append(generator(data))
                elif stype == "BreadcrumbList" and isinstance(data, list):
                    results.append(generator(data))
                else:
                    results.append(generator(data))
            else:
                # Fallback to generic if unsupported
                fallback = SchemaGenerator._base_schema(stype)
                fallback.update(data)
                results.append(fallback)
                
        return results
