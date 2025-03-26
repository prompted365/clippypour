import asyncio
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig

from .controller import ClippyPourController
from .template_manager import TemplateManager

# Load environment variables from .env file
load_dotenv()

async def clippy_dollop_fill_form(form_url: str, form_data: str, field_selectors: list[str], headless: bool = False) -> None:
    """
    Fill out a web form by streaming the provided form data into its fields.
    
    Args:
        form_url (str): URL of the form page.
        form_data (str): Clipboard text containing all form fields separated by the delimiter "||".
        field_selectors (list[str]): List of CSS selectors for each form field (in order).
        headless (bool): Whether to run the browser in headless mode.
    """
    # Initialize the template manager
    template_manager = TemplateManager()
    
    # Initialize the controller with the template manager
    controller = ClippyPourController(template_manager=template_manager)
    
    # Initialize a browser instance using Browser-use's Browser with a custom configuration.
    browser_config = BrowserConfig(headless=headless)
    browser = Browser(config=browser_config)
    
    # Create an Agent instance with a task description and our custom controller.
    task = "Fill out the form with the provided data using clippy-dollop method."
    llm = ChatOpenAI(model="gpt-4o")
    agent = Agent(task=task, llm=llm, browser=browser, controller=controller)
    
    try:
        # Navigate to the form URL.
        await agent.browser_context.navigate_to(form_url)
        await asyncio.sleep(2)  # Allow time for the page to load completely.
        
        # Split the form data using the delimiter "||"
        fields = form_data.split("||")
        if len(fields) != len(field_selectors):
            print("Error: Number of fields does not match number of selectors.")
            return
        
        # Detect forms on the page
        print("Analyzing the form structure...")
        detect_forms_result = await agent.run_action("Detect forms on the current page")
        forms_data = json.loads(detect_forms_result.extracted_content)
        
        if not forms_data.get("forms"):
            print("No forms detected on the page.")
            return
        
        # Find the form that contains our selectors
        target_form = None
        for form in forms_data.get("forms", []):
            # Check if any of our selectors match fields in this form
            form_selectors = [field.get("selector", "") for field in form.get("fields", [])]
            if any(selector in form_selectors for selector in field_selectors):
                target_form = form
                break
        
        if not target_form:
            # If no exact match, just use the first form
            target_form = forms_data.get("forms", [])[0]
        
        # Prepare field data for filling
        field_data = []
        for i, selector in enumerate(field_selectors):
            text = fields[i].strip()
            field_data.append({
                "selector": selector,
                "value": text
            })
        
        # Fill the form fields
        print("Filling form fields...")
        form_selector = target_form.get("form_selector", "form")
        fill_result = await agent.run_action(
            "Fill form fields",
            form_selector=form_selector,
            field_data=json.dumps(field_data)
        )
        
        fill_data = json.loads(fill_result.extracted_content)
        print(f"Filled {fill_data.get('fields_filled', 0)} fields successfully.")
        
        # Submit the form
        print("Submitting the form...")
        submit_result = await agent.run_action(
            "Submit form",
            form_selector=form_selector
        )
        
        print(submit_result.extracted_content)
        print("Form filling complete.")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the browser
        await browser.close()

async def analyze_form(form_url: str, headless: bool = False) -> Dict[str, Any]:
    """
    Analyze a form on a webpage to detect fields and suggest mappings.
    
    Args:
        form_url (str): URL of the form page.
        headless (bool): Whether to run the browser in headless mode.
        
    Returns:
        Dict[str, Any]: Information about detected forms and fields.
    """
    # Initialize the template manager
    template_manager = TemplateManager()
    
    # Initialize the controller with the template manager
    controller = ClippyPourController(template_manager=template_manager)
    
    # Initialize a browser instance using Browser-use's Browser with a custom configuration.
    browser_config = BrowserConfig(headless=headless)
    browser = Browser(config=browser_config)
    
    # Create an Agent instance with a task description and our custom controller.
    task = "Analyze the form structure and detect fields."
    llm = ChatOpenAI(model="gpt-4o")
    agent = Agent(task=task, llm=llm, browser=browser, controller=controller)
    
    try:
        # Navigate to the form URL.
        await agent.browser_context.navigate_to(form_url)
        await asyncio.sleep(2)  # Allow time for the page to load completely.
        
        # Detect forms on the page
        print("Analyzing the form structure...")
        detect_forms_result = await agent.run_action("Detect forms on the current page")
        forms_data = json.loads(detect_forms_result.extracted_content)
        
        if not forms_data.get("forms"):
            print("No forms detected on the page.")
            return forms_data
        
        # Analyze the purpose of each form
        enhanced_forms = []
        for form in forms_data.get("forms", []):
            print(f"Analyzing form purpose...")
            analyze_result = await agent.run_action(
                "Analyze form purpose",
                form_data=json.dumps(form)
            )
            enhanced_form = json.loads(analyze_result.extracted_content)
            enhanced_forms.append(enhanced_form)
        
        # Update the forms in the result
        forms_data["forms"] = enhanced_forms
        
        return forms_data
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}
    finally:
        # Close the browser
        await browser.close()

async def map_clipboard_to_form(form_data: Dict[str, Any], clipboard_data: str, headless: bool = False) -> Dict[str, Any]:
    """
    Map clipboard data to form fields.
    
    Args:
        form_data (Dict[str, Any]): Form data from analyze_form.
        clipboard_data (str): Data from clipboard, possibly with delimiters.
        headless (bool): Whether to run the browser in headless mode.
        
    Returns:
        Dict[str, Any]: Suggested mapping between clipboard fields and form fields.
    """
    # Initialize the template manager
    template_manager = TemplateManager()
    
    # Initialize the controller with the template manager
    controller = ClippyPourController(template_manager=template_manager)
    
    # Initialize a browser instance using Browser-use's Browser with a custom configuration.
    browser_config = BrowserConfig(headless=headless)
    browser = Browser(config=browser_config)
    
    # Create an Agent instance with a task description and our custom controller.
    task = "Map clipboard data to form fields."
    llm = ChatOpenAI(model="gpt-4o")
    agent = Agent(task=task, llm=llm, browser=browser, controller=controller)
    
    try:
        # Map clipboard data to form fields
        print("Mapping clipboard data to form fields...")
        mapping_result = await agent.run_action(
            "Map clipboard data to form fields",
            clipboard_data=clipboard_data,
            form_data=json.dumps(form_data)
        )
        
        mapping_data = json.loads(mapping_result.extracted_content)
        return mapping_data
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}
    finally:
        # Close the browser
        await browser.close()

async def save_form_template(template_name: str, form_data: Dict[str, Any]) -> str:
    """
    Save a form template for future use.
    
    Args:
        template_name (str): Name for the template.
        form_data (Dict[str, Any]): Form data from analyze_form.
        
    Returns:
        str: Template ID.
    """
    # Initialize the template manager
    template_manager = TemplateManager()
    
    # Save the template
    template_id = template_manager.save_template(form_data, template_name)
    return template_id

def list_templates() -> List[Dict[str, Any]]:
    """
    List all available templates.
    
    Returns:
        List[Dict[str, Any]]: List of template metadata.
    """
    # Initialize the template manager
    template_manager = TemplateManager()
    
    # List templates
    return template_manager.list_templates()

def load_template(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a form template by ID.
    
    Args:
        template_id (str): ID of the template to load.
        
    Returns:
        Optional[Dict[str, Any]]: The loaded template data.
    """
    # Initialize the template manager
    template_manager = TemplateManager()
    
    # Load the template
    return template_manager.load_template(template_id)

def delete_template(template_id: str) -> bool:
    """
    Delete a form template by ID.
    
    Args:
        template_id (str): ID of the template to delete.
        
    Returns:
        bool: True if deleted, False if not found.
    """
    # Initialize the template manager
    template_manager = TemplateManager()
    
    # Delete the template
    return template_manager.delete_template(template_id)

def find_template_for_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Find a template that matches a given URL.
    
    Args:
        url (str): URL to match.
        
    Returns:
        Optional[Dict[str, Any]]: Matching template, or None if not found.
    """
    # Initialize the template manager
    template_manager = TemplateManager()
    
    # Find a matching template
    return template_manager.find_template_for_url(url)

if __name__ == "__main__":
    # Example usage:
    # Replace with the actual form URL.
    form_url = "https://example.com/form"
    # Example clipboard data with fields separated by "||"
    form_data = "John Doe || john.doe@example.com || 123 Main St || (555) 123-4567"
    # CSS selectors for each corresponding form field.
    field_selectors = [
        "#name",       # Selector for the name field
        "#email",      # Selector for the email field
        "#address",    # Selector for the address field
        "#phone"       # Selector for the phone field
    ]
    asyncio.run(clippy_dollop_fill_form(form_url, form_data, field_selectors))