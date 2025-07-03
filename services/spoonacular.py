import os
import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SpoonacularService:
    """Service for interacting with Spoonacular API"""
    
    def __init__(self):
        self.api_key = os.environ.get("SPOONACULAR_API_KEY", "default_key")
        self.base_url = "https://api.spoonacular.com"
        self.session = requests.Session()
        
    def search_recipes_by_name(self, dish_name: str, number: int = 5) -> List[Dict]:
        """
        Search for recipes by dish name
        """
        try:
            endpoint = f"{self.base_url}/recipes/complexSearch"
            params = {
                'apiKey': self.api_key,
                'query': dish_name,
                'number': number,
                'addRecipeInformation': True,
                'fillIngredients': True,
                'instructionsRequired': False
            }
            
            logger.info(f"Searching Spoonacular for dish: {dish_name}")
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            recipes = data.get('results', [])
            
            logger.info(f"Found {len(recipes)} recipes for '{dish_name}'")
            return recipes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Spoonacular API request failed: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Spoonacular search: {str(e)}")
            return []
    
    def get_recipe_ingredients(self, recipe_id: int) -> List[Dict]:
        """
        Get detailed ingredients for a specific recipe
        """
        try:
            endpoint = f"{self.base_url}/recipes/{recipe_id}/ingredientWidget.json"
            params = {
                'apiKey': self.api_key
            }
            
            logger.info(f"Getting ingredients for recipe ID: {recipe_id}")
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            ingredients = data.get('ingredients', [])
            
            logger.info(f"Found {len(ingredients)} ingredients for recipe {recipe_id}")
            return ingredients
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Spoonacular ingredient request failed: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting ingredients: {str(e)}")
            return []
    
    def extract_ingredients_from_recipes(self, recipes: List[Dict]) -> List[str]:
        """
        Extract ingredient names from recipe data
        """
        ingredients = set()
        
        for recipe in recipes:
            # Get ingredients from extended ingredients
            if 'extendedIngredients' in recipe:
                for ingredient in recipe['extendedIngredients']:
                    if 'name' in ingredient:
                        ingredients.add(ingredient['name'].lower())
                    elif 'originalName' in ingredient:
                        ingredients.add(ingredient['originalName'].lower())
        
        return sorted(list(ingredients))
    
    def find_ingredients_for_dish(self, dish_name: str) -> Dict:
        """
        Find ingredients for a dish name
        Returns dict with ingredients and metadata
        """
        try:
            # Search for recipes
            recipes = self.search_recipes_by_name(dish_name)
            
            if not recipes:
                logger.warning(f"No recipes found for dish: {dish_name}")
                return {
                    'dish_name': dish_name,
                    'ingredients': [],
                    'source': 'spoonacular',
                    'found_recipes': False,
                    'recipe_count': 0
                }
            
            # Extract ingredients from recipes
            ingredients = self.extract_ingredients_from_recipes(recipes)
            
            return {
                'dish_name': dish_name,
                'ingredients': ingredients,
                'source': 'spoonacular',
                'found_recipes': True,
                'recipe_count': len(recipes),
                'confidence': min(1.0, len(recipes) / 3)  # Higher confidence with more recipes
            }
            
        except Exception as e:
            logger.error(f"Error finding ingredients for dish '{dish_name}': {str(e)}")
            return {
                'dish_name': dish_name,
                'ingredients': [],
                'source': 'spoonacular',
                'found_recipes': False,
                'error': str(e)
            }
