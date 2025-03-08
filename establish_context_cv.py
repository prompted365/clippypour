import asyncio
import json
import os
import base64
import io
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, simpledialog
from PIL import Image, ImageTk
import pyperclip
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI

class ContextManager:
    """
    Manages the context for the ClippyPour application.
    Stores and retrieves data from persistent memory (JSON).
    """
    def __init__(self, storage_path: str = "context_storage.json"):
        """
        Initialize the ContextManager.
        
        Args:
            storage_path (str): Path to the JSON file for persistent storage.
        """
        self.storage_path = storage_path
        self.context = self._load_context()
    
    def _load_context(self) -> Dict:
        """Load context from the JSON file or create a new one if it doesn't exist."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {self.storage_path}. Creating new context.")
                return {}
        return {}
    
    def save_context(self) -> None:
        """Save the current context to the JSON file."""
        with open(self.storage_path, 'w') as f:
            json.dump(self.context, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        return self.context.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the context and save it."""
        self.context[key] = value
        self.save_context()
    
    def update(self, data: Dict) -> None:
        """Update multiple values in the context and save it."""
        self.context.update(data)
        self.save_context()
    
    def delete(self, key: str) -> None:
        """Delete a key from the context and save it."""
        if key in self.context:
            del self.context[key]
            self.save_context()
    
    def clear(self) -> None:
        """Clear all context data and save it."""
        self.context = {}
        self.save_context()


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


class ClippyPourUI:
    """
    Provides a chat interface for user interaction with ClippyPour.
    """
    def __init__(self, context_manager: ContextManager):
        """
        Initialize the UI.
        
        Args:
            context_manager (ContextManager): The context manager for persistent storage.
        """
        self.context_manager = context_manager
        self.root = tk.Tk()
        self.root.title("ClippyPour - Context Establishment with Computer Vision")
        self.root.geometry("1000x700")
        
        # Initialize browser and agent
        self.browser = None
        self.agent = None
        self.cv_helper = None
        self.browser_initialized = False
        
        # Create an asyncio event loop for the UI
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Set up the UI components."""
        # Create main frames
        self.left_frame = tk.Frame(self.root, width=600)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.right_frame = tk.Frame(self.root, width=400)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left frame components (chat)
        self.chat_frame = tk.Frame(self.left_frame)
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        
        self.input_frame = tk.Frame(self.left_frame)
        self.input_frame.pack(fill=tk.X, pady=10)
        
        self.button_frame = tk.Frame(self.left_frame)
        self.button_frame.pack(fill=tk.X)
        
        # Chat history
        self.chat_history = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_history.pack(fill=tk.BOTH, expand=True)
        
        # Input field
        self.input_field = tk.Entry(self.input_frame)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_field.bind("<Return>", self.send_message)
        
        self.send_button = tk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=5)
        
        # Buttons
        self.upload_button = tk.Button(self.button_frame, text="Upload File", command=self.upload_file)
        self.upload_button.pack(side=tk.LEFT, padx=5)
        
        self.init_browser_button = tk.Button(self.button_frame, text="Initialize Browser", command=self.init_browser_wrapper)
        self.init_browser_button.pack(side=tk.LEFT, padx=5)
        
        self.clipboard_button = tk.Button(self.button_frame, text="Load Clipboard", command=self.load_clipboard)
        self.clipboard_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(self.button_frame, text="Clear Context", command=self.clear_context)
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        # Right frame components (vision and context)
        self.vision_frame = tk.LabelFrame(self.right_frame, text="Computer Vision")
        self.vision_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.screenshot_label = tk.Label(self.vision_frame, text="No screenshot available")
        self.screenshot_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.vision_button_frame = tk.Frame(self.vision_frame)
        self.vision_button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.screenshot_button = tk.Button(self.vision_button_frame, text="Take Screenshot", command=self.take_screenshot_wrapper)
        self.screenshot_button.pack(side=tk.LEFT, padx=5)
        
        self.find_element_button = tk.Button(self.vision_button_frame, text="Find Element", command=self.find_element_wrapper)
        self.find_element_button.pack(side=tk.LEFT, padx=5)
        
        self.verify_button = tk.Button(self.vision_button_frame, text="Verify Element", command=self.verify_element_wrapper)
        self.verify_button.pack(side=tk.LEFT, padx=5)
        
        # Context display
        self.context_frame = tk.LabelFrame(self.right_frame, text="Current Context")
        self.context_frame.pack(fill=tk.BOTH, expand=True)
        
        self.context_display = scrolledtext.ScrolledText(self.context_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.context_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.refresh_context_button = tk.Button(self.context_frame, text="Refresh Context", command=self.refresh_context)
        self.refresh_context_button.pack(pady=5)
        
        # Add a system message to start
        self.add_message("System", "Welcome to ClippyPour Context Establishment with Computer Vision. How can I help you today?")
        
        # Initial context refresh
        self.refresh_context()
    
    def add_message(self, sender: str, message: str) -> None:
        """Add a message to the chat history."""
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"{sender}: {message}\n\n")
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.see(tk.END)
    
    def send_message(self, event=None) -> None:
        """Send a message from the input field."""
        message = self.input_field.get().strip()
        if message:
            self.add_message("You", message)
            self.input_field.delete(0, tk.END)
            
            # Process the message
            self.run_async(self.process_message(message))
    
    def run_async(self, coro):
        """Run an async coroutine in the event loop."""
        asyncio.run_coroutine_threadsafe(coro, self.loop)
    
    async def process_message(self, message: str) -> None:
        """Process a message from the user."""
        # Simple command processing
        if message.startswith("/"):
            await self.process_command(message)
            return
        
        # Store the message in context
        messages = self.context_manager.get("messages", [])
        messages.append({"role": "user", "content": message})
        self.context_manager.set("messages", messages)
        
        # Respond to the message
        self.add_message("System", "Message received and stored in context.")
        self.refresh_context()
    
    async def process_command(self, command: str) -> None:
        """Process a command from the user."""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()
        
        if cmd == "/help":
            self.add_message("System", """
Available commands:
/help - Show this help message
/goto [url] - Navigate to a URL in the browser
/fill [selector] - Fill a form field with clipboard content
/click [selector] - Click an element in the browser
/screenshot - Take a screenshot of the current page
/find [description] - Find an element by description using computer vision
/verify [selector] - Verify that an element exists and get its attributes
/context - Show the current context
/stream [selectors...] - Stream clipboard fields into multiple selectors
            """)
        
        elif cmd == "/goto" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            url = cmd_parts[1]
            self.add_message("System", f"Navigating to {url}...")
            
            try:
                await self.agent.browser_context.navigate_to(url)
                self.add_message("System", f"Successfully navigated to {url}")
                
                # Take a screenshot after navigation
                await self.take_screenshot()
            except Exception as e:
                self.add_message("System", f"Error navigating to {url}: {str(e)}")
        
        elif cmd == "/fill" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            selector = cmd_parts[1]
            clipboard_text = pyperclip.paste()
            
            if not clipboard_text:
                self.add_message("System", "Clipboard is empty. Please copy some text first.")
                return
            
            self.add_message("System", f"Filling {selector} with clipboard content...")
            
            try:
                page = await self.agent.browser_context.get_current_page()
                await page.fill(selector, clipboard_text)
                self.add_message("System", f"Successfully filled {selector}")
                
                # Take a screenshot after filling
                await self.take_screenshot()
            except Exception as e:
                self.add_message("System", f"Error filling {selector}: {str(e)}")
        
        elif cmd == "/click" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            selector = cmd_parts[1]
            self.add_message("System", f"Clicking {selector}...")
            
            try:
                page = await self.agent.browser_context.get_current_page()
                await page.click(selector)
                self.add_message("System", f"Successfully clicked {selector}")
                
                # Take a screenshot after clicking
                await self.take_screenshot()
            except Exception as e:
                self.add_message("System", f"Error clicking {selector}: {str(e)}")
        
        elif cmd == "/screenshot":
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            await self.take_screenshot()
        
        elif cmd == "/find" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            description = " ".join(cmd_parts[1:])
            await self.find_element_by_description(description)
        
        elif cmd == "/verify" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            selector = cmd_parts[1]
            await self.verify_element_by_selector(selector)
        
        elif cmd == "/context":
            self.refresh_context()
            self.add_message("System", "Context refreshed.")
        
        elif cmd == "/stream" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            selectors = cmd_parts[1:]
            await self.stream_clipboard_to_fields(selectors)
        
        else:
            self.add_message("System", f"Unknown command: {cmd}. Type /help for available commands.")
    
    def upload_file(self) -> None:
        """Upload a file and store its content in the context."""
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            file_name = os.path.basename(file_path)
            self.context_manager.set(f"file_{file_name}", content)
            
            self.add_message("System", f"File '{file_name}' uploaded and stored in context.")
            self.refresh_context()
        except Exception as e:
            self.add_message("System", f"Error uploading file: {str(e)}")
    
    def load_clipboard(self) -> None:
        """Load clipboard content and store it in the context."""
        try:
            clipboard_content = pyperclip.paste()
            if not clipboard_content:
                self.add_message("System", "Clipboard is empty.")
                return
            
            self.context_manager.set("clipboard", clipboard_content)
            
            # Also parse the clipboard content if it contains delimiters
            if "||" in clipboard_content:
                fields = clipboard_content.split("||")
                self.context_manager.set("clipboard_fields", [field.strip() for field in fields])
                self.add_message("System", f"Clipboard content loaded and parsed into {len(fields)} fields.")
            else:
                self.add_message("System", "Clipboard content loaded.")
            
            self.refresh_context()
        except Exception as e:
            self.add_message("System", f"Error loading clipboard: {str(e)}")
    
    def clear_context(self) -> None:
        """Clear the context after confirmation."""
        if messagebox.askyesno("Clear Context", "Are you sure you want to clear all context data?"):
            self.context_manager.clear()
            self.add_message("System", "Context cleared.")
            self.refresh_context()
    
    def refresh_context(self) -> None:
        """Refresh the context display."""
        context_str = json.dumps(self.context_manager.context, indent=2)
        
        self.context_display.config(state=tk.NORMAL)
        self.context_display.delete(1.0, tk.END)
        self.context_display.insert(tk.END, context_str)
        self.context_display.config(state=tk.DISABLED)
    
    # Wrapper methods for async functions
    def init_browser_wrapper(self) -> None:
        """Wrapper for init_browser to run it asynchronously."""
        self.run_async(self.init_browser())
    
    def take_screenshot_wrapper(self) -> None:
        """Wrapper for take_screenshot to run it asynchronously."""
        self.run_async(self.take_screenshot())
    
    def find_element_wrapper(self) -> None:
        """Wrapper for find_element to run it asynchronously."""
        if not self.browser_initialized:
            messagebox.showwarning("Browser Not Initialized", "Please initialize the browser first.")
            return
        
        description = simpledialog.askstring("Find Element", "Enter element description:")
        if description:
            self.run_async(self.find_element_by_description(description))
    
    def verify_element_wrapper(self) -> None:
        """Wrapper for verify_element to run it asynchronously."""
        if not self.browser_initialized:
            messagebox.showwarning("Browser Not Initialized", "Please initialize the browser first.")
            return
        
        selector = simpledialog.askstring("Verify Element", "Enter element selector:")
        if selector:
            self.run_async(self.verify_element_by_selector(selector))
    
    async def init_browser(self) -> None:
        """Initialize the browser and agent."""
        if self.browser_initialized:
            self.add_message("System", "Browser already initialized.")
            return
        
        self.add_message("System", "Initializing browser...")
        
        try:
            # Initialize browser
            browser_config = BrowserConfig(headless=False)
            self.browser = Browser(config=browser_config)
            
            # Create agent
            task = "Establish context and fill forms using ClippyPour with computer vision."
            llm = ChatOpenAI(model="gpt-4o")
            self.agent = Agent(task=task, llm=llm, browser=self.browser)
            
            # Create computer vision helper
            self.cv_helper = ComputerVisionHelper(self.agent)
            
            self.browser_initialized = True
            self.add_message("System", "Browser initialized successfully.")
        except Exception as e:
            self.add_message("System", f"Error initializing browser: {str(e)}")
    
    async def take_screenshot(self) -> None:
        """Take a screenshot and display it."""
        if not self.browser_initialized:
            self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
            return
        
        self.add_message("System", "Taking screenshot...")
        
        try:
            screenshot_data = await self.cv_helper.take_screenshot()
            
            # Save the screenshot to a file instead of storing as base64
            screenshot_path = "last_screenshot.png"
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_data)
            
            # Store the path to the screenshot in the context instead of base64
            self.context_manager.set("last_screenshot_path", screenshot_path)
            
            # Display the screenshot
            image = Image.open(io.BytesIO(screenshot_data))
            
            # Resize the image to fit the display area
            max_width = 380
            max_height = 300
            width, height = image.size
            
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                image = image.resize((new_width, new_height), Image.LANCZOS)
            
            photo = ImageTk.PhotoImage(image)
            
            # Update the screenshot label
            self.screenshot_label.config(image=photo)
            self.screenshot_label.image = photo  # Keep a reference to prevent garbage collection
            
            self.add_message("System", f"Screenshot taken and saved to {screenshot_path}.")
            self.refresh_context()
        except Exception as e:
            self.add_message("System", f"Error taking screenshot: {str(e)}")
    
    async def find_element_by_description(self, description: str) -> None:
        """Find an element by description using computer vision."""
        if not self.browser_initialized:
            self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
            return
        
        self.add_message("System", f"Finding element: '{description}'...")
        
        try:
            result = await self.cv_helper.find_element_by_vision(description)
            
            if result and result.get("found", False):
                self.context_manager.set("last_found_element", result)
                
                # Format the result for display
                coords = result.get("coordinates", [0, 0])
                selector = result.get("selector", "Unknown")
                confidence = result.get("confidence", 0.0)
                
                self.add_message("System", f"""
Element found:
- Coordinates: ({coords[0]}, {coords[1]})
- Selector: {selector}
- Confidence: {confidence:.2f}
                """)
                
                # Store the selector for later use
                self.context_manager.set("last_selector", selector)
            else:
                self.add_message("System", f"Element not found: '{description}'")
            
            self.refresh_context()
        except Exception as e:
            self.add_message("System", f"Error finding element: {str(e)}")
    
    async def verify_element_by_selector(self, selector: str) -> None:
        """Verify that an element exists and get its attributes."""
        if not self.browser_initialized:
            self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
            return
        
        self.add_message("System", f"Verifying element: '{selector}'...")
        
        try:
            exists = await self.cv_helper.verify_element(selector)
            
            if exists:
                attributes = await self.cv_helper.get_element_attributes(selector)
                
                if attributes:
                    self.context_manager.set("last_verified_element", attributes)
                    
                    # Format the attributes for display
                    attrs_str = json.dumps(attributes, indent=2)
                    
                    self.add_message("System", f"""
Element verified:
- Selector: {selector}
- Tag: {attributes.get('tagName', 'Unknown')}
- Text: {attributes.get('innerText', 'None')[:50]}...
- Attributes: {len(attributes)} attributes found
                    """)
                else:
                    self.add_message("System", f"Element exists but couldn't get attributes: '{selector}'")
            else:
                self.add_message("System", f"Element not found: '{selector}'")
            
            self.refresh_context()
        except Exception as e:
            self.add_message("System", f"Error verifying element: {str(e)}")
    
    async def stream_clipboard_to_fields(self, selectors: List[str]) -> None:
        """Stream clipboard fields into multiple selectors."""
        if not self.browser_initialized:
            self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
            return
        
        clipboard_content = pyperclip.paste()
        if not clipboard_content:
            self.add_message("System", "Clipboard is empty. Please copy some text first.")
            return
        
        # Parse the clipboard content
        if "||" in clipboard_content:
            fields = [field.strip() for field in clipboard_content.split("||")]
        else:
            fields = [clipboard_content]
        
        if len(fields) != len(selectors):
            self.add_message("System", f"Warning: Number of fields ({len(fields)}) doesn't match number of selectors ({len(selectors)}).")
        
        self.add_message("System", f"Streaming {min(len(fields), len(selectors))} fields to form...")
        
        try:
            page = await self.agent.browser_context.get_current_page()
            
            for i, selector in enumerate(selectors):
                if i >= len(fields):
                    break
                
                text = fields[i]
                self.add_message("System", f"Filling field {i+1} ({selector}) with: {text[:20]}...")
                await page.fill(selector, text)
                await asyncio.sleep(0.5)  # Simulate a short typing delay
            
            self.add_message("System", "Form filling complete.")
            
            # Take a screenshot after filling
            await self.take_screenshot()
        except Exception as e:
            self.add_message("System", f"Error filling form: {str(e)}")
    
    def run(self) -> None:
        """Run the UI main loop."""
        # Start the asyncio event loop in a separate thread
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        # Run the Tkinter main loop
        self.root.mainloop()
    
    def _run_event_loop(self) -> None:
        """Run the asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    async def close(self) -> None:
        """Close the browser and clean up."""
        if self.browser:
            await self.browser.close()
        
        # Stop the event loop
        self.loop.stop()


class EstablishContextCV:
    """
    Main class for establishing context and filling forms with computer vision.
    """
    def __init__(self, storage_path: str = "context_storage.json"):
        """
        Initialize the EstablishContextCV.
        
        Args:
            storage_path (str): Path to the JSON file for persistent storage.
        """
        self.context_manager = ContextManager(storage_path)
        self.ui = None
    
    async def run(self) -> None:
        """Run the context establishment loop."""
        self.ui = ClippyPourUI(self.context_manager)
        
        # Set up event handling for the UI
        asyncio.create_task(self._handle_events())
        
        # Run the UI
        self.ui.run()
    
    async def _handle_events(self) -> None:
        """Handle events for the UI."""
        # This runs in the background to handle async events
        while True:
            await asyncio.sleep(0.1)
    
    async def close(self) -> None:
        """Close the application."""
        if self.ui:
            await self.ui.close()


async def main():
    """Main entry point for the application."""
    establish_context = EstablishContextCV()
    await establish_context.run()


if __name__ == "__main__":
    # Run the application
    asyncio.run(main())
