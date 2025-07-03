import os
import json
import logging
from typing import Dict, List
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI API"""
    
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "default_key")
        self.client = OpenAI(api_key=self.api_key)
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
        
    def suggest_missing_ingredients(self, dish_name: str, known_ingredients: List[str], 
                                   ocr_text: str = "") -> Dict:
        """
        Use ChatGPT to suggest missing ingredients for a dish
        """
        try:
            # Prepare the prompt
            prompt = self._build_ingredient_suggestion_prompt(
                dish_name, known_ingredients, ocr_text
            )
            
            logger.info(f"Requesting ingredient suggestions for: {dish_name}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a culinary expert specializing in restaurant dishes and ingredients. "
                                 "Analyze dish names and known ingredients to suggest commonly missing ingredients "
                                 "such as toppings, garnishes, seasonings, and components often omitted from menus. "
                                 "Respond with JSON in the specified format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            
            # Validate and clean the response
            suggested_ingredients = result.get('suggested_ingredients', [])
            reasoning = result.get('reasoning', '')
            confidence = result.get('confidence', 0.5)
            
            logger.info(f"ChatGPT suggested {len(suggested_ingredients)} additional ingredients")
            
            return {
                'dish_name': dish_name,
                'suggested_ingredients': suggested_ingredients,
                'reasoning': reasoning,
                'confidence': max(0.0, min(1.0, confidence)),
                'source': 'openai',
                'model': self.model
            }
            
        except Exception as e:
            logger.error(f"Error getting ingredient suggestions: {str(e)}")
            return {
                'dish_name': dish_name,
                'suggested_ingredients': [],
                'reasoning': '',
                'confidence': 0.0,
                'source': 'openai',
                'error': str(e)
            }
    
    def _build_ingredient_suggestion_prompt(self, dish_name: str, known_ingredients: List[str], 
                                          ocr_text: str) -> str:
        """
        Build the prompt for ingredient suggestion
        """
        prompt = f"""
Analyze this restaurant dish and suggest missing ingredients:

Dish Name: {dish_name}

Known Ingredients (from recipe database):
{', '.join(known_ingredients) if known_ingredients else 'None found'}

Original OCR Text (may contain additional clues):
{ocr_text}

IMPORTANT: First, perform a sanity check on the recipe database ingredients:
1. Do the listed ingredients actually make sense for this dish?
2. Are there any obviously incorrect or unrelated ingredients?
3. Are the ingredients appropriate for the cooking style/cuisine?

Then, suggest common ingredients that are likely missing from the known ingredients list. Focus on:
1. Common toppings and garnishes
2. Seasonings and spices typically used
3. Cooking ingredients often omitted from menus
4. Preparation components (oils, vinegars, etc.)
5. Side accompaniments commonly served with this dish

Consider the restaurant context and typical preparation methods.

Respond with JSON in this exact format:
{{
  "sanity_check": {{
    "recipe_ingredients_valid": true/false,
    "issues_found": ["list any problematic ingredients from the database"],
    "corrected_ingredients": ["list of ingredients that should replace invalid ones"]
  }},
  "suggested_ingredients": ["ingredient1", "ingredient2", ...],
  "reasoning": "Brief explanation of why these ingredients are likely included",
  "confidence": 0.8
}}

Keep ingredients as simple names (e.g., "olive oil", "garlic", "parsley").
Confidence should be between 0.0 and 1.0.
"""
        return prompt
    
    def analyze_ocr_text(self, ocr_text: str) -> Dict:
        """
        Analyze OCR text to extract dish names and potential ingredients
        """
        try:
            prompt = f"""
Analyze this OCR text from a restaurant menu and extract dish names and any ingredients mentioned:

OCR Text:
{ocr_text}

Extract and structure the information. Look for:
1. Dish/menu item names
2. Any ingredients explicitly mentioned
3. Cooking methods or preparation styles
4. Potential allergen information

Respond with JSON in this exact format:
{{
  "dishes": [
    {{
      "name": "dish name",
      "mentioned_ingredients": ["ingredient1", "ingredient2"],
      "cooking_method": "method if mentioned",
      "confidence": 0.9
    }}
  ],
  "overall_confidence": 0.8,
  "text_quality": "good/fair/poor"
}}
"""
            
            logger.info("Analyzing OCR text with ChatGPT")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing restaurant menu text and extracting dish information. "
                                 "Focus on identifying complete dish names and any ingredients explicitly mentioned."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            
            logger.info(f"OCR analysis found {len(result.get('dishes', []))} dishes")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing OCR text: {str(e)}")
            return {
                'dishes': [],
                'overall_confidence': 0.0,
                'text_quality': 'poor',
                'error': str(e)
            }
    
    def split_dish_name(self, dish_name: str) -> Dict:
        """
        Split dish name into simpler components for better Spoonacular search
        """
        try:
            prompt = f"""
Analyze this dish name and provide a simpler, more searchable alternative:

Dish Name: {dish_name}

The goal is to create a simplified version that would have better results in a recipe database search.
For example:
- "Grandma's Famous Chocolate Chip Cookies" → "Chocolate Chip Cookies"
- "BBQ Bacon Cheeseburger Deluxe" → "BBQ Bacon Cheeseburger"
- "Traditional Italian Margherita Pizza" → "Margherita Pizza"

Respond with JSON in this exact format:
{{
  "original_name": "{dish_name}",
  "alternative_name": "simplified name",
  "reasoning": "Brief explanation of the simplification"
}}
"""
            
            logger.info(f"Splitting dish name: {dish_name}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at simplifying dish names for recipe database searches. "
                                 "Focus on removing descriptive adjectives while keeping the core dish identity."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500
            )
            
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            
            logger.info(f"Split result: {result.get('alternative_name', 'No alternative found')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error splitting dish name: {str(e)}")
            return {
                'original_name': dish_name,
                'alternative_name': None,
                'reasoning': f'Error: {str(e)}',
                'error': str(e)
            }
    
    def sanity_check_ingredients(self, dish_name: str, ingredients: List[str]) -> Dict:
        """
        Perform sanity check on ingredients from recipe database
        """
        try:
            prompt = f"""
Perform a sanity check on these ingredients for the dish:

Dish Name: {dish_name}

Ingredients from recipe database:
{', '.join(ingredients)}

Analyze if these ingredients make sense for this dish:
1. Are any ingredients completely unrelated to this dish?
2. Are there any obvious mistakes or incorrect ingredients?
3. Are all ingredients appropriate for the cooking style/cuisine?

Remove any ingredients that don't belong and provide the verified list.

Respond with JSON in this exact format:
{{
  "verified_ingredients": ["ingredient1", "ingredient2", ...],
  "removed_ingredients": ["removed1", "removed2", ...],
  "reasoning": "Brief explanation of what was removed and why"
}}
"""
            
            logger.info(f"Sanity checking ingredients for: {dish_name}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a culinary expert performing quality control on recipe ingredients. "
                                 "Remove any ingredients that are clearly inappropriate or unrelated to the dish."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=800
            )
            
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            
            verified_ingredients = result.get('verified_ingredients', ingredients)
            removed_count = len(result.get('removed_ingredients', []))
            
            logger.info(f"Sanity check complete: {len(verified_ingredients)} verified, {removed_count} removed")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in sanity check: {str(e)}")
            return {
                'verified_ingredients': ingredients,
                'removed_ingredients': [],
                'reasoning': f'Error during sanity check: {str(e)}',
                'error': str(e)
            }
    
    def suggest_additional_ingredients(self, dish_name: str, verified_ingredients: List[str], 
                                     mentioned_ingredients: List[str], ocr_text: str) -> Dict:
        """
        Suggest additional ingredients that are commonly missing
        """
        try:
            prompt = f"""
Suggest additional ingredients for this dish that are commonly missing from menus:

Dish Name: {dish_name}

Verified ingredients from recipe database:
{', '.join(verified_ingredients) if verified_ingredients else 'None'}

Ingredients mentioned in menu:
{', '.join(mentioned_ingredients) if mentioned_ingredients else 'None'}

Original OCR text (context):
{ocr_text}

Focus on suggesting ingredients that are:
1. Common toppings and garnishes
2. Base ingredients (oils, seasonings, etc.)
3. Typical accompaniments
4. Ingredients that are often assumed/not mentioned

Avoid suggesting ingredients that are already in the verified list.

Respond with JSON in this exact format:
{{
  "suggested_ingredients": ["ingredient1", "ingredient2", ...],
  "reasoning": "Brief explanation of why these ingredients are commonly included",
  "confidence": 0.8
}}

Keep ingredients as simple names (e.g., "olive oil", "garlic", "parsley").
Confidence should be between 0.0 and 1.0.
"""
            
            logger.info(f"Suggesting additional ingredients for: {dish_name}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a culinary expert specializing in identifying commonly omitted ingredients. "
                                 "Focus on ingredients that restaurants typically use but don't list on menus."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            
            suggested_ingredients = result.get('suggested_ingredients', [])
            reasoning = result.get('reasoning', '')
            confidence = result.get('confidence', 0.5)
            
            logger.info(f"Suggested {len(suggested_ingredients)} additional ingredients")
            
            return {
                'suggested_ingredients': suggested_ingredients,
                'reasoning': reasoning,
                'confidence': max(0.0, min(1.0, confidence)),
                'source': 'openai',
                'model': self.model
            }
            
        except Exception as e:
            logger.error(f"Error suggesting additional ingredients: {str(e)}")
            return {
                'suggested_ingredients': [],
                'reasoning': f'Error: {str(e)}',
                'confidence': 0.0,
                'source': 'openai',
                'error': str(e)
            }
