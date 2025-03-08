import asyncio
import json
import os
import base64
import io
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
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
        self.root.title("ClippyPour - Context Establishment")
        self.root.geometry("900x600")
        
        # Initialize browser and agent
        self.browser = None
        self.agent = None
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
        
        self.right_frame = tk.Frame(self.root, width=300)
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
        
        # Context display
        self.context_frame = tk.LabelFrame(self.right_frame, text="Current Context")
        self.context_frame.pack(fill=tk.BOTH, expand=True)
        
        self.context_display = scrolledtext.ScrolledText(self.context_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.context_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.refresh_context_button = tk.Button(self.context_frame, text="Refresh Context", command=self.refresh_context)
        self.refresh_context_button.pack(pady=5)
        
        # Add a system message to start
        self.add_message("System", "Welcome to ClippyPour Context Establishment. How can I help you today?")
        
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
/context - Show the current context
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
            
            self.browser_initialized = True
            self.add_message("System", "Browser initialized successfully.")
        except Exception as e:
            self.add_message("System", f"Error initializing browser: {str(e)}")
    
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


class EstablishContext:
    """
    Main class for establishing context and filling forms.
    """
    def __init__(self, storage_path: str = "context_storage.json"):
        """
        Initialize the EstablishContext.
        
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
    establish_context = EstablishContext()
    await establish_context.run()


if __name__ == "__main__":
    # Run the application
    asyncio.run(main())
