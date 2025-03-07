import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig

# Load environment variables from .env file
load_dotenv()

async def clippy_dollop_fill_form(form_url: str, form_data: str, field_selectors: list[str]) -> None:
    """
    Fill out a web form by streaming the provided form data into its fields.
    
    Args:
        form_url (str): URL of the form page.
        form_data (str): Clipboard text containing all form fields separated by the delimiter "||".
        field_selectors (list[str]): List of CSS selectors for each form field (in order).
    """
    # Initialize a browser instance using Browser-use's Browser with a custom configuration.
    browser_config = BrowserConfig(headless=False)
    browser = Browser(config=browser_config)
    
    # Create an Agent instance with a dummy task description.
    task = "Fill out the form with the provided data using clippy-dollop method."
    llm = ChatOpenAI(model="gpt-4o")
    agent = Agent(task=task, llm=llm, browser=browser)
    
    # Navigate to the form URL.
    await agent.browser_context.navigate_to(form_url)
    await asyncio.sleep(2)  # Allow time for the page to load completely.
    
    # Split the form data using the delimiter "||"
    fields = form_data.split("||")
    if len(fields) != len(field_selectors):
        print("Error: Number of fields does not match number of selectors.")
        await browser.close()
        return

    # Fill each form field sequentially.
    for i, selector in enumerate(field_selectors):
        text = fields[i].strip()
        print(f"Filling field {i+1} with: {text}")
        page = await agent.browser_context.get_current_page()
        await page.fill(selector, text)
        await asyncio.sleep(0.5)  # Simulate a short typing delay.

    print("Form filling complete.")
    await browser.close()

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
