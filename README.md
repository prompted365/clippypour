# ClippyPour

ClippyPour is an AI-driven, copy/paste free form-filling automation system that streams structured form data directly into multiple web form fields. By leveraging the robust [Browser-Use](https://github.com/browser-use/browser-use) library and Playwright, ClippyPour bypasses traditional clipboard mechanics, enabling faster and more efficient web automation.

![ClippyPour Demo](video.mp4)

## Features

- **Smart Form Detection:** AI-powered analysis automatically detects form fields and suggests mappings.
- **Visual Selector:** Point-and-click interface for selecting form fields without needing to know CSS selectors.
- **Templates System:** Save and reuse form configurations for frequently visited websites.
- **Clipboard-Free Streaming:** Copy once and stream the data into several fields using a custom delimiter.
- **Efficient Form Filling:** Bypass OS clipboard limitations to fill out forms quickly.
- **Browser-Based Automation:** Built on Browser-Use's powerful Playwright interface for real browser control.
- **Multiple Interfaces:** Use the GUI, CLI, or web interface based on your needs.
- **Computer Vision Support:** Optional computer vision features for more advanced automation.

## Installation

### From PyPI (Recommended)

```bash
pip install clippypour
```

### Using uv (Faster Installation)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. It can significantly speed up the installation process:

```bash
# Install uv first
pip install uv

# Then use uv to install ClippyPour
uv pip install clippypour
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

   Standard installation:
   ```bash
   pip install -e .
   ```
   
   Or with uv for faster installation:
   ```bash
   pip install uv
   uv pip install -e .
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

### Web Application (Recommended)

Start the web server with the enhanced interface:

```bash
python -m clippypour.main web --port 12000
```

Then open your browser to http://localhost:12000

The enhanced web interface provides:
- Smart form detection and analysis
- Visual field selector
- Templates management
- Clipboard data mapping
- Dark mode support

#### Using Smart Form Detection

1. Enter the URL of the form you want to fill
2. Click "Analyze Form" to let ClippyPour detect form fields automatically
3. Review the detected fields and click "Use All Fields" to add them to your configuration
4. Paste your data in the "Form Data" field (separated by "||")
5. Click "Fill Form" to automatically fill the form

#### Using Templates

1. After successfully filling a form, you can save it as a template
2. Give your template a name and click "Save Template"
3. Access your saved templates from the "Templates" tab
4. Click on a template to load its configuration

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
