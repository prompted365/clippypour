import os
import json
from typing import Dict, Optional
from browser_use import Agent

class ComputerVisionHelper:
    """
    Helper class for computer vision operations.
    """
    def __init__(self, agent: Agent):
        """
        Initialize the ComputerVisionHelper.
        
        Args:
            agent (Agent): The browser-use Agent instance.
        """
        self.agent = agent
    
    async def take_screenshot(self) -> bytes:
        """
        Take a screenshot of the current page.
        
        Returns:
            bytes: The screenshot image data.
        """
        page = await self.agent.browser_context.get_current_page()
        screenshot_path = "temp_screenshot.png"
        await page.screenshot(path=screenshot_path)
        
        with open(screenshot_path, "rb") as f:
            screenshot_data = f.read()
        
        # Clean up the temporary file
        os.remove(screenshot_path)
        
        return screenshot_data
    
    async def find_element_by_vision(self, element_description: str) -> Optional[Dict]:
        """
        Find an element on the page using computer vision.
        
        Args:
            element_description (str): Description of the element to find.
            
        Returns:
            Optional[Dict]: Information about the found element, or None if not found.
        """
        # Take a screenshot
        screenshot_data = await self.take_screenshot()
        
        # Use the agent's LLM to analyze the screenshot and find the element
        # This is a simplified version - in a real implementation, you would use
        # more sophisticated computer vision techniques
        
        # Create a temporary file to save the screenshot for the LLM
        screenshot_path = "temp_screenshot_for_llm.png"
        with open(screenshot_path, "wb") as f:
            f.write(screenshot_data)
        
        # Ask the LLM to analyze the screenshot and find the element
        # For GPT-4 Vision or similar models that can process images directly
        response = await self.agent.llm.apredict(
            f"""
            I need to find an element on this webpage that matches this description: "{element_description}".
            
            Please analyze the screenshot and tell me:
            1. If you can find the element
            2. The approximate coordinates (x, y) of the element
            3. What the element's selector might be (CSS or XPath)
            
            The screenshot is available at: {screenshot_path}
            
            Respond in JSON format:
            {{
                "found": true/false,
                "coordinates": [x, y],
                "selector": "selector string",
                "confidence": 0.0-1.0
            }}
            """
        )
        
        # Clean up the temporary file
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
        
        try:
            # Parse the response as JSON
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            print(f"Error parsing LLM response as JSON: {response}")
            return None
    
    async def verify_element(self, selector: str) -> bool:
        """
        Verify that an element exists on the page.
        
        Args:
            selector (str): The CSS selector of the element.
            
        Returns:
            bool: True if the element exists, False otherwise.
        """
        page = await self.agent.browser_context.get_current_page()
        element = await page.query_selector(selector)
        return element is not None
    
    async def get_element_attributes(self, selector: str) -> Optional[Dict]:
        """
        Get attributes of an element.
        
        Args:
            selector (str): The CSS selector of the element.
            
        Returns:
            Optional[Dict]: The element's attributes, or None if the element doesn't exist.
        """
        page = await self.agent.browser_context.get_current_page()
        
        # Check if the element exists
        element = await page.query_selector(selector)
        if not element:
            return None
        
        # Get the element's attributes
        attributes = await page.evaluate("""
            (selector) => {
                const element = document.querySelector(selector);
                if (!element) return null;
                
                const result = {};
                for (const attr of element.attributes) {
                    result[attr.name] = attr.value;
                }
                
                // Add some computed properties
                const rect = element.getBoundingClientRect();
                result.boundingRect = {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    top: rect.top,
                    right: rect.right,
                    bottom: rect.bottom,
                    left: rect.left
                };
                
                result.tagName = element.tagName.toLowerCase();
                result.innerText = element.innerText;
                
                return result;
            }
        """, selector)
        
        return attributes