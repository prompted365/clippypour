import asyncio
import argparse
import sys
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig

from .context_manager import ContextManager
from .ui import ClippyPourUI
from .dollop import clippy_dollop_fill_form
from .controller import ClippyPourController
from .template_manager import TemplateManager

# Load environment variables from .env file
load_dotenv()

class ClippyPour:
    """
    Main class for the ClippyPour application.
    """
    def __init__(self, storage_path: str = "context_storage.json", with_cv: bool = False):
        """
        Initialize the ClippyPour application.
        
        Args:
            storage_path (str): Path to the JSON file for persistent storage.
            with_cv (bool): Whether to include computer vision features.
        """
        self.context_manager = ContextManager(storage_path)
        self.with_cv = with_cv
        self.ui = None
    
    async def run_gui(self) -> None:
        """Run the GUI application."""
        self.ui = ClippyPourUI(self.context_manager, self.with_cv)
        self.ui.run()
    
    async def run_cli(self, form_url: str, form_data: str, field_selectors: list[str], headless: bool = False) -> None:
        """
        Run the CLI application to fill a form.
        
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
        
        # Initialize a browser instance
        browser_config = BrowserConfig(headless=headless)
        browser = Browser(config=browser_config)
        
        # Create an Agent instance with a task description and our custom controller
        task = "Fill out the form with the provided data using clippy-dollop method."
        llm = ChatOpenAI(model="gpt-4o")
        agent = Agent(task=task, llm=llm, browser=browser, controller=controller)
        
        try:
            # Use the clippy_dollop_fill_form function
            await clippy_dollop_fill_form(form_url, form_data, field_selectors, headless)
        finally:
            # Close the browser
            await browser.close()
    
    async def close(self) -> None:
        """Close the application."""
        if self.ui:
            await self.ui.close()


def main_gui():
    """Entry point for the GUI application."""
    parser = argparse.ArgumentParser(description="ClippyPour - AI-driven form-filling automation system")
    parser.add_argument("--storage", type=str, default="context_storage.json", help="Path to the context storage JSON file")
    parser.add_argument("--cv", action="store_true", help="Enable computer vision features")
    
    args = parser.parse_args()
    
    app = ClippyPour(storage_path=args.storage, with_cv=args.cv)
    asyncio.run(app.run_gui())


def main_cli():
    """Entry point for the CLI application."""
    parser = argparse.ArgumentParser(description="ClippyPour CLI - Fill forms from the command line")
    parser.add_argument("--url", type=str, required=True, help="URL of the form page")
    parser.add_argument("--data", type=str, required=True, help="Form data with fields separated by '||'")
    parser.add_argument("--selectors", type=str, nargs="+", required=True, help="CSS selectors for each form field (in order)")
    parser.add_argument("--headless", action="store_true", help="Run the browser in headless mode")
    
    args = parser.parse_args()
    
    asyncio.run(clippy_dollop_fill_form(args.url, args.data, args.selectors, args.headless))


def main_web():
    """Entry point for the web application."""
    from .web_app import create_app
    
    parser = argparse.ArgumentParser(description="ClippyPour Web - Smart form filling automation")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=12000, help="Port to bind the server to")
    parser.add_argument("--debug", action="store_true", help="Run the server in debug mode")
    parser.add_argument("--legacy", action="store_true", help="Use the legacy interface instead of the enhanced one")
    
    args = parser.parse_args()
    
    app = create_app()
    
    print(f"\nClippyPour is running at http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    print("Enhanced interface with smart form detection is enabled")
    print("Press Ctrl+C to stop the server\n")
    
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        sys.argv.pop(1)  # Remove the "cli" argument
        main_cli()
    elif len(sys.argv) > 1 and sys.argv[1] == "web":
        sys.argv.pop(1)  # Remove the "web" argument
        main_web()
    else:
        main_gui()