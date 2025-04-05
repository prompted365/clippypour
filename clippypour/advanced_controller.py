"""
Advanced Controller module for ClippyPour.

This module extends the ClippyPourController with advanced features:
1. Computer vision capabilities for when selectors fail
2. Wait actions for handling asynchronous workflows
3. Command palette functionality for both AI and human users
"""

import asyncio
import json
import base64
import os
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field

from browser_use import Controller, Browser, ActionResult

from .controller import ClippyPourController, FormField, Form, FormTemplate


class ScreenCoordinates(BaseModel):
    """Model representing screen coordinates."""
    x: int = Field(..., description="X coordinate")
    y: int = Field(..., description="Y coordinate")


class ElementBounds(BaseModel):
    """Model representing element bounds."""
    x: int = Field(..., description="X coordinate")
    y: int = Field(..., description="Y coordinate")
    width: int = Field(..., description="Width of the element")
    height: int = Field(..., description="Height of the element")


class AdvancedClippyPourController(ClippyPourController):
    """
    Advanced Controller for ClippyPour that extends the base controller with
    computer vision capabilities, wait actions, and command palette functionality.
    """
    
    def __init__(self, template_manager=None, *args, **kwargs):
        """
        Initialize the AdvancedClippyPourController.
        
        Args:
            template_manager: The template manager instance for saving/loading templates
            *args, **kwargs: Additional arguments to pass to the parent Controller
        """
        super().__init__(template_manager, *args, **kwargs)
        self._register_advanced_actions()
    
    def _register_advanced_actions(self):
        """Register advanced actions with the controller."""
        
        @self.action("Take screenshot")
        async def take_screenshot(browser: Browser) -> ActionResult:
            """
            Take a screenshot of the current page.
            
            Args:
                browser: The browser instance
                
            Returns:
                ActionResult: Path to the screenshot file
            """
            page = await browser.get_current_page()
            
            # Create a directory for screenshots if it doesn't exist
            screenshots_dir = os.path.join(os.path.expanduser("~"), ".clippypour", "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Generate a filename with timestamp
            timestamp = int(time.time())
            screenshot_path = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
            
            # Take the screenshot
            await page.screenshot(path=screenshot_path)
            
            return ActionResult(
                extracted_content=f"Screenshot saved to {screenshot_path}"
            )
        
        @self.action("Find element by vision")
        async def find_element_by_vision(element_description: str, browser: Browser) -> ActionResult:
            """
            Find an element on the page using computer vision when selectors fail.
            
            Args:
                element_description: Description of the element to find
                browser: The browser instance
                
            Returns:
                ActionResult: Information about the found element
            """
            page = await browser.get_current_page()
            
            # Take a screenshot
            screenshots_dir = os.path.join(os.path.expanduser("~"), ".clippypour", "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            timestamp = int(time.time())
            screenshot_path = os.path.join(screenshots_dir, f"vision_search_{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            
            # Get the page dimensions
            dimensions = await page.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight,
                        scrollX: window.scrollX,
                        scrollY: window.scrollY
                    };
                }
            """)
            
            # Convert the screenshot to base64 for the LLM
            with open(screenshot_path, "rb") as f:
                screenshot_base64 = base64.b64encode(f.read()).decode("utf-8")
            
            # Ask the LLM to analyze the screenshot and find the element
            llm = browser.agent.llm
            response = await llm.apredict(
                f"""
                I need to find an element on this webpage that matches this description: "{element_description}".
                
                The page dimensions are:
                - Width: {dimensions['width']}px
                - Height: {dimensions['height']}px
                - Current scroll position: ({dimensions['scrollX']}px, {dimensions['scrollY']}px)
                
                Please analyze the screenshot and tell me:
                1. If you can find the element
                2. The approximate coordinates (x, y) of the element
                3. What the element might be (button, input field, link, etc.)
                4. Any text content or attributes that might help identify it
                
                Respond with ONLY a JSON object in this format:
                {{
                    "found": true/false,
                    "coordinates": [x, y],
                    "element_type": "button/input/link/etc",
                    "description": "Brief description of what you see",
                    "confidence": 0.0-1.0
                }}
                """
            )
            
            # Extract the JSON from the response
            try:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
                if json_match:
                    vision_result = json.loads(json_match.group(1))
                else:
                    # If that fails, try to find anything that looks like JSON
                    json_match = re.search(r'({[\s\S]*})', response)
                    if json_match:
                        vision_result = json.loads(json_match.group(1))
                    else:
                        vision_result = {"found": False, "error": "Could not parse LLM response"}
            except:
                vision_result = {"found": False, "error": "Could not parse LLM response"}
            
            # Add the screenshot path to the result
            vision_result["screenshot_path"] = screenshot_path
            
            return ActionResult(
                extracted_content=json.dumps(vision_result, indent=2)
            )
        
        @self.action("Click at coordinates")
        async def click_at_coordinates(x: int, y: int, browser: Browser) -> ActionResult:
            """
            Click at specific coordinates on the page.
            
            Args:
                x: X coordinate
                y: Y coordinate
                browser: The browser instance
                
            Returns:
                ActionResult: Result of the click operation
            """
            page = await browser.get_current_page()
            
            # Scroll to ensure the coordinates are in view
            await page.evaluate(f"""
                () => {{
                    const x = {x};
                    const y = {y};
                    
                    // Calculate if we need to scroll
                    const viewportHeight = window.innerHeight;
                    const viewportWidth = window.innerWidth;
                    
                    if (y < window.scrollY || y > window.scrollY + viewportHeight) {{
                        window.scrollTo({{
                            top: Math.max(0, y - (viewportHeight / 2)),
                            behavior: 'smooth'
                        }});
                    }}
                    
                    if (x < window.scrollX || x > window.scrollX + viewportWidth) {{
                        window.scrollTo({{
                            left: Math.max(0, x - (viewportWidth / 2)),
                            behavior: 'smooth'
                        }});
                    }}
                }}
            """)
            
            # Wait a moment for the scroll to complete
            await asyncio.sleep(0.5)
            
            # Click at the coordinates
            await page.mouse.click(x, y)
            
            return ActionResult(
                extracted_content=f"Clicked at coordinates ({x}, {y})"
            )
        
        @self.action("Wait for element")
        async def wait_for_element(selector: str, browser: Browser, timeout: int = 30000) -> ActionResult:
            """
            Wait for an element to appear on the page.
            
            Args:
                selector: CSS selector for the element
                timeout: Maximum time to wait in milliseconds
                browser: The browser instance
                
            Returns:
                ActionResult: Result of the wait operation
            """
            page = await browser.get_current_page()
            
            try:
                await page.wait_for_selector(selector, timeout=timeout)
                return ActionResult(
                    extracted_content=f"Element with selector '{selector}' appeared on the page"
                )
            except Exception as e:
                return ActionResult(
                    extracted_content=f"Error waiting for element: {str(e)}"
                )
        
        @self.action("Wait for navigation")
        async def wait_for_navigation(browser: Browser, timeout: int = 30000) -> ActionResult:
            """
            Wait for page navigation to complete.
            
            Args:
                timeout: Maximum time to wait in milliseconds
                browser: The browser instance
                
            Returns:
                ActionResult: Result of the wait operation
            """
            page = await browser.get_current_page()
            
            try:
                await page.wait_for_navigation(timeout=timeout)
                return ActionResult(
                    extracted_content=f"Navigation completed. New URL: {page.url}"
                )
            except Exception as e:
                return ActionResult(
                    extracted_content=f"Error waiting for navigation: {str(e)}"
                )
        
        @self.action("Wait for network idle")
        async def wait_for_network_idle(browser: Browser, timeout: int = 30000) -> ActionResult:
            """
            Wait for network to become idle (no requests for 500ms).
            
            Args:
                timeout: Maximum time to wait in milliseconds
                browser: The browser instance
                
            Returns:
                ActionResult: Result of the wait operation
            """
            page = await browser.get_current_page()
            
            try:
                await page.wait_for_load_state("networkidle", timeout=timeout)
                return ActionResult(
                    extracted_content="Network is now idle"
                )
            except Exception as e:
                return ActionResult(
                    extracted_content=f"Error waiting for network idle: {str(e)}"
                )
        
        @self.action("Wait fixed time")
        async def wait_fixed_time(browser: Browser, seconds: float = 1.0) -> ActionResult:
            """
            Wait for a fixed amount of time.
            
            Args:
                seconds: Number of seconds to wait
                browser: The browser instance
                
            Returns:
                ActionResult: Result of the wait operation
            """
            await asyncio.sleep(seconds)
            return ActionResult(
                extracted_content=f"Waited for {seconds} seconds"
            )
        
        @self.action("Get page grid")
        async def get_page_grid(rows: int = 10, columns: int = 10, browser: Browser) -> ActionResult:
            """
            Divide the page into a grid and return information about each cell.
            
            Args:
                rows: Number of rows in the grid
                columns: Number of columns in the grid
                browser: The browser instance
                
            Returns:
                ActionResult: Grid information
            """
            page = await browser.get_current_page()
            
            # Get the page dimensions
            dimensions = await page.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight,
                        scrollX: window.scrollX,
                        scrollY: window.scrollY,
                        documentHeight: document.body.scrollHeight,
                        documentWidth: document.body.scrollWidth
                    };
                }
            """)
            
            # Calculate cell dimensions
            cell_width = dimensions["width"] / columns
            cell_height = dimensions["height"] / rows
            
            # Create the grid
            grid = []
            for row in range(rows):
                grid_row = []
                for col in range(columns):
                    # Calculate cell coordinates
                    x = int(col * cell_width + (cell_width / 2))
                    y = int(row * cell_height + (cell_height / 2))
                    
                    # Get element at this position
                    element_info = await page.evaluate(f"""
                        () => {{
                            const x = {x};
                            const y = {y};
                            
                            // Get the element at this position
                            const element = document.elementFromPoint(x, y);
                            
                            if (!element) {{
                                return {{
                                    empty: true,
                                    coordinates: [x, y]
                                }};
                            }}
                            
                            // Get basic info about the element
                            return {{
                                tagName: element.tagName.toLowerCase(),
                                id: element.id || null,
                                className: element.className || null,
                                textContent: element.textContent?.trim().substring(0, 50) || null,
                                coordinates: [x, y],
                                isClickable: element.tagName === 'A' || 
                                             element.tagName === 'BUTTON' || 
                                             element.onclick != null ||
                                             element.tagName === 'INPUT' ||
                                             window.getComputedStyle(element).cursor === 'pointer'
                            }};
                        }}
                    """)
                    
                    # Add cell info to the grid
                    grid_row.append({
                        "row": row,
                        "column": col,
                        "center_x": x,
                        "center_y": y,
                        "top_left": [int(col * cell_width), int(row * cell_height)],
                        "bottom_right": [int((col + 1) * cell_width), int((row + 1) * cell_height)],
                        "element": element_info
                    })
                
                grid.append(grid_row)
            
            # Create a visual representation of the grid
            grid_visual = []
            for row in grid:
                row_visual = []
                for cell in row:
                    if cell["element"].get("empty", False):
                        row_visual.append("□")  # Empty cell
                    elif cell["element"].get("isClickable", False):
                        row_visual.append("▣")  # Clickable element
                    else:
                        row_visual.append("■")  # Non-clickable element
                grid_visual.append("".join(row_visual))
            
            result = {
                "dimensions": dimensions,
                "grid_size": {"rows": rows, "columns": columns},
                "cell_size": {"width": cell_width, "height": cell_height},
                "grid": grid,
                "visual": "\n".join(grid_visual)
            }
            
            return ActionResult(
                extracted_content=json.dumps(result, indent=2)
            )
        
        @self.action("Open command palette")
        async def open_command_palette(for_agent: bool = False, browser: Browser) -> ActionResult:
            """
            Open the command palette UI.
            
            Args:
                for_agent: Whether this is for the AI agent (True) or human (False)
                browser: The browser instance
                
            Returns:
                ActionResult: Result of opening the command palette
            """
            page = await browser.get_current_page()
            
            # Inject the command palette UI
            await page.evaluate(f"""
                () => {{
                    // Check if the command palette already exists
                    if (document.getElementById('clippypour-command-palette-{for_agent}')) {{
                        return;
                    }}
                    
                    // Create the command palette container
                    const palette = document.createElement('div');
                    palette.id = 'clippypour-command-palette-{for_agent}';
                    palette.style.position = 'fixed';
                    palette.style.top = '20%';
                    palette.style.left = '{50 - 20 if for_agent else 50 + 20}%';
                    palette.style.transform = 'translateX(-50%)';
                    palette.style.width = '400px';
                    palette.style.maxHeight = '60%';
                    palette.style.backgroundColor = '{for_agent and "#1a1a2e" or "#2e1a1a"}';
                    palette.style.color = 'white';
                    palette.style.borderRadius = '8px';
                    palette.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.5)';
                    palette.style.zIndex = '10000';
                    palette.style.overflow = 'hidden';
                    palette.style.display = 'flex';
                    palette.style.flexDirection = 'column';
                    palette.style.transition = 'all 0.3s ease';
                    
                    // Create the header
                    const header = document.createElement('div');
                    header.style.padding = '12px 16px';
                    header.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
                    header.style.display = 'flex';
                    header.style.justifyContent = 'space-between';
                    header.style.alignItems = 'center';
                    
                    const title = document.createElement('div');
                    title.textContent = '{for_agent and "AI Agent" or "Human"} Command Palette';
                    title.style.fontWeight = 'bold';
                    
                    const closeButton = document.createElement('button');
                    closeButton.textContent = '×';
                    closeButton.style.background = 'none';
                    closeButton.style.border = 'none';
                    closeButton.style.color = 'white';
                    closeButton.style.fontSize = '20px';
                    closeButton.style.cursor = 'pointer';
                    closeButton.onclick = () => {{
                        document.body.removeChild(palette);
                        
                        // Check if both palettes are closed and center the remaining one
                        const otherPalette = document.getElementById('clippypour-command-palette-{not for_agent}');
                        if (otherPalette) {{
                            otherPalette.style.left = '50%';
                        }}
                    }};
                    
                    header.appendChild(title);
                    header.appendChild(closeButton);
                    palette.appendChild(header);
                    
                    // Create the search input
                    const searchContainer = document.createElement('div');
                    searchContainer.style.padding = '12px 16px';
                    searchContainer.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
                    
                    const searchInput = document.createElement('input');
                    searchInput.type = 'text';
                    searchInput.placeholder = 'Search commands...';
                    searchInput.style.width = '100%';
                    searchInput.style.padding = '8px 12px';
                    searchInput.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                    searchInput.style.border = 'none';
                    searchInput.style.borderRadius = '4px';
                    searchInput.style.color = 'white';
                    searchInput.style.fontSize = '14px';
                    
                    searchContainer.appendChild(searchInput);
                    palette.appendChild(searchContainer);
                    
                    // Create the commands list
                    const commandsList = document.createElement('div');
                    commandsList.style.overflowY = 'auto';
                    commandsList.style.flex = '1';
                    
                    // Add some example commands
                    const commands = [
                        {{ name: 'Take Screenshot', description: 'Capture the current page' }},
                        {{ name: 'Fill Form', description: 'Automatically fill the current form' }},
                        {{ name: 'Save Template', description: 'Save the current form as a template' }},
                        {{ name: 'Load Template', description: 'Load a saved form template' }},
                        {{ name: 'Visual Select', description: 'Select elements visually' }},
                        {{ name: 'Wait for Element', description: 'Wait for an element to appear' }},
                        {{ name: 'Click at Coordinates', description: 'Click at specific coordinates' }},
                        {{ name: 'Get Page Grid', description: 'Divide page into a grid' }}
                    ];
                    
                    commands.forEach(command => {{
                        const commandItem = document.createElement('div');
                        commandItem.className = 'clippypour-command-item';
                        commandItem.style.padding = '10px 16px';
                        commandItem.style.borderBottom = '1px solid rgba(255, 255, 255, 0.05)';
                        commandItem.style.cursor = 'pointer';
                        commandItem.style.transition = 'background-color 0.2s';
                        
                        commandItem.onmouseover = () => {{
                            commandItem.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                        }};
                        
                        commandItem.onmouseout = () => {{
                            commandItem.style.backgroundColor = 'transparent';
                        }};
                        
                        const commandName = document.createElement('div');
                        commandName.textContent = command.name;
                        commandName.style.fontWeight = 'bold';
                        commandName.style.marginBottom = '4px';
                        
                        const commandDesc = document.createElement('div');
                        commandDesc.textContent = command.description;
                        commandDesc.style.fontSize = '12px';
                        commandDesc.style.opacity = '0.7';
                        
                        commandItem.appendChild(commandName);
                        commandItem.appendChild(commandDesc);
                        commandsList.appendChild(commandItem);
                    }});
                    
                    palette.appendChild(commandsList);
                    
                    // Add to the page
                    document.body.appendChild(palette);
                    
                    // Focus the search input
                    searchInput.focus();
                    
                    // If both palettes are open, adjust their positions
                    const otherPalette = document.getElementById('clippypour-command-palette-{not for_agent}');
                    if (otherPalette) {{
                        palette.style.left = '{for_agent and "30%" or "70%"}';
                        otherPalette.style.left = '{for_agent and "70%" or "30%"}';
                    }}
                }}
            """)
            
            return ActionResult(
                extracted_content=f"Command palette opened for {'AI agent' if for_agent else 'human'}"
            )
        
        @self.action("Execute command from palette")
        async def execute_command_from_palette(command_name: str, for_agent: bool = False, browser: Browser) -> ActionResult:
            """
            Execute a command from the command palette.
            
            Args:
                command_name: Name of the command to execute
                for_agent: Whether this is for the AI agent (True) or human (False)
                browser: The browser instance
                
            Returns:
                ActionResult: Result of executing the command
            """
            # Map command names to actions
            command_map = {
                "Take Screenshot": "Take screenshot",
                "Fill Form": "Fill form fields",
                "Save Template": "Save form template",
                "Load Template": "Load form template",
                "Visual Select": "Activate visual selector",
                "Wait for Element": "Wait for element",
                "Click at Coordinates": "Click at coordinates",
                "Get Page Grid": "Get page grid"
            }
            
            if command_name not in command_map:
                return ActionResult(
                    extracted_content=f"Unknown command: {command_name}"
                )
            
            # Return the action name that should be executed
            return ActionResult(
                extracted_content=f"Execute action: {command_map[command_name]}"
            )
        
        @self.action("Close command palette")
        async def close_command_palette(for_agent: bool = False, browser: Browser) -> ActionResult:
            """
            Close the command palette UI.
            
            Args:
                for_agent: Whether this is for the AI agent (True) or human (False)
                browser: The browser instance
                
            Returns:
                ActionResult: Result of closing the command palette
            """
            page = await browser.get_current_page()
            
            # Remove the command palette
            await page.evaluate(f"""
                () => {{
                    const palette = document.getElementById('clippypour-command-palette-{for_agent}');
                    if (palette) {{
                        document.body.removeChild(palette);
                        
                        // Check if the other palette is still open and center it
                        const otherPalette = document.getElementById('clippypour-command-palette-{not for_agent}');
                        if (otherPalette) {{
                            otherPalette.style.left = '50%';
                        }}
                    }}
                }}
            """)
            
            return ActionResult(
                extracted_content=f"Command palette closed for {'AI agent' if for_agent else 'human'}"
            )