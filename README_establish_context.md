# ClippyPour Context Establishment

This module provides tools for establishing context and filling forms using ClippyPour. It includes two main components:

1. **EstablishContext**: Basic context establishment without computer vision
2. **EstablishContextCV**: Advanced context establishment with computer vision capabilities

## Features

### Common Features

- **Context Management**: Store and retrieve data from persistent memory (JSON)
- **Chat Interface**: Interact with the application through a chat-like interface
- **File Upload**: Upload files and store their content in the context
- **Clipboard Integration**: Load clipboard content and parse it if it contains delimiters
- **Browser Integration**: Initialize a browser and interact with web pages

### Computer Vision Features (EstablishContextCV only)

- **Screenshot Capture**: Take screenshots of web pages
- **Element Finding**: Find elements on a page using computer vision and natural language descriptions
- **Element Verification**: Verify that elements exist and get their attributes
- **Form Filling**: Stream clipboard fields into multiple form fields

## Installation

1. Ensure you have Python 3.8+ installed
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

#### Basic Version (without Computer Vision)

```bash
python run_establish_context.py
```

#### Advanced Version (with Computer Vision)

```bash
python run_establish_context_cv.py
```

### Chat Commands

#### Common Commands

- `/help`: Show available commands
- `/goto [url]`: Navigate to a URL in the browser
- `/fill [selector]`: Fill a form field with clipboard content
- `/click [selector]`: Click an element in the browser
- `/context`: Show the current context

#### Computer Vision Commands (EstablishContextCV only)

- `/screenshot`: Take a screenshot of the current page
- `/find [description]`: Find an element by description using computer vision
- `/verify [selector]`: Verify that an element exists and get its attributes
- `/stream [selectors...]`: Stream clipboard fields into multiple selectors

### Using Clipboard Delimiters

You can prepare clipboard content with delimiters to fill multiple form fields at once:

1. Copy text with fields separated by `||` (e.g., `Field1||Field2||Field3`)
2. Use the "Load Clipboard" button to parse the fields
3. Use the `/stream` command with multiple selectors to fill the fields

Example:
```
/stream #field1 #field2 #field3
```

## Development

### Project Structure

- `clippypour/establish_context.py`: Basic context establishment implementation
- `clippypour/establish_context_cv.py`: Advanced context establishment with computer vision
- `run_establish_context.py`: Runner script for the basic version
- `run_establish_context_cv.py`: Runner script for the advanced version
- `tests/test_establish_context_cv.py`: Tests for the EstablishContextCV module

### Running Tests

```bash
pytest tests/test_establish_context_cv.py
```

## How It Works

1. **Context Management**: The `ContextManager` class handles storing and retrieving data from a JSON file
2. **UI**: The `ClippyPourUI` class provides a chat interface for interacting with the application
3. **Browser Integration**: The application uses the `browser_use` module to interact with web pages
4. **Computer Vision**: The `ComputerVisionHelper` class uses LLMs to analyze screenshots and find elements

## Example Workflow

1. Start the application
2. Initialize the browser using the "Initialize Browser" button
3. Navigate to a web page using `/goto [url]`
4. Find form fields using `/find [description]` (CV version only)
5. Prepare clipboard content with fields separated by `||`
6. Load the clipboard using the "Load Clipboard" button
7. Fill the form fields using `/stream [selectors...]`

## Troubleshooting

- **Browser Initialization**: If the browser fails to initialize, check that you have a compatible browser installed
- **Element Not Found**: If an element is not found, try using a more specific description or selector
- **Form Filling**: If form filling fails, check that the selector is correct and the field is visible and enabled
