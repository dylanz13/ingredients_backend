// JavaScript for the OCR Ingredient Processor interface

document.addEventListener('DOMContentLoaded', function() {
    const ocrForm = document.getElementById('ocrForm');
    const ocrText = document.getElementById('ocrText');
    const processBtn = document.getElementById('processBtn');
    const resultsCard = document.getElementById('resultsCard');
    const resultsContent = document.getElementById('resultsContent');
    const healthCheckBtn = document.getElementById('healthCheckBtn');
    const healthStatus = document.getElementById('healthStatus');

    // Process OCR form submission
    ocrForm.addEventListener('submit', function(e) {
        e.preventDefault();
        processOCRText();
    });

    // Health check button
    healthCheckBtn.addEventListener('click', function() {
        performHealthCheck();
    });

    async function processOCRText() {
        const text = ocrText.value.trim();
        
        if (!text) {
            showError('Please enter some OCR text to process.');
            return;
        }

        // Show loading state
        processBtn.disabled = true;
        processBtn.innerHTML = '<span class="loading-spinner me-2"></span>Processing...';
        resultsCard.style.display = 'none';

        try {
            const response = await fetch('/api/process-ocr', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ocr_text: text
                })
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data);
                resultsCard.style.display = 'block';
                resultsCard.scrollIntoView({ behavior: 'smooth' });
            } else {
                showError(data.error || 'An error occurred while processing the OCR text.');
            }
        } catch (error) {
            showError('Network error: Unable to connect to the API.');
            console.error('Error:', error);
        } finally {
            // Reset button state
            processBtn.disabled = false;
            processBtn.innerHTML = '<i class="fas fa-cogs me-2"></i>Process OCR Text';
        }
    }

    async function performHealthCheck() {
        healthCheckBtn.disabled = true;
        healthCheckBtn.innerHTML = '<span class="loading-spinner me-2"></span>Checking...';
        
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            if (response.ok) {
                healthStatus.innerHTML = `
                    <div class="alert alert-success alert-sm">
                        <i class="fas fa-check-circle me-2"></i>
                        ${data.message}
                    </div>
                `;
            } else {
                healthStatus.innerHTML = `
                    <div class="alert alert-danger alert-sm">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        API is not responding properly
                    </div>
                `;
            }
        } catch (error) {
            healthStatus.innerHTML = `
                <div class="alert alert-danger alert-sm">
                    <i class="fas fa-times-circle me-2"></i>
                    Unable to connect to API
                </div>
            `;
        } finally {
            healthCheckBtn.disabled = false;
            healthCheckBtn.innerHTML = '<i class="fas fa-heartbeat me-2"></i>Check API Health';
        }
    }

    function displayResults(data) {
        if (!data.success) {
            showError(data.message || 'Processing failed');
            return;
        }

        let html = '';

        // Processing Summary
        if (data.processing_summary) {
            html += createProcessingSummary(data.processing_summary);
        }

        // Dishes
        if (data.dishes && data.dishes.length > 0) {
            html += '<h6 class="mt-4"><i class="fas fa-utensils me-2"></i>Processed Dishes</h6>';
            data.dishes.forEach(dish => {
                html += createDishCard(dish);
            });
        }

        // OCR Analysis
        if (data.ocr_analysis) {
            html += createOCRAnalysis(data.ocr_analysis);
        }

        resultsContent.innerHTML = html;
    }

    function createProcessingSummary(summary) {
        return `
            <div class="processing-summary">
                <h6><i class="fas fa-chart-bar me-2"></i>Processing Summary</h6>
                <div class="row">
                    <div class="col-md-6">
                        <p class="mb-1"><strong>Dishes Processed:</strong> ${summary.total_dishes_processed}</p>
                        <p class="mb-1"><strong>Total Ingredients:</strong> ${summary.total_ingredients_found}</p>
                    </div>
                    <div class="col-md-6">
                        <p class="mb-1"><strong>Spoonacular Success:</strong> ${Math.round(summary.spoonacular_success_rate * 100)}%</p>
                        <p class="mb-1"><strong>AI Success:</strong> ${Math.round(summary.openai_success_rate * 100)}%</p>
                    </div>
                </div>
            </div>
        `;
    }

    function createDishCard(dish) {
        const ingredients = dish.ingredients || {};
        const metadata = dish.metadata || {};
        const sources = dish.sources || {};

        let html = `
            <div class="dish-card">
                <h6><i class="fas fa-utensils me-2"></i>${dish.dish_name}</h6>
                
                <div class="mb-3">
                    <strong>All Ingredients (${ingredients.combined_list ? ingredients.combined_list.length : 0}):</strong>
                    <div class="mt-2">
        `;

        if (ingredients.combined_list && ingredients.combined_list.length > 0) {
            ingredients.combined_list.forEach(ingredient => {
                html += `<span class="ingredient-badge">${ingredient}</span>`;
            });
        } else {
            html += '<span class="text-muted">No ingredients found</span>';
        }

        html += `
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-4">
                        <strong>From Menu:</strong>
                        <div class="mt-1">
        `;

        if (ingredients.from_menu && ingredients.from_menu.length > 0) {
            ingredients.from_menu.forEach(ingredient => {
                html += `<span class="source-badge source-menu">${ingredient}</span> `;
            });
        } else {
            html += '<span class="text-muted">None</span>';
        }

        html += `
                        </div>
                    </div>
                    <div class="col-md-4">
                        <strong>From Spoonacular:</strong>
                        <div class="mt-1">
        `;

        if (ingredients.from_spoonacular && ingredients.from_spoonacular.length > 0) {
            ingredients.from_spoonacular.forEach(ingredient => {
                html += `<span class="source-badge source-spoonacular">${ingredient}</span> `;
            });
        } else {
            html += '<span class="text-muted">None</span>';
        }

        html += `
                        </div>
                    </div>
                    <div class="col-md-4">
                        <strong>AI Suggested:</strong>
                        <div class="mt-1">
        `;

        if (ingredients.suggested_by_ai && ingredients.suggested_by_ai.length > 0) {
            ingredients.suggested_by_ai.forEach(ingredient => {
                html += `<span class="source-badge source-ai">${ingredient}</span> `;
            });
        } else {
            html += '<span class="text-muted">None</span>';
        }

        html += `
                        </div>
                    </div>
                </div>
        `;

        if (metadata.ai_reasoning) {
            html += `
                <div class="mt-3">
                    <strong>AI Reasoning:</strong>
                    <p class="text-muted mb-0">${metadata.ai_reasoning}</p>
                </div>
            `;
        }

        html += `
                <div class="mt-3">
                    <small class="text-muted">
                        Confidence: Spoonacular ${Math.round((metadata.spoonacular_confidence || 0) * 100)}%, 
                        AI ${Math.round((metadata.ai_confidence || 0) * 100)}% | 
                        Recipes Found: ${metadata.recipes_found || 0}
                    </small>
                </div>
            </div>
        `;

        return html;
    }

    function createOCRAnalysis(analysis) {
        return `
            <div class="mt-4">
                <h6><i class="fas fa-eye me-2"></i>OCR Analysis</h6>
                <div class="processing-summary">
                    <p class="mb-1"><strong>Text Quality:</strong> ${analysis.text_quality}</p>
                    <p class="mb-1"><strong>Overall Confidence:</strong> ${Math.round((analysis.overall_confidence || 0) * 100)}%</p>
                    <p class="mb-0"><strong>Dishes Detected:</strong> ${analysis.dishes ? analysis.dishes.length : 0}</p>
                </div>
            </div>
        `;
    }

    function showError(message) {
        resultsContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
        resultsCard.style.display = 'block';
    }

    // Perform initial health check
    performHealthCheck();
});
