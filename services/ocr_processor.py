import logging
from typing import Dict, List
from .spoonacular import SpoonacularService
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)

class OCRProcessor:
    """Main processor for OCR text processing workflow"""
    
    def __init__(self):
        self.spoonacular = SpoonacularService()
        self.openai = OpenAIService()
    
    def process_ocr_text(self, ocr_text: str) -> Dict:
        """
        Main processing pipeline for OCR text
        """
        try:
            logger.info("Starting OCR text processing")
            
            # Step 1: Analyze OCR text with ChatGPT to extract dish names
            logger.info("Step 1: Analyzing OCR text with ChatGPT")
            ocr_analysis = self.openai.analyze_ocr_text(ocr_text)
            
            dishes = ocr_analysis.get('dishes', [])
            if not dishes:
                logger.warning("No dishes found in OCR text")
                return {
                    'success': False,
                    'message': 'No dishes could be identified in the OCR text',
                    'ocr_analysis': ocr_analysis,
                    'dishes': []
                }
            
            # Step 2: Process each dish
            processed_dishes = []
            for dish_data in dishes:
                dish_name = dish_data.get('name', '').strip()
                if not dish_name:
                    continue
                    
                logger.info(f"Processing dish: {dish_name}")
                processed_dish = self._process_single_dish(
                    dish_name, 
                    dish_data.get('mentioned_ingredients', []),
                    ocr_text
                )
                processed_dishes.append(processed_dish)
            
            # Step 3: Compile final results
            result = {
                'success': True,
                'total_dishes': len(processed_dishes),
                'ocr_analysis': ocr_analysis,
                'dishes': processed_dishes,
                'processing_summary': self._generate_processing_summary(processed_dishes)
            }
            
            logger.info(f"OCR processing completed successfully for {len(processed_dishes)} dishes")
            return result
            
        except Exception as e:
            logger.error(f"Error in OCR processing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'An error occurred while processing the OCR text'
            }
    
    def _process_single_dish(self, dish_name: str, mentioned_ingredients: List[str], 
                           ocr_text: str) -> Dict:
        """
        Process a single dish through the complete pipeline
        """
        try:
            # Step 1: Get ingredients from Spoonacular
            logger.info(f"Getting Spoonacular ingredients for: {dish_name}")
            spoonacular_result = self.spoonacular.find_ingredients_for_dish(dish_name)
            
            # Step 2: If no results, try splitting dish name and retry
            if not spoonacular_result.get('found_recipes', False):
                logger.info(f"No recipes found for '{dish_name}', trying to split dish name")
                split_result = self.openai.split_dish_name(dish_name)
                if split_result.get('alternative_name'):
                    logger.info(f"Retrying with alternative name: {split_result['alternative_name']}")
                    spoonacular_result = self.spoonacular.find_ingredients_for_dish(split_result['alternative_name'])
            
            # Step 3: If we have Spoonacular results, perform sanity check
            verified_ingredients = []
            if spoonacular_result.get('found_recipes', False):
                logger.info(f"Performing sanity check on Spoonacular ingredients for: {dish_name}")
                sanity_check_result = self.openai.sanity_check_ingredients(
                    dish_name, spoonacular_result.get('ingredients', [])
                )
                verified_ingredients = sanity_check_result.get('verified_ingredients', [])
            
            # Step 4: Get ChatGPT suggestions for additional ingredients
            logger.info(f"Getting ChatGPT suggestions for additional ingredients: {dish_name}")
            additional_result = self.openai.suggest_additional_ingredients(
                dish_name, verified_ingredients, mentioned_ingredients, ocr_text
            )
            
            # Step 5: Combine all ingredients
            all_ingredients = self._combine_ingredients(
                verified_ingredients + [ing.lower() for ing in mentioned_ingredients],
                additional_result.get('suggested_ingredients', [])
            )
            
            # Step 6: Compile dish result
            dish_result = {
                'dish_name': dish_name,
                'ingredients': {
                    'from_menu': mentioned_ingredients,
                    'from_spoonacular': spoonacular_result.get('ingredients', []),
                    'verified_spoonacular': verified_ingredients,
                    'suggested_by_ai': additional_result.get('suggested_ingredients', []),
                    'combined_list': all_ingredients
                },
                'metadata': {
                    'spoonacular_confidence': spoonacular_result.get('confidence', 0.0),
                    'ai_confidence': additional_result.get('confidence', 0.0),
                    'recipes_found': spoonacular_result.get('recipe_count', 0),
                    'ai_reasoning': additional_result.get('reasoning', ''),
                    'total_ingredients': len(all_ingredients),
                    'sanity_check_performed': spoonacular_result.get('found_recipes', False)
                },
                'sources': {
                    'spoonacular_success': spoonacular_result.get('found_recipes', False),
                    'openai_success': 'error' not in additional_result
                }
            }
            
            return dish_result
            
        except Exception as e:
            logger.error(f"Error processing dish '{dish_name}': {str(e)}")
            return {
                'dish_name': dish_name,
                'ingredients': {
                    'from_menu': mentioned_ingredients,
                    'from_spoonacular': [],
                    'verified_spoonacular': [],
                    'suggested_by_ai': [],
                    'combined_list': mentioned_ingredients
                },
                'metadata': {
                    'error': str(e),
                    'total_ingredients': len(mentioned_ingredients)
                },
                'sources': {
                    'spoonacular_success': False,
                    'openai_success': False
                }
            }
    
    def _combine_ingredients(self, known_ingredients: List[str], 
                           suggested_ingredients: List[str]) -> List[str]:
        """
        Combine and deduplicate ingredients from different sources
        """
        # Convert to lowercase for comparison
        combined = set()
        
        # Add known ingredients
        for ingredient in known_ingredients:
            combined.add(ingredient.lower().strip())
        
        # Add suggested ingredients (avoid duplicates)
        for ingredient in suggested_ingredients:
            cleaned = ingredient.lower().strip()
            if cleaned and cleaned not in combined:
                combined.add(cleaned)
        
        # Return sorted list
        return sorted(list(combined))
    
    def _generate_processing_summary(self, dishes: List[Dict]) -> Dict:
        """
        Generate summary statistics for the processing
        """
        try:
            total_dishes = len(dishes)
            spoonacular_successes = sum(1 for d in dishes if d.get('sources', {}).get('spoonacular_success', False))
            openai_successes = sum(1 for d in dishes if d.get('sources', {}).get('openai_success', False))
            
            total_ingredients = sum(d.get('metadata', {}).get('total_ingredients', 0) for d in dishes)
            avg_ingredients = total_ingredients / total_dishes if total_dishes > 0 else 0
            
            return {
                'total_dishes_processed': total_dishes,
                'spoonacular_success_rate': spoonacular_successes / total_dishes if total_dishes > 0 else 0,
                'openai_success_rate': openai_successes / total_dishes if total_dishes > 0 else 0,
                'total_ingredients_found': total_ingredients,
                'average_ingredients_per_dish': round(avg_ingredients, 1)
            }
            
        except Exception as e:
            logger.error(f"Error generating processing summary: {str(e)}")
            return {
                'error': str(e)
            }
