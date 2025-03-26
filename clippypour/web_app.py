import os
import json
import asyncio
import threading
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig

from .dollop import clippy_dollop_fill_form
from .form_analyzer import FormAnalyzer
from .template_manager import TemplateManager

# Load environment variables from .env file
load_dotenv()

# Global variables to store browser and agent instances
browser_instance = None
agent_instance = None
form_analyzer_instance = None
current_analysis = None
visual_selector_active = False
selected_elements = []

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure the app
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-for-clippypour")
    
    # Create a directory for templates if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), "templates"), exist_ok=True)
    
    # Create a directory for static files if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
    
    # Create a favicon.ico file if it doesn't exist
    favicon_path = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")
    if not os.path.exists(favicon_path):
        # Create a simple favicon (1x1 transparent pixel)
        with open(favicon_path, "wb") as f:
            f.write(b"\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x0A\x00\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
    
    # Initialize template manager
    template_manager = TemplateManager()
    
    @app.route("/")
    def index():
        """Render the enhanced page."""
        return render_template("enhanced.html")
    
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
        
        thread = threading.Thread(target=run_form_filling)
        thread.start()
        thread.join()  # Wait for the thread to complete
        
        return jsonify({"success": True, "message": "Form filled successfully"})
    
    @app.route("/api/analyze-form", methods=["POST"])
    def analyze_form():
        """API endpoint to analyze a form."""
        global browser_instance, agent_instance, form_analyzer_instance, current_analysis
        
        data = request.json
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        form_url = data.get("formUrl")
        
        if not form_url:
            return jsonify({"success": False, "message": "Missing form URL"}), 400
        
        # Initialize browser and agent if not already initialized
        def init_browser_and_analyze():
            global browser_instance, agent_instance, form_analyzer_instance, current_analysis
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Initialize browser if not already initialized
                if browser_instance is None:
                    browser_config = BrowserConfig(headless=False)
                    browser_instance = Browser(config=browser_config)
                    
                    # Create agent
                    task = "Analyze forms and fill them using ClippyPour."
                    llm = ChatOpenAI(model="gpt-4o")
                    agent_instance = Agent(task=task, llm=llm, browser=browser_instance)
                    
                    # Create form analyzer
                    form_analyzer_instance = FormAnalyzer(agent_instance)
                
                # Navigate to the form URL
                loop.run_until_complete(agent_instance.browser_context.navigate_to(form_url))
                
                # Wait for the page to load
                time.sleep(2)
                
                # Analyze the form
                analysis = loop.run_until_complete(form_analyzer_instance.analyze_current_page())
                
                # Store the analysis for later use
                current_analysis = analysis
                
                return True, analysis
            except Exception as e:
                return False, f"Error analyzing form: {str(e)}"
            finally:
                loop.close()
        
        thread = threading.Thread(target=init_browser_and_analyze)
        thread.start()
        thread.join()  # Wait for the thread to complete
        
        if current_analysis:
            return jsonify({"success": True, "message": "Form analyzed successfully", "analysis": current_analysis})
        else:
            return jsonify({"success": False, "message": "Failed to analyze form"})
    
    @app.route("/api/map-clipboard", methods=["POST"])
    def map_clipboard():
        """API endpoint to map clipboard data to form fields."""
        global form_analyzer_instance, current_analysis
        
        data = request.json
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        form_index = data.get("formIndex", 0)
        clipboard_data = data.get("clipboardData", "")
        
        if not clipboard_data:
            return jsonify({"success": False, "message": "Missing clipboard data"}), 400
        
        if not current_analysis or not current_analysis.get("forms") or form_index >= len(current_analysis.get("forms", [])):
            return jsonify({"success": False, "message": "No form analysis available"}), 400
        
        # Get the form data
        form_data = current_analysis["forms"][form_index]
        
        # Map clipboard data to form fields
        def run_mapping():
            global form_analyzer_instance
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                mapping = loop.run_until_complete(form_analyzer_instance.suggest_data_mapping(form_data, clipboard_data))
                return True, mapping
            except Exception as e:
                return False, f"Error mapping clipboard data: {str(e)}"
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_mapping)
        thread.start()
        thread.join()  # Wait for the thread to complete
        
        # Get the result from the thread
        success, result = thread._target()
        
        if success:
            return jsonify({"success": True, "message": "Clipboard data mapped successfully", "mapping": result})
        else:
            return jsonify({"success": False, "message": result})
    
    @app.route("/api/save-template", methods=["POST"])
    def save_template():
        """API endpoint to save a template."""
        data = request.json
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        name = data.get("name")
        form_url = data.get("formUrl")
        form_data = data.get("formData")
        selectors = data.get("selectors")
        
        if not name or not form_url or not form_data or not selectors:
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        # Create template data
        template_data = {
            "name": name,
            "formUrl": form_url,
            "formData": form_data,
            "selectors": selectors,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save the template
        try:
            template_id = template_manager.save_template(template_data, name)
            return jsonify({"success": True, "message": f"Template saved successfully with ID: {template_id}", "template_id": template_id})
        except Exception as e:
            return jsonify({"success": False, "message": f"Error saving template: {str(e)}"}), 500
    
    @app.route("/api/templates", methods=["GET"])
    def list_templates():
        """API endpoint to list all templates."""
        try:
            templates = template_manager.list_templates()
            return jsonify({"success": True, "templates": templates})
        except Exception as e:
            return jsonify({"success": False, "message": f"Error listing templates: {str(e)}"}), 500
    
    @app.route("/api/templates/<template_id>", methods=["GET"])
    def get_template(template_id):
        """API endpoint to get a template by ID."""
        try:
            template = template_manager.load_template(template_id)
            if template:
                return jsonify({"success": True, "template": template})
            else:
                return jsonify({"success": False, "message": f"Template not found: {template_id}"}), 404
        except Exception as e:
            return jsonify({"success": False, "message": f"Error loading template: {str(e)}"}), 500
    
    @app.route("/api/templates/<template_id>", methods=["DELETE"])
    def delete_template(template_id):
        """API endpoint to delete a template by ID."""
        try:
            success = template_manager.delete_template(template_id)
            if success:
                return jsonify({"success": True, "message": f"Template deleted: {template_id}"})
            else:
                return jsonify({"success": False, "message": f"Template not found: {template_id}"}), 404
        except Exception as e:
            return jsonify({"success": False, "message": f"Error deleting template: {str(e)}"}), 500
    
    @app.route("/api/activate-visual-selector", methods=["POST"])
    def activate_visual_selector():
        """API endpoint to activate the visual selector."""
        global browser_instance, agent_instance, visual_selector_active, selected_elements
        
        if browser_instance is None or agent_instance is None:
            return jsonify({"success": False, "message": "Browser not initialized. Please analyze a form first."}), 400
        
        # Reset selected elements
        selected_elements = []
        
        # Set visual selector active flag
        visual_selector_active = True
        
        # Run the visual selector in a separate thread
        def run_visual_selector():
            global browser_instance, agent_instance, visual_selector_active, selected_elements
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Get the current page
                page = loop.run_until_complete(agent_instance.browser_context.get_current_page())
                
                # Add click event listener to the page
                loop.run_until_complete(page.evaluate("""
                    () => {
                        // Remove any existing listeners
                        if (window._clippyPourClickListener) {
                            document.removeEventListener('click', window._clippyPourClickListener);
                        }
                        
                        // Add highlight style
                        const style = document.createElement('style');
                        style.textContent = `
                            .clippypour-highlight {
                                outline: 2px solid red !important;
                                background-color: rgba(255, 0, 0, 0.1) !important;
                            }
                        `;
                        document.head.appendChild(style);
                        
                        // Create a function to get a unique selector for an element
                        function getUniqueSelector(el) {
                            if (el.id) {
                                return `#${el.id}`;
                            }
                            
                            if (el.name && (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA')) {
                                return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
                            }
                            
                            // Try with classes
                            if (el.className) {
                                const classes = el.className.split(/\\s+/).filter(c => c);
                                if (classes.length > 0) {
                                    const selector = `.${classes.join('.')}`;
                                    if (document.querySelectorAll(selector).length === 1) {
                                        return selector;
                                    }
                                }
                            }
                            
                            // Fallback to a more complex selector
                            let selector = el.tagName.toLowerCase();
                            let parent = el.parentElement;
                            let nth = 1;
                            
                            // Find the element's position among siblings of the same type
                            for (let sibling = el.previousElementSibling; sibling; sibling = sibling.previousElementSibling) {
                                if (sibling.tagName === el.tagName) {
                                    nth++;
                                }
                            }
                            
                            // Add nth-of-type if there are multiple elements of the same type
                            if (parent && parent.querySelectorAll(selector).length > 1) {
                                selector += `:nth-of-type(${nth})`;
                            }
                            
                            // If parent has ID, use that for a more specific selector
                            if (parent && parent.id) {
                                return `#${parent.id} > ${selector}`;
                            }
                            
                            // Add parent tag for more specificity
                            if (parent) {
                                const parentTag = parent.tagName.toLowerCase();
                                return `${parentTag} > ${selector}`;
                            }
                            
                            return selector;
                        }
                        
                        // Create a click listener
                        window._clippyPourClickListener = function(e) {
                            // Prevent default behavior
                            e.preventDefault();
                            e.stopPropagation();
                            
                            // Get the target element
                            const target = e.target;
                            
                            // Highlight the element
                            target.classList.add('clippypour-highlight');
                            
                            // Get the selector
                            const selector = getUniqueSelector(target);
                            
                            // Send the selector to the server
                            fetch('/api/visual-selector', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    selector: selector,
                                    tagName: target.tagName.toLowerCase(),
                                    type: target.type || '',
                                    name: target.name || '',
                                    id: target.id || ''
                                })
                            });
                            
                            return false;
                        };
                        
                        // Add the click listener
                        document.addEventListener('click', window._clippyPourClickListener, true);
                        
                        // Show a message to the user
                        const message = document.createElement('div');
                        message.style.position = 'fixed';
                        message.style.top = '0';
                        message.style.left = '0';
                        message.style.right = '0';
                        message.style.padding = '10px';
                        message.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
                        message.style.color = 'white';
                        message.style.textAlign = 'center';
                        message.style.zIndex = '9999';
                        message.textContent = 'Visual Selector Mode: Click on form fields to select them. Press ESC to exit.';
                        document.body.appendChild(message);
                        
                        // Add ESC key listener to exit visual selector mode
                        document.addEventListener('keydown', function(e) {
                            if (e.key === 'Escape') {
                                // Remove the click listener
                                document.removeEventListener('click', window._clippyPourClickListener, true);
                                
                                // Remove the message
                                message.remove();
                                
                                // Remove highlights
                                document.querySelectorAll('.clippypour-highlight').forEach(el => {
                                    el.classList.remove('clippypour-highlight');
                                });
                                
                                // Send exit message to server
                                fetch('/api/visual-selector-exit', {
                                    method: 'POST'
                                });
                            }
                        });
                    }
                """))
                
                # Wait for the visual selector to be deactivated
                while visual_selector_active:
                    time.sleep(0.5)
                
                return True, "Visual selector deactivated"
            except Exception as e:
                return False, f"Error activating visual selector: {str(e)}"
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_visual_selector)
        thread.start()
        
        return jsonify({"success": True, "message": "Visual selector activated"})
    
    @app.route("/api/visual-selector", methods=["POST"])
    def visual_selector():
        """API endpoint to receive visual selector events."""
        global selected_elements
        
        data = request.json
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        selector = data.get("selector")
        
        if not selector:
            return jsonify({"success": False, "message": "Missing selector"}), 400
        
        # Add the selector to the list of selected elements
        selected_elements.append({
            "selector": selector,
            "tagName": data.get("tagName", ""),
            "type": data.get("type", ""),
            "name": data.get("name", ""),
            "id": data.get("id", "")
        })
        
        return jsonify({"success": True, "message": f"Element selected: {selector}"})
    
    @app.route("/api/visual-selector-exit", methods=["POST"])
    def visual_selector_exit():
        """API endpoint to exit visual selector mode."""
        global visual_selector_active, selected_elements
        
        # Set visual selector active flag to False
        visual_selector_active = False
        
        return jsonify({
            "success": True, 
            "message": "Visual selector deactivated",
            "selected_elements": selected_elements
        })
    
    @app.route("/api/selected-elements", methods=["GET"])
    def get_selected_elements():
        """API endpoint to get selected elements."""
        global selected_elements
        
        return jsonify({
            "success": True,
            "selected_elements": selected_elements
        })
    
    return app