"""
Form Analyzer module for ClippyPour.

This module provides intelligent form field detection and analysis capabilities.
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple, Any
from browser_use import Agent

from .controller import ClippyPourController

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
        # Use the controller's detect_forms action
        detect_forms_result = await self.agent.run_action("Detect forms on the current page")
        forms_data = json.loads(detect_forms_result.extracted_content)
        
        # If no forms were detected, return the empty result
        if not forms_data.get("forms"):
            return forms_data
        
        # Analyze the purpose of each form
        enhanced_forms = []
        for form in forms_data.get("forms", []):
            # Use the controller's analyze_form_purpose action
            analyze_result = await self.agent.run_action(
                "Analyze form purpose",
                form_data=json.dumps(form)
            )
            enhanced_form = json.loads(analyze_result.extracted_content)
            enhanced_forms.append(enhanced_form)
        
        # Update the forms in the result
        forms_data["forms"] = enhanced_forms
        
        return forms_data
    
    async def map_clipboard_data(self, clipboard_data: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map clipboard data to form fields.
        
        Args:
            clipboard_data (str): Data from clipboard, possibly with delimiters.
            form_data (Dict[str, Any]): Form data from analyze_current_page.
            
        Returns:
            Dict[str, Any]: Suggested mapping between clipboard fields and form fields.
        """
        # Use the controller's map_clipboard_data_to_form_fields action
        mapping_result = await self.agent.run_action(
            "Map clipboard data to form fields",
            clipboard_data=clipboard_data,
            form_data=json.dumps(form_data)
        )
        
        mapping_data = json.loads(mapping_result.extracted_content)
        return mapping_data
    
    async def fill_form(self, form_selector: str, field_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fill a form with the provided field mappings.
        
        Args:
            form_selector (str): CSS selector for the form.
            field_mappings (List[Dict[str, Any]]): List of field mappings from map_clipboard_data.
            
        Returns:
            Dict[str, Any]: Result of the form filling operation.
        """
        # Prepare field data for filling
        field_data = []
        for mapping in field_mappings:
            field_data.append({
                "selector": mapping.get("form_field_selector", ""),
                "value": mapping.get("clipboard_value", "")
            })
        
        # Use the controller's fill_form_fields action
        fill_result = await self.agent.run_action(
            "Fill form fields",
            form_selector=form_selector,
            field_data=json.dumps(field_data)
        )
        
        fill_data = json.loads(fill_result.extracted_content)
        return fill_data
    
    async def submit_form(self, form_selector: str) -> str:
        """
        Submit a form.
        
        Args:
            form_selector (str): CSS selector for the form.
            
        Returns:
            str: Result of the form submission.
        """
        # Use the controller's submit_form action
        submit_result = await self.agent.run_action(
            "Submit form",
            form_selector=form_selector
        )
        
        return submit_result.extracted_content
    
    async def activate_visual_selector(self) -> str:
        """
        Activate the visual selector mode to allow clicking on form fields.
        
        Returns:
            str: Result of the activation.
        """
        # Use the controller's activate_visual_selector action
        activate_result = await self.agent.run_action("Activate visual selector")
        return activate_result.extracted_content
    
    async def get_selected_elements(self) -> List[Dict[str, Any]]:
        """
        Get the elements selected using the visual selector.
        
        Returns:
            List[Dict[str, Any]]: The selected elements.
        """
        # Use the controller's get_selected_elements action
        selected_result = await self.agent.run_action("Get selected elements")
        selected_elements = json.loads(selected_result.extracted_content)
        return selected_elements