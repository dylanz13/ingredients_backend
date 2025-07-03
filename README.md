# Restaurant OCR Ingredient Processor

## Overview

This application is a Flask-based web service that processes OCR text from restaurant menus to extract dish names and suggest complete ingredient lists. The system uses a combination of OpenAI's GPT-4 and Spoonacular API to analyze menu text and provide comprehensive ingredient suggestions for dishes.

## System Architecture

The application follows a service-oriented architecture with the following layers:

1. **Web Layer**: Flask application serving both API endpoints and a web interface
2. **Service Layer**: Three main services handling different aspects of processing
3. **Integration Layer**: External API integrations with OpenAI and Spoonacular

### Key Components

#### Backend Services
- **OCRProcessor**: Main orchestrator that coordinates the processing pipeline
- **OpenAIService**: Handles GPT-4 integration for text analysis and ingredient suggestions
- **SpoonacularService**: Manages recipe search and ingredient data retrieval

#### Web Interface
- **Flask App**: Serves both API endpoints and a testing interface
- **Static Assets**: HTML template with JavaScript for interactive testing
- **API Endpoints**: RESTful endpoints for OCR text processing

## Data Flow

1. **Input**: OCR text containing dish names and partial ingredients
2. **Analysis**: OpenAI GPT-4 analyzes the text to extract structured dish information
3. **Recipe Search**: Spoonacular API searches for matching recipes
4. **Fallback Search**: If no recipes found, GPT-4 simplifies dish name and retries Spoonacular
5. **Quality Control**: GPT-4 performs sanity check on recipe ingredients, removing invalid items
6. **Enhancement**: GPT-4 suggests additional commonly-missing ingredients (toppings, seasonings, etc.)
7. **Output**: Structured JSON response with verified and enhanced ingredient lists

## External Dependencies

### Required APIs
- **OpenAI API**: Used for text analysis and ingredient suggestions (GPT-4o model)
- **Spoonacular API**: Provides recipe data and ingredient information

### Python Libraries
- **Flask**: Web framework for API and interface
- **Flask-CORS**: Cross-origin resource sharing support
- **OpenAI**: Official OpenAI Python client
- **Requests**: HTTP library for API calls

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API authentication
- `SPOONACULAR_API_KEY`: Spoonacular API authentication
- `SESSION_SECRET`: Flask session security (optional, defaults to dev key)

## Deployment Strategy

The application is configured for Replit deployment with:
- Main entry point through `main.py`
- Flask development server configuration
- Environment variable management
- Static file serving for the web interface

## Changelog
- July 03, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.

