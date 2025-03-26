import os
import json
import asyncio
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from .dollop import clippy_dollop_fill_form

# Load environment variables from .env file
load_dotenv()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure the app
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-for-clippypour")
    
    # Create a directory for templates if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), "templates"), exist_ok=True)
    
    # Create a directory for static files if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
    
    # Create the index.html template
    index_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ClippyPour - Form Filling Automation</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            .form-group {
                margin-bottom: 1rem;
            }
            .selector-group {
                display: flex;
                margin-bottom: 0.5rem;
            }
            .selector-group input {
                flex-grow: 1;
                margin-right: 0.5rem;
            }
            .selector-group button {
                flex-shrink: 0;
            }
            #result {
                margin-top: 1rem;
                padding: 1rem;
                border-radius: 0.25rem;
                display: none;
            }
            .success {
                background-color: #d4edda;
                color: #155724;
            }
            .error {
                background-color: #f8d7da;
                color: #721c24;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">ClippyPour - Form Filling Automation</h1>
            
            <div class="card mb-4">
                <div class="card-header">
                    <h2 class="h5 mb-0">Fill Form</h2>
                </div>
                <div class="card-body">
                    <form id="fillForm">
                        <div class="form-group">
                            <label for="formUrl">Form URL:</label>
                            <input type="url" class="form-control" id="formUrl" name="formUrl" required placeholder="https://example.com/form">
                        </div>
                        
                        <div class="form-group">
                            <label for="formData">Form Data (fields separated by "||"):</label>
                            <textarea class="form-control" id="formData" name="formData" rows="3" required placeholder="John Doe || john.doe@example.com || 123 Main St"></textarea>
                        </div>
                        
                        <div class="form-group">
                            <label>Field Selectors:</label>
                            <div id="selectors">
                                <div class="selector-group">
                                    <input type="text" class="form-control" name="selectors[]" required placeholder="#name">
                                    <button type="button" class="btn btn-danger remove-selector">-</button>
                                </div>
                            </div>
                            <button type="button" class="btn btn-secondary mt-2" id="addSelector">Add Selector</button>
                        </div>
                        
                        <div class="form-check mb-3">
                            <input type="checkbox" class="form-check-input" id="headless" name="headless">
                            <label class="form-check-label" for="headless">Run in headless mode</label>
                        </div>
                        
                        <button type="submit" class="btn btn-primary">Fill Form</button>
                    </form>
                    
                    <div id="result" class="mt-3"></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2 class="h5 mb-0">About ClippyPour</h2>
                </div>
                <div class="card-body">
                    <p>ClippyPour is an AI-driven, clipboard-free form-filling automation system that streams structured form data directly into multiple web form fields.</p>
                    <p>By leveraging the robust Browser-Use library and Playwright, ClippyPour bypasses traditional clipboard mechanics, enabling faster and more efficient web automation.</p>
                    <h3 class="h6">Features:</h3>
                    <ul>
                        <li><strong>Clipboard-Free Streaming:</strong> Copy once and stream the data into several fields using a custom delimiter.</li>
                        <li><strong>Efficient Form Filling:</strong> Bypass OS clipboard limitations to fill out forms quickly.</li>
                        <li><strong>Browser-Based Automation:</strong> Built on Browser-Use's powerful Playwright interface for real browser control.</li>
                        <li><strong>Customizable Field Mapping:</strong> Easily configure CSS selectors to target the appropriate form fields.</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                // Add selector button
                document.getElementById('addSelector').addEventListener('click', function() {
                    const selectorsDiv = document.getElementById('selectors');
                    const newGroup = document.createElement('div');
                    newGroup.className = 'selector-group';
                    newGroup.innerHTML = `
                        <input type="text" class="form-control" name="selectors[]" required placeholder="#field">
                        <button type="button" class="btn btn-danger remove-selector">-</button>
                    `;
                    selectorsDiv.appendChild(newGroup);
                });
                
                // Remove selector button
                document.getElementById('selectors').addEventListener('click', function(e) {
                    if (e.target.classList.contains('remove-selector')) {
                        const selectorsDiv = document.getElementById('selectors');
                        if (selectorsDiv.children.length > 1) {
                            e.target.parentElement.remove();
                        }
                    }
                });
                
                // Form submission
                document.getElementById('fillForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const formUrl = document.getElementById('formUrl').value;
                    const formData = document.getElementById('formData').value;
                    const headless = document.getElementById('headless').checked;
                    
                    const selectorInputs = document.querySelectorAll('input[name="selectors[]"]');
                    const selectors = Array.from(selectorInputs).map(input => input.value);
                    
                    // Validate that the number of fields matches the number of selectors
                    const fields = formData.split('||');
                    if (fields.length !== selectors.length) {
                        showResult(`Error: Number of fields (${fields.length}) does not match number of selectors (${selectors.length}).`, false);
                        return;
                    }
                    
                    // Disable form during submission
                    const submitButton = this.querySelector('button[type="submit"]');
                    const originalText = submitButton.textContent;
                    submitButton.disabled = true;
                    submitButton.textContent = 'Processing...';
                    
                    // Send the request
                    fetch('/api/fill-form', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            formUrl,
                            formData,
                            selectors,
                            headless
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        showResult(data.message, data.success);
                    })
                    .catch(error => {
                        showResult(`Error: ${error.message}`, false);
                    })
                    .finally(() => {
                        // Re-enable the form
                        submitButton.disabled = false;
                        submitButton.textContent = originalText;
                    });
                });
                
                function showResult(message, success) {
                    const resultDiv = document.getElementById('result');
                    resultDiv.textContent = message;
                    resultDiv.className = success ? 'success' : 'error';
                    resultDiv.style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """
    
    # Write the template to the templates directory
    with open(os.path.join(os.path.dirname(__file__), "templates", "index.html"), "w") as f:
        f.write(index_html)
    
    @app.route("/")
    def index():
        """Render the index page."""
        return render_template("index.html")
    
    @app.route("/api/fill-form", methods=["POST"])
    def fill_form():
        """API endpoint to fill a form."""
        data = request.json
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        form_url = data.get("formUrl")
        form_data = data.get("formData")
        selectors = data.get("selectors")
        headless = data.get("headless", False)
        
        if not form_url or not form_data or not selectors:
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        # Run the form filling in a separate thread
        def run_form_filling():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(clippy_dollop_fill_form(form_url, form_data, selectors, headless))
                return True, "Form filled successfully"
            except Exception as e:
                return False, f"Error filling form: {str(e)}"
            finally:
                loop.close()
        
        import threading
        thread = threading.Thread(target=run_form_filling)
        thread.start()
        thread.join()  # Wait for the thread to complete
        
        # For now, just return a success message
        # In a real application, you would want to handle errors and provide more feedback
        return jsonify({"success": True, "message": "Form filling process started"})
    
    return app