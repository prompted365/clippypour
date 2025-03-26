"""
Form Analyzer module for ClippyPour.

This module provides intelligent form field detection and analysis capabilities.
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple, Any
from browser_use import Agent

class FormAnalyzer:
    """
    Analyzes web forms to automatically detect fields and suggest mappings.
    Uses AI to understand form structure and purpose.
    """
    
    def __init__(self, agent: Agent):
        """
        Initialize the FormAnalyzer.
        
        Args:
            agent (Agent): The browser-use Agent instance with LLM capabilities.
        """
        self.agent = agent
    
    async def analyze_current_page(self) -> Dict[str, Any]:
        """
        Analyze the current page to detect forms and form fields.
        
        Returns:
            Dict[str, Any]: Information about detected forms and fields.
        """
        page = await self.agent.browser_context.get_current_page()
        
        # Get the page URL
        url = page.url
        
        # Get the page title
        title = await page.title()
        
        # Extract all form elements and their fields
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
            return {
                "url": url,
                "title": title,
                "forms": [],
                "message": "No forms detected on the page."
            }
        
        # Use the LLM to analyze the form purpose and suggest field mappings
        enhanced_forms = await self._enhance_form_data_with_llm(forms_data, url, title)
        
        return {
            "url": url,
            "title": title,
            "forms": enhanced_forms,
            "message": f"Successfully detected {len(enhanced_forms)} form(s) on the page."
        }
    
    async def _enhance_form_data_with_llm(self, forms_data: List[Dict], url: str, title: str) -> List[Dict]:
        """
        Use the LLM to enhance form data with purpose detection and field mapping suggestions.
        
        Args:
            forms_data (List[Dict]): Raw form data from page evaluation.
            url (str): The page URL.
            title (str): The page title.
            
        Returns:
            List[Dict]: Enhanced form data with AI insights.
        """
        enhanced_forms = []
        
        for form_data in forms_data:
            # Skip forms with no fields
            if not form_data["fields"]:
                continue
            
            # Create a description of the form for the LLM
            form_description = f"""
            Form found on page: "{title}" (URL: {url})
            Form ID: {form_data.get('id') or 'None'}
            Form Name: {form_data.get('name') or 'None'}
            Form Action: {form_data.get('action') or 'None'}
            Form Method: {form_data.get('method') or 'None'}
            
            Fields:
            """
            
            for field in form_data["fields"]:
                field_desc = f"""
                - Field: {field.get('name')}
                  Type: {field.get('type')}
                  Label: {field.get('label') or 'None'}
                  Placeholder: {field.get('placeholder') or 'None'}
                  Required: {field.get('required')}
                """
                form_description += field_desc
            
            # Ask the LLM to analyze the form
            llm_response = await self.agent.llm.apredict(
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
            
            try:
                # Extract the JSON from the response
                llm_json = self._extract_json_from_llm_response(llm_response)
                
                # Merge the LLM insights with the original form data
                enhanced_form = form_data.copy()
                enhanced_form["purpose"] = llm_json.get("form_purpose", "Unknown")
                enhanced_form["form_type"] = llm_json.get("form_type", "other")
                
                # Enhance each field with LLM suggestions
                field_mappings = llm_json.get("field_mappings", [])
                for field in enhanced_form["fields"]:
                    field_index = field["index"]
                    
                    # Find the corresponding mapping from LLM
                    mapping = next((m for m in field_mappings if m.get("field_index") == field_index), None)
                    
                    if mapping:
                        field["suggested_data_type"] = mapping.get("suggested_data_type", "Unknown")
                        field["fill_order"] = mapping.get("fill_order", field_index + 1)
                    else:
                        field["suggested_data_type"] = "Unknown"
                        field["fill_order"] = field_index + 1
                
                # Sort fields by fill_order
                enhanced_form["fields"] = sorted(enhanced_form["fields"], key=lambda x: x["fill_order"])
                
                enhanced_forms.append(enhanced_form)
                
            except Exception as e:
                # If LLM analysis fails, just add the original form data
                form_data["purpose"] = "Unknown (LLM analysis failed)"
                form_data["form_type"] = "other"
                for field in form_data["fields"]:
                    field["suggested_data_type"] = "Unknown"
                    field["fill_order"] = field["index"] + 1
                
                enhanced_forms.append(form_data)
        
        return enhanced_forms
    
    def _extract_json_from_llm_response(self, response: str) -> Dict:
        """
        Extract JSON from LLM response, handling various formats.
        
        Args:
            response (str): The raw LLM response.
            
        Returns:
            Dict: Extracted JSON data.
        """
        # Try to find JSON in the response
        try:
            # First, try to parse the entire response as JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # If that fails, try to find anything that looks like JSON
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # If all else fails, return an empty dict
            return {}
    
    async def suggest_data_mapping(self, form_data: Dict, clipboard_data: str) -> Dict:
        """
        Suggest mapping between clipboard data and form fields.
        
        Args:
            form_data (Dict): Form data from analyze_current_page.
            clipboard_data (str): Data from clipboard, possibly with delimiters.
            
        Returns:
            Dict: Suggested mapping between clipboard fields and form fields.
        """
        # Split clipboard data if it contains delimiters
        clipboard_fields = []
        if "||" in clipboard_data:
            clipboard_fields = [field.strip() for field in clipboard_data.split("||")]
        else:
            # Try to intelligently split the clipboard data
            clipboard_fields = [clipboard_data.strip()]
        
        # If we have only one clipboard field but multiple form fields,
        # ask the LLM to suggest how to split it
        if len(clipboard_fields) == 1 and len(form_data["fields"]) > 1:
            llm_response = await self.agent.llm.apredict(
                f"""
                I have a single piece of text data and a form with multiple fields.
                
                Text data: "{clipboard_fields[0]}"
                
                Form fields:
                {json.dumps([{
                    "name": field.get("name"),
                    "type": field.get("type"),
                    "label": field.get("label"),
                    "suggested_data_type": field.get("suggested_data_type")
                } for field in form_data["fields"]], indent=2)}
                
                Please suggest how to split this single text into appropriate parts for each form field.
                Respond with ONLY a JSON array of strings, where each string is a part of the original text
                that should be mapped to the corresponding form field in the same order.
                
                For example: ["John", "Doe", "john.doe@example.com"]
                """
            )
            
            try:
                # Extract the JSON from the response
                suggested_split = self._extract_json_from_llm_response(llm_response)
                if isinstance(suggested_split, list) and suggested_split:
                    clipboard_fields = suggested_split
            except:
                # If splitting fails, keep the original single field
                pass
        
        # Create mapping suggestions
        form_fields = form_data["fields"]
        mapping = {
            "form_url": form_data.get("url", ""),
            "form_title": form_data.get("title", ""),
            "form_purpose": form_data.get("purpose", "Unknown"),
            "clipboard_fields": clipboard_fields,
            "field_mapping": []
        }
        
        # If we have exactly the same number of clipboard fields as form fields,
        # suggest a direct mapping
        if len(clipboard_fields) == len(form_fields):
            for i, (field, clipboard_value) in enumerate(zip(form_fields, clipboard_fields)):
                mapping["field_mapping"].append({
                    "form_field_index": field["index"],
                    "form_field_name": field.get("name", ""),
                    "form_field_selector": field["selector"],
                    "clipboard_field_index": i,
                    "clipboard_value": clipboard_value,
                    "confidence": 0.9  # High confidence for direct mapping
                })
        else:
            # Otherwise, use the LLM to suggest the best mapping
            llm_response = await self.agent.llm.apredict(
                f"""
                I need to map clipboard data to form fields.
                
                Clipboard data (split into fields):
                {json.dumps(clipboard_fields, indent=2)}
                
                Form fields:
                {json.dumps([{
                    "index": field["index"],
                    "name": field.get("name", ""),
                    "type": field.get("type", ""),
                    "label": field.get("label", ""),
                    "suggested_data_type": field.get("suggested_data_type", "")
                } for field in form_fields], indent=2)}
                
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
                suggested_mapping = self._extract_json_from_llm_response(llm_response)
                
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
                                "form_field_index": field["index"],
                                "form_field_name": field.get("name", ""),
                                "form_field_selector": field["selector"],
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
                        "form_field_index": field["index"],
                        "form_field_name": field.get("name", ""),
                        "form_field_selector": field["selector"],
                        "clipboard_field_index": i,
                        "clipboard_value": clipboard_value,
                        "confidence": 0.5  # Medium confidence for order-based mapping
                    })
        
        return mapping