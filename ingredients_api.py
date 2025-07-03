from flask import Flask, request, jsonify
import requests
import openai
import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import os
from functools import wraps
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

@dataclass
class IngredientResult:
    """Data class for ingredient processing results"""
    original_text: str
    dish_name: str
    spoonacular_ingredients: List[str]
    ai_suggested_ingredients: List[str]
    final_ingredients: List[str]
    confidence_score: float

class TextProcessor:
    """Handles OCR text processing and dish name extraction"""
    
    @staticmethod
    def clean_ocr_text(text: str) -> str:
        """Clean and normalize OCR text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s\-&,.()\'/]', '', text)
        
        # Fix common OCR mistakes
        replacements = {
            'chícken': 'chicken',
            'chíck': 'chicken',
            'beéf': 'beef',
            'pórk': 'pork',
            'tómato': 'tomato',
            'oníon': 'onion',
            'chése': 'cheese',
            'chéese': 'cheese'
        }
        
        for wrong, correct in replacements.items():
            text = text.replace(wrong, correct)
        
        return text
    
    @staticmethod
    def extract_dish_name(text: str) -> str:
        """Extract the most likely dish name from OCR text"""
        lines = text.split('\n')
        
        # Look for the first substantial line that could be a dish name
        for line in lines:
            line = line.strip()
            if len(line) > 3 and not line.isdigit():
                # Remove price patterns
                line = re.sub(r'\$?\d+\.?\d*', '', line)
                line = line.strip()
                if line:
                    return line
        
        # Fallback: return first 50 characters
        return text[:50].strip()

class SpoonacularClient:
    """Handles Spoonacular API interactions"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.spoonacular.com"
    
    def search_recipe_by_dish_name(self, dish_name: str) -> Optional[Dict]:
        """Search for recipe by dish name"""
        try:
            url = f"{self.base_url}/recipes/complexSearch"
            params = {
                'apiKey': self.api_key,
                'query': dish_name,
                'number': 1,
                'addRecipeInformation': True,
                'fillIngredients': True
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('results'):
                return data['results'][0]
            return None
            
        except Exception as e:
            logger.error(f"Spoonacular search error: {e}")
            return None
    
    def get_recipe_ingredients(self, recipe_id: int) -> List[str]:
        """Get detailed ingredients for a recipe"""
        try:
            url = f"{self.base_url}/recipes/{recipe_id}/ingredientWidget.json"
            params = {'apiKey': self.api_key}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            ingredients = []
            
            for ingredient in data.get('ingredients', []):
                name = ingredient.get('name', '').strip()
                if name:
                    ingredients.append(name)
            
            return ingredients
            
        except Exception as e:
            logger.error(f"Spoonacular ingredients error: {e}")
            return []
    
    def analyze_dish_ingredients(self, dish_name: str, ocr_text: str) -> List[str]:
        """Analyze dish and return ingredient list"""
        # First, try to find exact recipe match
        recipe = self.search_recipe_by_dish_name(dish_name)
        
        if recipe:
            # Get detailed ingredients
            recipe_id = recipe.get('id')
            if recipe_id:
                ingredients = self.get_recipe_ingredients(recipe_id)
                if ingredients:
                    return ingredients
            
            # Fallback to basic recipe ingredients
            extended_ingredients = recipe.get('extendedIngredients', [])
            if extended_ingredients:
                return [ing.get('name', '').strip() for ing in extended_ingredients if ing.get('name')]
        
        # If no recipe found, try ingredient parsing from OCR text
        return self.extract_ingredients_from_text(ocr_text)
    
    def extract_ingredients_from_text(self, text: str) -> List[str]:
        """Extract potential ingredients from OCR text"""
        # Common ingredient keywords
        common_ingredients = {
            'chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'shrimp',
            'rice', 'pasta', 'noodles', 'bread', 'tortilla',
            'cheese', 'mozzarella', 'cheddar', 'parmesan',
            'tomato', 'onion', 'garlic', 'pepper', 'mushroom',
            'lettuce', 'spinach', 'basil', 'cilantro', 'parsley',
            'oil', 'butter', 'cream', 'milk', 'egg',
            'salt', 'pepper', 'spice', 'herbs'
        }
        
        text_lower = text.lower()
        found_ingredients = []
        
        for ingredient in common_ingredients:
            if ingredient in text_lower:
                found_ingredients.append(ingredient)
        
        return found_ingredients

class AIEnhancer:
    """Handles ChatGPT integration for ingredient enhancement"""
    
    @staticmethod
    def enhance_ingredients(dish_name: str, ocr_text: str, 
                          current_ingredients: List[str]) -> List[str]:
        """Use ChatGPT to suggest additional ingredients"""
        try:
            # Prepare the prompt
            ingredients_str = ", ".join(current_ingredients) if current_ingredients else "None found"
            
            prompt = f"""
Based on the dish name "{dish_name}" and OCR text from a restaurant menu:
"{ocr_text}"

Current ingredients identified: {ingredients_str}

Please suggest additional common ingredients that are typically found in this dish but might not be explicitly listed. Consider:
1. Common toppings and garnishes
2. Base ingredients (oils, seasonings, etc.)
3. Typical accompaniments
4. Ingredients that are often assumed/not mentioned

Return only a simple comma-separated list of ingredient names, no explanations.
Maximum 8 additional ingredients.
"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a culinary expert helping identify ingredients in restaurant dishes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Parse the response
            suggested_ingredients = []
            for ingredient in ai_response.split(','):
                ingredient = ingredient.strip().lower()
                if ingredient and len(ingredient) > 2:
                    suggested_ingredients.append(ingredient)
            
            return suggested_ingredients[:8]  # Limit to 8 suggestions
            
        except Exception as e:
            logger.error(f"ChatGPT enhancement error: {e}")
            return []

class IngredientProcessor:
    """Main processor that orchestrates the entire pipeline"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.spoonacular = SpoonacularClient(SPOONACULAR_API_KEY)
        self.ai_enhancer = AIEnhancer()
    
    def process_ocr_text(self, ocr_text: str) -> IngredientResult:
        """Process OCR text through the entire pipeline"""
        # Step 1: Clean and process OCR text
        cleaned_text = self.text_processor.clean_ocr_text(ocr_text)
        dish_name = self.text_processor.extract_dish_name(cleaned_text)
        
        logger.info(f"Processing dish: {dish_name}")
        
        # Step 2: Get ingredients from Spoonacular
        spoonacular_ingredients = self.spoonacular.analyze_dish_ingredients(
            dish_name, cleaned_text
        )
        
        # Step 3: Enhance with AI suggestions
        ai_suggested = self.ai_enhancer.enhance_ingredients(
            dish_name, cleaned_text, spoonacular_ingredients
        )
        
        # Step 4: Combine and deduplicate ingredients
        final_ingredients = self.combine_ingredients(
            spoonacular_ingredients, ai_suggested
        )
        
        # Step 5: Calculate confidence score
        confidence = self.calculate_confidence(
            dish_name, spoonacular_ingredients, ai_suggested
        )
        
        return IngredientResult(
            original_text=ocr_text,
            dish_name=dish_name,
            spoonacular_ingredients=spoonacular_ingredients,
            ai_suggested_ingredients=ai_suggested,
            final_ingredients=final_ingredients,
            confidence_score=confidence
        )
    
    def combine_ingredients(self, spoonacular_ingredients: List[str], 
                          ai_suggested: List[str]) -> List[str]:
        """Combine and deduplicate ingredients from different sources"""
        combined = set()
        
        # Add Spoonacular ingredients
        for ingredient in spoonacular_ingredients:
            combined.add(ingredient.lower().strip())
        
        # Add AI suggested ingredients
        for ingredient in ai_suggested:
            combined.add(ingredient.lower().strip())
        
        # Remove empty strings and sort
        final_ingredients = sorted([ing for ing in combined if ing])
        
        return final_ingredients
    
    def calculate_confidence(self, dish_name: str, 
                           spoonacular_ingredients: List[str],
                           ai_suggested: List[str]) -> float:
        """Calculate confidence score for the results"""
        confidence = 0.0
        
        # Base confidence from having a dish name
        if dish_name and len(dish_name) > 3:
            confidence += 0.3
        
        # Confidence from Spoonacular results
        if spoonacular_ingredients:
            confidence += 0.4
        
        # Confidence from AI enhancement
        if ai_suggested:
            confidence += 0.3
        
        return min(confidence, 1.0)

# Initialize processor
processor = IngredientProcessor()

# API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'spoonacular_configured': bool(SPOONACULAR_API_KEY),
        'openai_configured': bool(OPENAI_API_KEY)
    })

@app.route('/process-ingredients', methods=['POST'])
def process_ingredients():
    """Main endpoint to process OCR text and return ingredients"""
    try:
        # Validate request
        if not request.json or 'ocr_text' not in request.json:
            return jsonify({
                'error': 'Missing ocr_text in request body'
            }), 400
        
        ocr_text = request.json['ocr_text']
        
        if not ocr_text or not ocr_text.strip():
            return jsonify({
                'error': 'OCR text cannot be empty'
            }), 400
        
        # Process the text
        result = processor.process_ocr_text(ocr_text)
        
        # Return structured response
        return jsonify({
            'success': True,
            'dish_name': result.dish_name,
            'ingredients': result.final_ingredients,
            'confidence_score': result.confidence_score,
            'details': {
                'spoonacular_ingredients': result.spoonacular_ingredients,
                'ai_suggested_ingredients': result.ai_suggested_ingredients,
                'original_text': result.original_text
            }
        })
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({
            'error': 'Internal server error occurred',
            'success': False
        }), 500

@app.route('/process-ingredients/simple', methods=['POST'])
def process_ingredients_simple():
    """Simplified endpoint that returns only the ingredient list"""
    try:
        if not request.json or 'ocr_text' not in request.json:
            return jsonify({
                'error': 'Missing ocr_text in request body'
            }), 400
        
        ocr_text = request.json['ocr_text']
        result = processor.process_ocr_text(ocr_text)
        
        return jsonify({
            'ingredients': result.final_ingredients
        })
        
    except Exception as e:
        logger.error(f"Simple processing error: {e}")
        return jsonify({
            'error': 'Processing failed',
            'ingredients': []
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Validate configuration
    if not SPOONACULAR_API_KEY:
        logger.warning("SPOONACULAR_API_KEY not configured")
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
