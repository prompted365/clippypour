# ClippyPour

ClippyPour is an AI-driven, clipboard-free form-filling automation system that streams structured form data directly into multiple web form fields. By leveraging the robust [Browser-Use](https://github.com/browser-use/browser-use) library and Playwright, ClippyPour bypasses traditional clipboard mechanics, enabling faster and more efficient web automation.

![ClippyPour Demo](video.mp4)

## Features

- **Clipboard-Free Streaming:** Copy once and stream the data into several fields using a custom delimiter.
- **Efficient Form Filling:** Bypass OS clipboard limitations to fill out forms quickly.
- **Browser-Based Automation:** Built on Browser-Use's powerful Playwright interface for real browser control.
- **Customizable Field Mapping:** Easily configure CSS selectors to target the appropriate form fields.
- **Multiple Interfaces:** Use the GUI, CLI, or web interface based on your needs.
- **Computer Vision Support:** Optional computer vision features for more advanced automation.

## Installation

### From PyPI (Recommended)

```bash
pip install clippypour
```

### From Source

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/prompted365/clippypour.git
   cd clippypour
   ```

2. **Set Up a Virtual Environment (optional but recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the Package:**

   ```bash
   pip install -e .
   ```

4. **Install Playwright Browsers:**

   ```bash
   playwright install
   ```

5. **Configure Environment Variables:**

   Create a `.env` file in the project root and add any necessary variables (e.g., API keys):

   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

### GUI Application

Launch the GUI application with:

```bash
clippypour-gui
```

For computer vision features:

```bash
clippypour-gui --cv
```

### CLI Application

Fill a form from the command line:

```bash
clippypour --url "https://example.com/form" --data "John Doe || john.doe@example.com || 123 Main St" --selectors "#name" "#email" "#address"
```

Run in headless mode:

```bash
clippypour --url "https://example.com/form" --data "John Doe || john.doe@example.com" --selectors "#name" "#email" --headless
```

### Web Application

Start the web server:

```bash
python -m clippypour.main web --port 12000
```

Then open your browser to http://localhost:12000

### Python API

```python
import asyncio
from clippypour.dollop import clippy_dollop_fill_form

async def main():
    form_url = "https://example.com/form"
    form_data = "John Doe || john.doe@example.com || 123 Main St"
    field_selectors = ["#name", "#email", "#address"]
    
    await clippy_dollop_fill_form(form_url, form_data, field_selectors)

if __name__ == "__main__":
    asyncio.run(main())
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/prompted365/clippypour.git
cd clippypour
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

## Contributing

Contributions are welcome! If you have suggestions or improvements, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

ClippyPour aims to redefine automated form filling with a seamless, clipboard-streaming approach. Enjoy and happy coding!