import asyncio
import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, simpledialog
from PIL import Image, ImageTk
import pyperclip
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI

from .context_manager import ContextManager
from .cv_helper import ComputerVisionHelper

class ClippyPourUI:
    """
    Provides a chat interface for user interaction with ClippyPour.
    """
    def __init__(self, context_manager: ContextManager, with_cv: bool = False):
        """
        Initialize the UI.
        
        Args:
            context_manager (ContextManager): The context manager for persistent storage.
            with_cv (bool): Whether to include computer vision features.
        """
        self.context_manager = context_manager
        self.with_cv = with_cv
        self.root = tk.Tk()
        
        if with_cv:
            self.root.title("ClippyPour - Context Establishment with Computer Vision")
            self.root.geometry("1000x700")
        else:
            self.root.title("ClippyPour - Context Establishment")
            self.root.geometry("900x600")
        
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
        
        self.right_frame = tk.Frame(self.root, width=300 if not self.with_cv else 400)
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
        
        # Computer Vision components if enabled
        if self.with_cv:
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
        welcome_msg = "Welcome to ClippyPour Context Establishment"
        if self.with_cv:
            welcome_msg += " with Computer Vision"
        welcome_msg += ". How can I help you today?"
        self.add_message("System", welcome_msg)
        
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
            help_text = """
Available commands:
/help - Show this help message
/goto [url] - Navigate to a URL in the browser
/fill [selector] - Fill a form field with clipboard content
/click [selector] - Click an element in the browser
/context - Show the current context
            """
            
            if self.with_cv:
                help_text += """
/screenshot - Take a screenshot of the current page
/find [description] - Find an element by description using computer vision
/verify [selector] - Verify that an element exists and get its attributes
/stream [selectors...] - Stream clipboard fields into multiple selectors
                """
            
            self.add_message("System", help_text)
        
        elif cmd == "/goto" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            url = cmd_parts[1]
            self.add_message("System", f"Navigating to {url}...")
            
            try:
                await self.agent.browser_context.navigate_to(url)
                self.add_message("System", f"Successfully navigated to {url}")
                
                # Take a screenshot after navigation if CV is enabled
                if self.with_cv:
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
            except Exception as e:
                self.add_message("System", f"Error clicking {selector}: {str(e)}")
        
        elif cmd == "/context":
            self.refresh_context()
            self.add_message("System", "Context refreshed.")
        
        # Computer Vision commands
        elif self.with_cv and cmd == "/screenshot":
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            await self.take_screenshot()
            self.add_message("System", "Screenshot taken.")
        
        elif self.with_cv and cmd == "/find" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            description = " ".join(cmd_parts[1:])
            self.add_message("System", f"Finding element matching: {description}...")
            
            result = await self.cv_helper.find_element_by_vision(description)
            if result and result.get("found", False):
                self.add_message("System", f"Found element: {json.dumps(result, indent=2)}")
                self.context_manager.set("last_found_element", result)
                self.refresh_context()
            else:
                self.add_message("System", f"Element not found: {description}")
        
        elif self.with_cv and cmd == "/verify" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            selector = cmd_parts[1]
            self.add_message("System", f"Verifying element: {selector}...")
            
            exists = await self.cv_helper.verify_element(selector)
            if exists:
                attributes = await self.cv_helper.get_element_attributes(selector)
                self.add_message("System", f"Element exists. Attributes: {json.dumps(attributes, indent=2)}")
                self.context_manager.set("last_verified_element", attributes)
                self.refresh_context()
            else:
                self.add_message("System", f"Element does not exist: {selector}")
        
        elif self.with_cv and cmd == "/stream" and len(cmd_parts) > 1:
            if not self.browser_initialized:
                self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
                return
            
            selectors = cmd_parts[1:]
            clipboard_text = pyperclip.paste()
            
            if not clipboard_text:
                self.add_message("System", "Clipboard is empty. Please copy some text first.")
                return
            
            if "||" not in clipboard_text:
                self.add_message("System", "Clipboard content does not contain the delimiter '||'. Please use the format 'value1 || value2 || value3'.")
                return
            
            fields = clipboard_text.split("||")
            fields = [field.strip() for field in fields]
            
            if len(fields) != len(selectors):
                self.add_message("System", f"Number of fields ({len(fields)}) does not match number of selectors ({len(selectors)}).")
                return
            
            self.add_message("System", f"Streaming {len(fields)} fields into {len(selectors)} selectors...")
            
            page = await self.agent.browser_context.get_current_page()
            for i, (selector, field) in enumerate(zip(selectors, fields)):
                try:
                    self.add_message("System", f"Filling {selector} with: {field}")
                    await page.fill(selector, field)
                    await asyncio.sleep(0.5)  # Short delay between fields
                except Exception as e:
                    self.add_message("System", f"Error filling {selector}: {str(e)}")
                    break
            
            self.add_message("System", "Streaming complete.")
        
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
            task = "Establish context and fill forms using ClippyPour."
            llm = ChatOpenAI(model="gpt-4o")
            self.agent = Agent(task=task, llm=llm, browser=self.browser)
            
            # Initialize CV helper if needed
            if self.with_cv:
                self.cv_helper = ComputerVisionHelper(self.agent)
            
            self.browser_initialized = True
            self.add_message("System", "Browser initialized successfully.")
        except Exception as e:
            self.add_message("System", f"Error initializing browser: {str(e)}")
    
    # Computer Vision methods
    async def take_screenshot(self) -> None:
        """Take a screenshot of the current page and display it."""
        if not self.with_cv or not self.browser_initialized:
            return
        
        try:
            screenshot_data = await self.cv_helper.take_screenshot()
            
            # Save the screenshot to a temporary file
            temp_path = "temp_screenshot_display.png"
            with open(temp_path, "wb") as f:
                f.write(screenshot_data)
            
            # Display the screenshot in the UI
            img = Image.open(temp_path)
            img = img.resize((300, 200), Image.LANCZOS)  # Resize to fit in the UI
            photo = ImageTk.PhotoImage(img)
            
            self.screenshot_label.config(image=photo)
            self.screenshot_label.image = photo  # Keep a reference to prevent garbage collection
            
            # Clean up the temporary file
            os.remove(temp_path)
            
            self.add_message("System", "Screenshot taken and displayed.")
        except Exception as e:
            self.add_message("System", f"Error taking screenshot: {str(e)}")
    
    def take_screenshot_wrapper(self) -> None:
        """Wrapper for take_screenshot to run it asynchronously."""
        if not self.with_cv:
            return
        
        if not self.browser_initialized:
            self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
            return
        
        self.run_async(self.take_screenshot())
    
    def find_element_wrapper(self) -> None:
        """Wrapper for find_element_by_vision to run it asynchronously."""
        if not self.with_cv:
            return
        
        if not self.browser_initialized:
            self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
            return
        
        description = simpledialog.askstring("Find Element", "Enter element description:")
        if description:
            self.add_message("System", f"Finding element matching: {description}...")
            self.run_async(self.find_element(description))
    
    async def find_element(self, description: str) -> None:
        """Find an element by description using computer vision."""
        if not self.with_cv or not self.browser_initialized:
            return
        
        result = await self.cv_helper.find_element_by_vision(description)
        if result and result.get("found", False):
            self.add_message("System", f"Found element: {json.dumps(result, indent=2)}")
            self.context_manager.set("last_found_element", result)
            self.refresh_context()
        else:
            self.add_message("System", f"Element not found: {description}")
    
    def verify_element_wrapper(self) -> None:
        """Wrapper for verify_element to run it asynchronously."""
        if not self.with_cv:
            return
        
        if not self.browser_initialized:
            self.add_message("System", "Browser not initialized. Please click 'Initialize Browser' first.")
            return
        
        selector = simpledialog.askstring("Verify Element", "Enter element selector:")
        if selector:
            self.add_message("System", f"Verifying element: {selector}...")
            self.run_async(self.verify_element(selector))
    
    async def verify_element(self, selector: str) -> None:
        """Verify that an element exists and get its attributes."""
        if not self.with_cv or not self.browser_initialized:
            return
        
        exists = await self.cv_helper.verify_element(selector)
        if exists:
            attributes = await self.cv_helper.get_element_attributes(selector)
            self.add_message("System", f"Element exists. Attributes: {json.dumps(attributes, indent=2)}")
            self.context_manager.set("last_verified_element", attributes)
            self.refresh_context()
        else:
            self.add_message("System", f"Element does not exist: {selector}")
    
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