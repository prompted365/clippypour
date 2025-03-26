"""
Controller module for ClippyPour.

This module provides a custom Controller implementation that extends browser-use's
Controller with form-specific actions.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

from browser_use import Controller as BrowserUseController, Browser, ActionResult


class FormField(BaseModel):
    """Model representing a form field."""
    name: str = Field(..., description="The name of the form field")
    selector: str = Field(..., description="CSS selector for the form field")
    field_type: str = Field(..., description="Type of the form field (text, email, password, etc.)")
    label: Optional[str] = Field(None, description="Label text associated with the field")
    placeholder: Optional[str] = Field(None, description="Placeholder text for the field")
    required: bool = Field(False, description="Whether the field is required")
    value: Optional[str] = Field(None, description="Current value of the field")
    suggested_data_type: Optional[str] = Field(None, description="Suggested data type for this field")


class Form(BaseModel):
    """Model representing a form."""
    form_id: Optional[str] = Field(None, description="ID of the form if available")
    form_name: Optional[str] = Field(None, description="Name of the form if available")
    form_action: Optional[str] = Field(None, description="Action URL of the form if available")
    form_method: Optional[str] = Field(None, description="HTTP method of the form if available")
    form_selector: str = Field(..., description="CSS selector for the form")
    fields: List[FormField] = Field(..., description="List of fields in the form")
    purpose: Optional[str] = Field(None, description="Detected purpose of the form")
    form_type: Optional[str] = Field(None, description="Type of the form (login, registration, etc.)")


class FormTemplate(BaseModel):
    """Model representing a saved form template."""
    name: str = Field(..., description="Name of the template")
    url: str = Field(..., description="URL of the form")
    title: Optional[str] = Field(None, description="Title of the page containing the form")
    forms: List[Form] = Field(..., description="Forms detected on the page")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class ClippyPourController(BrowserUseController):
    """
    Controller for ClippyPour that extends browser-use's Controller with form-specific actions.
    """
    
    def __init__(self, template_manager=None, *args, **kwargs):
        """
        Initialize the ClippyPourController.
        
        Args:
            template_manager: The template manager instance for saving/loading templates
            *args, **kwargs: Additional arguments to pass to the parent Controller
        """
        super().__init__(*args, **kwargs)
        self.template_manager = template_manager
        self._register_form_actions()
    
    def _register_form_actions(self):
        """Register form-specific actions with the controller."""
        
        @self.action("Detect forms on the current page")
        async def detect_forms(browser: Browser) -> ActionResult:
            """
            Detect and analyze forms on the current page.
            
            Args:
                browser: The browser instance
                
            Returns:
                ActionResult: Information about detected forms
            """
            page = await browser.get_current_page()
            
            # Get page information
            url = page.url
            title = await page.title()
            
            # Execute JavaScript to detect forms
            forms_data = await page.evaluate("""
                () => {
                    const results = [];
                    const forms = document.querySelectorAll('form');
                    
                    // If no forms found, look for div containers that might act as forms
                    const formElements = forms.length > 0 ? 
                        Array.from(forms) : 
                        Array.from(document.querySelectorAll('div, section')).filter(el => 
                            el.querySelectorAll('input, textarea, select').length > 1
                        );
                    
                    formElements.forEach((form, formIndex) => {
                        const formData = {
                            formIndex,
                            id: form.id || null,
                            name: form.getAttribute('name') || null,
                            action: form instanceof HTMLFormElement ? form.action : null,
                            method: form instanceof HTMLFormElement ? form.method : null,
                            selector: getUniqueSelector(form),
                            fields: []
                        };
                        
                        // Get all input elements
                        const inputElements = form.querySelectorAll('input, textarea, select');
                        inputElements.forEach((input, inputIndex) => {
                            // Skip hidden and submit inputs for form filling purposes
                            if (input.type === 'hidden' || input.type === 'submit' || input.type === 'button') {
                                return;
                            }
                            
                            // Find associated label
                            let labelText = null;
                            const inputId = input.id;
                            if (inputId) {
                                const label = document.querySelector(`label[for="${inputId}"]`);
                                if (label) {
                                    labelText = label.textContent.trim();
                                }
                            }
                            
                            // If no label found, try to find nearby text
                            if (!labelText) {
                                // Check for preceding text node or element
                                let node = input.previousSibling;
                                while (node && !labelText) {
                                    if (node.nodeType === 3 && node.textContent.trim()) { // Text node
                                        labelText = node.textContent.trim();
                                    } else if (node.nodeType === 1 && node.textContent.trim()) { // Element node
                                        labelText = node.textContent.trim();
                                    }
                                    node = node.previousSibling;
                                }
                                
                                // If still no label, check parent's text content
                                if (!labelText && input.parentElement) {
                                    const parentText = input.parentElement.textContent.trim();
                                    const inputValue = input.value || '';
                                    if (parentText && parentText !== inputValue) {
                                        // Extract just the label part, not the input's value
                                        labelText = parentText.replace(inputValue, '').trim();
                                    }
                                }
                            }
                            
                            // Get placeholder as fallback
                            const placeholder = input.placeholder || null;
                            
                            // Determine field name from various sources
                            const fieldName = input.name || input.id || placeholder || labelText || `field_${inputIndex}`;
                            
                            formData.fields.push({
                                index: inputIndex,
                                name: fieldName,
                                type: input.type || input.tagName.toLowerCase(),
                                id: input.id || null,
                                selector: getUniqueSelector(input),
                                label: labelText,
                                placeholder: placeholder,
                                required: input.required || false,
                                value: input.value || null,
                                options: input.tagName.toLowerCase() === 'select' ? 
                                    Array.from(input.options).map(opt => ({
                                        value: opt.value,
                                        text: opt.text,
                                        selected: opt.selected
                                    })) : null
                            });
                        });
                        
                        if (formData.fields.length > 0) {
                            results.push(formData);
                        }
                    });
                    
                    return results;
                    
                    // Helper function to get a unique CSS selector for an element
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
                }
            """)
            
            # If no forms were detected, return empty result
            if not forms_data:
                return ActionResult(
                    extracted_content=json.dumps({
                        "url": url,
                        "title": title,
                        "forms": [],
                        "message": "No forms detected on the page."
                    }, indent=2)
                )
            
            # Convert the raw form data to our Form model
            forms = []
            for form_data in forms_data:
                fields = []
                for field_data in form_data.get("fields", []):
                    fields.append(FormField(
                        name=field_data.get("name", ""),
                        selector=field_data.get("selector", ""),
                        field_type=field_data.get("type", "text"),
                        label=field_data.get("label"),
                        placeholder=field_data.get("placeholder"),
                        required=field_data.get("required", False),
                        value=field_data.get("value")
                    ))
                
                forms.append(Form(
                    form_id=form_data.get("id"),
                    form_name=form_data.get("name"),
                    form_action=form_data.get("action"),
                    form_method=form_data.get("method"),
                    form_selector=form_data.get("selector", ""),
                    fields=fields
                ))
            
            result = {
                "url": url,
                "title": title,
                "forms": [form.dict() for form in forms],
                "message": f"Successfully detected {len(forms)} form(s) on the page."
            }
            
            return ActionResult(extracted_content=json.dumps(result, indent=2))
        
        @self.action("Analyze form purpose")
        async def analyze_form_purpose(form_data: str, browser: Browser) -> ActionResult:
            """
            Analyze the purpose of a form using the LLM.
            
            Args:
                form_data: JSON string containing form data
                browser: The browser instance
                
            Returns:
                ActionResult: Enhanced form data with purpose analysis
            """
            # Parse the form data
            form_dict = json.loads(form_data)
            
            # Get the LLM from the browser's agent
            llm = browser.agent.llm
            
            # Create a description of the form for the LLM
            form_description = f"""
            Form found on page: "{form_dict.get('title', '')}" (URL: {form_dict.get('url', '')})
            
            Fields:
            """
            
            for field in form_dict.get("fields", []):
                field_desc = f"""
                - Field: {field.get('name', '')}
                  Type: {field.get('type', '')}
                  Label: {field.get('label', 'None')}
                  Placeholder: {field.get('placeholder', 'None')}
                  Required: {field.get('required', False)}
                """
                form_description += field_desc
            
            # Ask the LLM to analyze the form
            llm_response = await llm.apredict(
                f"""
                Analyze this web form and provide insights:
                
                {form_description}
                
                Please provide the following information in JSON format:
                1. What is the likely purpose of this form?
                2. For each field, suggest a common data type that would be appropriate (e.g., "full name", "email address", "phone number", "street address", "date of birth", etc.)
                3. Suggest a logical order for filling out the fields.
                
                Respond with ONLY a JSON object in this format:
                {{
                    "form_purpose": "Brief description of the form's purpose",
                    "form_type": "One of: contact, login, registration, payment, subscription, search, survey, other",
                    "field_mappings": [
                        {{
                            "field_index": 0,
                            "field_name": "Original field name",
                            "suggested_data_type": "Suggested data type",
                            "fill_order": 1
                        }},
                        ...
                    ]
                }}
                """
            )
            
            # Extract the JSON from the response
            try:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', llm_response)
                if json_match:
                    llm_json = json.loads(json_match.group(1))
                else:
                    # If that fails, try to find anything that looks like JSON
                    json_match = re.search(r'({[\s\S]*})', llm_response)
                    if json_match:
                        llm_json = json.loads(json_match.group(1))
                    else:
                        # If all else fails, return an empty dict
                        llm_json = {}
            except:
                llm_json = {}
            
            # Enhance the form data with the LLM insights
            form_dict["purpose"] = llm_json.get("form_purpose", "Unknown")
            form_dict["form_type"] = llm_json.get("form_type", "other")
            
            # Enhance each field with LLM suggestions
            field_mappings = llm_json.get("field_mappings", [])
            for field in form_dict.get("fields", []):
                field_index = field.get("index")
                
                # Find the corresponding mapping from LLM
                mapping = next((m for m in field_mappings if m.get("field_index") == field_index), None)
                
                if mapping:
                    field["suggested_data_type"] = mapping.get("suggested_data_type", "Unknown")
                    field["fill_order"] = mapping.get("fill_order", field_index + 1)
                else:
                    field["suggested_data_type"] = "Unknown"
                    field["fill_order"] = field_index + 1
            
            # Sort fields by fill_order
            form_dict["fields"] = sorted(form_dict.get("fields", []), key=lambda x: x.get("fill_order", 0))
            
            return ActionResult(extracted_content=json.dumps(form_dict, indent=2))
        
        @self.action("Fill form fields")
        async def fill_form_fields(form_selector: str, field_data: str, browser: Browser) -> ActionResult:
            """
            Fill form fields with the provided data.
            
            Args:
                form_selector: CSS selector for the form
                field_data: JSON string containing field data in format [{"selector": "...", "value": "..."}]
                browser: The browser instance
                
            Returns:
                ActionResult: Result of the form filling operation
            """
            page = await browser.get_current_page()
            
            # Parse the field data
            fields = json.loads(field_data)
            
            # Check if the form exists
            form_exists = await page.evaluate(f"() => !!document.querySelector('{form_selector}')")
            if not form_exists:
                return ActionResult(
                    extracted_content=f"Error: Form with selector '{form_selector}' not found on the page."
                )
            
            # Fill each field
            filled_fields = []
            for field in fields:
                selector = field.get("selector")
                value = field.get("value")
                
                if not selector or value is None:
                    continue
                
                try:
                    # Check if the field exists
                    field_exists = await page.evaluate(f"() => !!document.querySelector('{selector}')")
                    if not field_exists:
                        filled_fields.append({
                            "selector": selector,
                            "success": False,
                            "message": "Field not found"
                        })
                        continue
                    
                    # Fill the field
                    await page.fill(selector, value)
                    await asyncio.sleep(0.5)  # Small delay between fields
                    
                    filled_fields.append({
                        "selector": selector,
                        "success": True,
                        "message": f"Filled with: {value}"
                    })
                except Exception as e:
                    filled_fields.append({
                        "selector": selector,
                        "success": False,
                        "message": f"Error: {str(e)}"
                    })
            
            result = {
                "form_selector": form_selector,
                "fields_filled": len([f for f in filled_fields if f.get("success", False)]),
                "fields_failed": len([f for f in filled_fields if not f.get("success", False)]),
                "details": filled_fields
            }
            
            return ActionResult(extracted_content=json.dumps(result, indent=2))
        
        @self.action("Save form template")
        async def save_form_template(template_name: str, form_data: str) -> ActionResult:
            """
            Save a form template for future use.
            
            Args:
                template_name: Name for the template
                form_data: JSON string containing form data
                
            Returns:
                ActionResult: Result of the save operation
            """
            if not self.template_manager:
                return ActionResult(
                    extracted_content="Error: Template manager not initialized."
                )
            
            try:
                # Parse the form data
                form_dict = json.loads(form_data)
                
                # Save the template
                template_id = self.template_manager.save_template(form_dict, template_name)
                
                return ActionResult(
                    extracted_content=f"Template '{template_name}' saved successfully with ID: {template_id}"
                )
            except Exception as e:
                return ActionResult(
                    extracted_content=f"Error saving template: {str(e)}"
                )
        
        @self.action("Load form template")
        async def load_form_template(template_id: str) -> ActionResult:
            """
            Load a form template by ID.
            
            Args:
                template_id: ID of the template to load
                
            Returns:
                ActionResult: The loaded template data
            """
            if not self.template_manager:
                return ActionResult(
                    extracted_content="Error: Template manager not initialized."
                )
            
            try:
                # Load the template
                template = self.template_manager.load_template(template_id)
                
                if not template:
                    return ActionResult(
                        extracted_content=f"Error: Template with ID '{template_id}' not found."
                    )
                
                return ActionResult(
                    extracted_content=json.dumps(template, indent=2)
                )
            except Exception as e:
                return ActionResult(
                    extracted_content=f"Error loading template: {str(e)}"
                )
        
        @self.action("Find template for URL")
        async def find_template_for_url(url: str) -> ActionResult:
            """
            Find a template that matches a given URL.
            
            Args:
                url: URL to match
                
            Returns:
                ActionResult: The matching template data or error message
            """
            if not self.template_manager:
                return ActionResult(
                    extracted_content="Error: Template manager not initialized."
                )
            
            try:
                # Find a matching template
                template = self.template_manager.find_template_for_url(url)
                
                if not template:
                    return ActionResult(
                        extracted_content=f"No template found for URL: {url}"
                    )
                
                return ActionResult(
                    extracted_content=json.dumps(template, indent=2)
                )
            except Exception as e:
                return ActionResult(
                    extracted_content=f"Error finding template: {str(e)}"
                )
        
        @self.action("Map clipboard data to form fields")
        async def map_clipboard_data(clipboard_data: str, form_data: str, browser: Browser) -> ActionResult:
            """
            Map clipboard data to form fields.
            
            Args:
                clipboard_data: Data from clipboard, possibly with delimiters
                form_data: JSON string containing form data
                browser: The browser instance
                
            Returns:
                ActionResult: Suggested mapping between clipboard fields and form fields
            """
            # Parse the form data
            form_dict = json.loads(form_data)
            
            # Split clipboard data if it contains delimiters
            clipboard_fields = []
            if "||" in clipboard_data:
                clipboard_fields = [field.strip() for field in clipboard_data.split("||")]
            else:
                # Try to intelligently split the clipboard data
                clipboard_fields = [clipboard_data.strip()]
            
            # Get the LLM from the browser's agent
            llm = browser.agent.llm
            
            # If we have only one clipboard field but multiple form fields,
            # ask the LLM to suggest how to split it
            if len(clipboard_fields) == 1 and len(form_dict.get("fields", [])) > 1:
                llm_response = await llm.apredict(
                    f"""
                    I have a single piece of text data and a form with multiple fields.
                    
                    Text data: "{clipboard_fields[0]}"
                    
                    Form fields:
                    {json.dumps([{
                        "name": field.get("name"),
                        "type": field.get("type"),
                        "label": field.get("label"),
                        "suggested_data_type": field.get("suggested_data_type")
                    } for field in form_dict.get("fields", [])], indent=2)}
                    
                    Please suggest how to split this single text into appropriate parts for each form field.
                    Respond with ONLY a JSON array of strings, where each string is a part of the original text
                    that should be mapped to the corresponding form field in the same order.
                    
                    For example: ["John", "Doe", "john.doe@example.com"]
                    """
                )
                
                try:
                    # Extract the JSON from the response
                    import re
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', llm_response)
                    if json_match:
                        suggested_split = json.loads(json_match.group(1))
                    else:
                        # If that fails, try to find anything that looks like JSON
                        json_match = re.search(r'(\[[\s\S]*\])', llm_response)
                        if json_match:
                            suggested_split = json.loads(json_match.group(1))
                        else:
                            suggested_split = []
                    
                    if isinstance(suggested_split, list) and suggested_split:
                        clipboard_fields = suggested_split
                except:
                    # If splitting fails, keep the original single field
                    pass
            
            # Create mapping suggestions
            form_fields = form_dict.get("fields", [])
            mapping = {
                "form_url": form_dict.get("url", ""),
                "form_title": form_dict.get("title", ""),
                "form_purpose": form_dict.get("purpose", "Unknown"),
                "clipboard_fields": clipboard_fields,
                "field_mapping": []
            }
            
            # If we have exactly the same number of clipboard fields as form fields,
            # suggest a direct mapping
            if len(clipboard_fields) == len(form_fields):
                for i, (field, clipboard_value) in enumerate(zip(form_fields, clipboard_fields)):
                    mapping["field_mapping"].append({
                        "form_field_index": field.get("index", i),
                        "form_field_name": field.get("name", ""),
                        "form_field_selector": field.get("selector", ""),
                        "clipboard_field_index": i,
                        "clipboard_value": clipboard_value,
                        "confidence": 0.9  # High confidence for direct mapping
                    })
            else:
                # Otherwise, use the LLM to suggest the best mapping
                llm_response = await llm.apredict(
                    f"""
                    I need to map clipboard data to form fields.
                    
                    Clipboard data (split into fields):
                    {json.dumps(clipboard_fields, indent=2)}
                    
                    Form fields:
                    {json.dumps([{
                        "index": field.get("index", i),
                        "name": field.get("name", ""),
                        "type": field.get("type", ""),
                        "label": field.get("label", ""),
                        "suggested_data_type": field.get("suggested_data_type", "")
                    } for i, field in enumerate(form_fields)], indent=2)}
                    
                    Please suggest the best mapping between clipboard fields and form fields.
                    Respond with ONLY a JSON array in this format:
                    [
                        {{
                            "form_field_index": 0,
                            "clipboard_field_index": 2,
                            "confidence": 0.8
                        }},
                        ...
                    ]
                    
                    The confidence should be between 0 and 1, indicating how confident you are in the mapping.
                    You don't need to map every field if there's no good match.
                    """
                )
                
                try:
                    # Extract the JSON from the response
                    import re
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', llm_response)
                    if json_match:
                        suggested_mapping = json.loads(json_match.group(1))
                    else:
                        # If that fails, try to find anything that looks like JSON
                        json_match = re.search(r'(\[[\s\S]*\])', llm_response)
                        if json_match:
                            suggested_mapping = json.loads(json_match.group(1))
                        else:
                            suggested_mapping = []
                    
                    if isinstance(suggested_mapping, list):
                        for item in suggested_mapping:
                            form_field_index = item.get("form_field_index")
                            clipboard_field_index = item.get("clipboard_field_index")
                            
                            # Validate indices
                            if (form_field_index is not None and 
                                clipboard_field_index is not None and
                                0 <= form_field_index < len(form_fields) and
                                0 <= clipboard_field_index < len(clipboard_fields)):
                                
                                field = form_fields[form_field_index]
                                clipboard_value = clipboard_fields[clipboard_field_index]
                                
                                mapping["field_mapping"].append({
                                    "form_field_index": field.get("index", form_field_index),
                                    "form_field_name": field.get("name", ""),
                                    "form_field_selector": field.get("selector", ""),
                                    "clipboard_field_index": clipboard_field_index,
                                    "clipboard_value": clipboard_value,
                                    "confidence": item.get("confidence", 0.5)
                                })
                except:
                    # If mapping fails, create a simple mapping based on order
                    max_fields = min(len(clipboard_fields), len(form_fields))
                    for i in range(max_fields):
                        field = form_fields[i]
                        clipboard_value = clipboard_fields[i]
                        
                        mapping["field_mapping"].append({
                            "form_field_index": field.get("index", i),
                            "form_field_name": field.get("name", ""),
                            "form_field_selector": field.get("selector", ""),
                            "clipboard_field_index": i,
                            "clipboard_value": clipboard_value,
                            "confidence": 0.5  # Medium confidence for order-based mapping
                        })
            
            return ActionResult(extracted_content=json.dumps(mapping, indent=2))
        
        @self.action("Submit form")
        async def submit_form(form_selector: str, browser: Browser) -> ActionResult:
            """
            Submit a form.
            
            Args:
                form_selector: CSS selector for the form
                browser: The browser instance
                
            Returns:
                ActionResult: Result of the form submission
            """
            page = await browser.get_current_page()
            
            # Check if the form exists
            form_exists = await page.evaluate(f"() => !!document.querySelector('{form_selector}')")
            if not form_exists:
                return ActionResult(
                    extracted_content=f"Error: Form with selector '{form_selector}' not found on the page."
                )
            
            # Get the form's submit button
            submit_button = await page.evaluate(f"""
                () => {{
                    const form = document.querySelector('{form_selector}');
                    
                    // Try to find a submit button within the form
                    let submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
                    
                    // If no submit button found, look for buttons that might be submit buttons
                    if (!submitButton) {{
                        const buttons = Array.from(form.querySelectorAll('button'));
                        submitButton = buttons.find(button => 
                            button.textContent.toLowerCase().includes('submit') || 
                            button.textContent.toLowerCase().includes('send') ||
                            button.textContent.toLowerCase().includes('login') ||
                            button.textContent.toLowerCase().includes('sign in') ||
                            button.textContent.toLowerCase().includes('register') ||
                            button.textContent.toLowerCase().includes('sign up') ||
                            button.textContent.toLowerCase().includes('continue')
                        );
                    }}
                    
                    if (submitButton) {{
                        return {{
                            found: true,
                            selector: getUniqueSelector(submitButton)
                        }};
                    }}
                    
                    return {{
                        found: false
                    }};
                    
                    // Helper function to get a unique CSS selector for an element
                    function getUniqueSelector(el) {{
                        if (el.id) {{
                            return `#${{el.id}}`;
                        }}
                        
                        if (el.name && (el.tagName === 'INPUT' || el.tagName === 'BUTTON')) {{
                            return `${{el.tagName.toLowerCase()}}[name="${{el.name}}"]`;
                        }}
                        
                        // Try with classes
                        if (el.className) {{
                            const classes = el.className.split(/\\s+/).filter(c => c);
                            if (classes.length > 0) {{
                                const selector = `.${{classes.join('.')}}`;
                                if (document.querySelectorAll(selector).length === 1) {{
                                    return selector;
                                }}
                            }}
                        }}
                        
                        // Fallback to a more complex selector
                        let selector = el.tagName.toLowerCase();
                        let parent = el.parentElement;
                        let nth = 1;
                        
                        // Find the element's position among siblings of the same type
                        for (let sibling = el.previousElementSibling; sibling; sibling = sibling.previousElementSibling) {{
                            if (sibling.tagName === el.tagName) {{
                                nth++;
                            }}
                        }}
                        
                        // Add nth-of-type if there are multiple elements of the same type
                        if (parent && parent.querySelectorAll(selector).length > 1) {{
                            selector += `:nth-of-type(${{nth}})`;
                        }}
                        
                        // If parent has ID, use that for a more specific selector
                        if (parent && parent.id) {{
                            return `#${{parent.id}} > ${{selector}}`;
                        }}
                        
                        // Add parent tag for more specificity
                        if (parent) {{
                            const parentTag = parent.tagName.toLowerCase();
                            return `${{parentTag}} > ${{selector}}`;
                        }}
                        
                        return selector;
                    }}
                }}
            """)
            
            try:
                if submit_button.get("found", False):
                    # Click the submit button
                    submit_selector = submit_button.get("selector")
                    await page.click(submit_selector)
                    
                    # Wait for navigation or a short delay
                    try:
                        await page.wait_for_navigation(timeout=5000)
                    except:
                        # If navigation doesn't happen, that's okay
                        await asyncio.sleep(2)
                    
                    return ActionResult(
                        extracted_content=f"Form submitted successfully by clicking {submit_selector}."
                    )
                else:
                    # If no submit button found, try to submit the form directly
                    await page.evaluate(f"""
                        () => {{
                            const form = document.querySelector('{form_selector}');
                            form.submit();
                        }}
                    """)
                    
                    # Wait for navigation or a short delay
                    try:
                        await page.wait_for_navigation(timeout=5000)
                    except:
                        # If navigation doesn't happen, that's okay
                        await asyncio.sleep(2)
                    
                    return ActionResult(
                        extracted_content=f"Form submitted programmatically using form.submit()."
                    )
            except Exception as e:
                return ActionResult(
                    extracted_content=f"Error submitting form: {str(e)}"
                )
        
        @self.action("Activate visual selector")
        async def activate_visual_selector(browser: Browser) -> ActionResult:
            """
            Activate the visual selector mode to allow clicking on form fields.
            
            Args:
                browser: The browser instance
                
            Returns:
                ActionResult: Result of the activation
            """
            page = await browser.get_current_page()
            
            # Add click event listener to the page
            await page.evaluate("""
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
                        
                        // Store the selector in a global variable
                        if (!window._clippyPourSelectedElements) {
                            window._clippyPourSelectedElements = [];
                        }
                        
                        window._clippyPourSelectedElements.push({
                            selector: selector,
                            tagName: target.tagName.toLowerCase(),
                            type: target.type || '',
                            name: target.name || '',
                            id: target.id || ''
                        });
                        
                        // Show a message
                        const message = document.createElement('div');
                        message.style.position = 'fixed';
                        message.style.bottom = '20px';
                        message.style.left = '20px';
                        message.style.padding = '10px';
                        message.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
                        message.style.color = 'white';
                        message.style.borderRadius = '5px';
                        message.style.zIndex = '9999';
                        message.textContent = `Selected: ${selector}`;
                        document.body.appendChild(message);
                        
                        // Remove the message after 3 seconds
                        setTimeout(() => {
                            message.remove();
                        }, 3000);
                        
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
                            
                            // Show a completion message
                            const completionMessage = document.createElement('div');
                            completionMessage.style.position = 'fixed';
                            completionMessage.style.top = '20px';
                            completionMessage.style.left = '20px';
                            completionMessage.style.padding = '10px';
                            completionMessage.style.backgroundColor = 'rgba(0, 128, 0, 0.8)';
                            completionMessage.style.color = 'white';
                            completionMessage.style.borderRadius = '5px';
                            completionMessage.style.zIndex = '9999';
                            completionMessage.textContent = 'Visual selection completed.';
                            document.body.appendChild(completionMessage);
                            
                            // Remove the completion message after 3 seconds
                            setTimeout(() => {
                                completionMessage.remove();
                            }, 3000);
                        }
                    });
                }
            """)
            
            return ActionResult(
                extracted_content="Visual selector activated. Click on form fields in the browser. Press ESC when done."
            )
        
        @self.action("Get selected elements")
        async def get_selected_elements(browser: Browser) -> ActionResult:
            """
            Get the elements selected using the visual selector.
            
            Args:
                browser: The browser instance
                
            Returns:
                ActionResult: The selected elements
            """
            page = await browser.get_current_page()
            
            # Get the selected elements
            selected_elements = await page.evaluate("""
                () => {
                    return window._clippyPourSelectedElements || [];
                }
            """)
            
            return ActionResult(extracted_content=json.dumps(selected_elements, indent=2))