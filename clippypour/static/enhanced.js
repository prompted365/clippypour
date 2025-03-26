/**
 * ClippyPour Enhanced JavaScript
 * Provides interactive functionality for the ClippyPour web interface
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initApp();
});

/**
 * Initialize the application
 */
function initApp() {
    // Set up event listeners
    setupEventListeners();
    
    // Initialize tabs if present
    initTabs();
    
    // Initialize dark mode toggle if present
    initDarkMode();
    
    // Check for URL parameters
    handleUrlParameters();
}

/**
 * Set up event listeners for interactive elements
 */
function setupEventListeners() {
    // Form submission
    const formElement = document.getElementById('fillForm');
    if (formElement) {
        formElement.addEventListener('submit', handleFormSubmit);
    }
    
    // Analyze form button
    const analyzeButton = document.getElementById('analyzeButton');
    if (analyzeButton) {
        analyzeButton.addEventListener('click', handleAnalyzeForm);
    }
    
    // Add selector button
    const addSelectorButton = document.getElementById('addSelector');
    if (addSelectorButton) {
        addSelectorButton.addEventListener('click', addSelectorField);
    }
    
    // Remove selector buttons (delegated event)
    const selectorsContainer = document.getElementById('selectors');
    if (selectorsContainer) {
        selectorsContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-selector')) {
                removeSelector(e.target);
            }
        });
    }
    
    // Clipboard paste button
    const pasteButton = document.getElementById('pasteClipboard');
    if (pasteButton) {
        pasteButton.addEventListener('click', handleClipboardPaste);
    }
    
    // Save template button
    const saveTemplateButton = document.getElementById('saveTemplate');
    if (saveTemplateButton) {
        saveTemplateButton.addEventListener('click', handleSaveTemplate);
    }
    
    // Template cards (delegated event)
    const templatesContainer = document.getElementById('templatesContainer');
    if (templatesContainer) {
        templatesContainer.addEventListener('click', function(e) {
            const templateCard = e.target.closest('.template-card');
            if (templateCard) {
                const templateId = templateCard.dataset.templateId;
                loadTemplate(templateId);
            }
        });
    }
    
    // Delete template buttons (delegated event)
    if (templatesContainer) {
        templatesContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('delete-template')) {
                e.stopPropagation(); // Prevent template card click
                const templateId = e.target.closest('.template-card').dataset.templateId;
                deleteTemplate(templateId);
            }
        });
    }
    
    // Visual selector button
    const visualSelectorButton = document.getElementById('visualSelector');
    if (visualSelectorButton) {
        visualSelectorButton.addEventListener('click', activateVisualSelector);
    }
}

/**
 * Handle form submission
 * @param {Event} e - The submit event
 */
function handleFormSubmit(e) {
    e.preventDefault();
    
    // Show loading indicator
    showLoading();
    
    // Get form data
    const formUrl = document.getElementById('formUrl').value;
    const formData = document.getElementById('formData').value;
    const headless = document.getElementById('headless')?.checked || false;
    
    // Get selectors
    const selectorInputs = document.querySelectorAll('input[name="selectors[]"]');
    const selectors = Array.from(selectorInputs).map(input => input.value);
    
    // Validate that the number of fields matches the number of selectors
    const fields = formData.split('||');
    if (fields.length !== selectors.length) {
        showResult(`Error: Number of fields (${fields.length}) does not match number of selectors (${selectors.length}).`, false);
        hideLoading();
        return;
    }
    
    // Send the request
    fetch('/api/fill-form', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            formUrl,
            formData,
            selectors,
            headless
        })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.success);
        
        // If successful, offer to save as template
        if (data.success) {
            const saveTemplateSection = document.getElementById('saveTemplateSection');
            if (saveTemplateSection) {
                saveTemplateSection.style.display = 'block';
            }
        }
    })
    .catch(error => {
        showResult(`Error: ${error.message}`, false);
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Handle analyze form button click
 */
function handleAnalyzeForm() {
    // Show loading indicator
    showLoading();
    
    // Get form URL
    const formUrl = document.getElementById('formUrl').value;
    
    if (!formUrl) {
        showResult('Please enter a form URL to analyze.', false);
        hideLoading();
        return;
    }
    
    // Send the request
    fetch('/api/analyze-form', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            formUrl
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Display the form analysis results
            displayFormAnalysis(data.analysis);
            showResult('Form analyzed successfully.', true);
        } else {
            showResult(`Error analyzing form: ${data.message}`, false);
        }
    })
    .catch(error => {
        showResult(`Error: ${error.message}`, false);
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Display form analysis results
 * @param {Object} analysis - The form analysis data
 */
function displayFormAnalysis(analysis) {
    const formAnalysisSection = document.getElementById('formAnalysisSection');
    if (!formAnalysisSection) return;
    
    // Show the section
    formAnalysisSection.style.display = 'block';
    
    // Get the container for form details
    const formDetails = document.getElementById('formDetails');
    if (!formDetails) return;
    
    // Clear previous content
    formDetails.innerHTML = '';
    
    // Display page title and URL
    const titleElement = document.createElement('h3');
    titleElement.textContent = analysis.title || 'Untitled Page';
    formDetails.appendChild(titleElement);
    
    const urlElement = document.createElement('p');
    urlElement.textContent = analysis.url;
    urlElement.className = 'text-muted';
    formDetails.appendChild(urlElement);
    
    // If no forms found
    if (!analysis.forms || analysis.forms.length === 0) {
        const noFormsMessage = document.createElement('div');
        noFormsMessage.className = 'alert alert-warning';
        noFormsMessage.textContent = 'No forms detected on the page.';
        formDetails.appendChild(noFormsMessage);
        return;
    }
    
    // Create form selector if multiple forms
    if (analysis.forms.length > 1) {
        const formSelectorContainer = document.createElement('div');
        formSelectorContainer.className = 'form-selector';
        
        const formSelectorLabel = document.createElement('label');
        formSelectorLabel.textContent = 'Select a form:';
        formSelectorLabel.className = 'form-label';
        formSelectorContainer.appendChild(formSelectorLabel);
        
        const formSelector = document.createElement('select');
        formSelector.className = 'form-control';
        formSelector.id = 'formSelector';
        
        analysis.forms.forEach((form, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = `Form ${index + 1}: ${form.purpose || 'Unknown purpose'}`;
            formSelector.appendChild(option);
        });
        
        formSelectorContainer.appendChild(formSelector);
        formDetails.appendChild(formSelectorContainer);
        
        // Add event listener to form selector
        formSelector.addEventListener('change', function() {
            const selectedFormIndex = parseInt(this.value);
            displayFormFields(analysis.forms[selectedFormIndex]);
        });
    }
    
    // Display the first form's fields
    displayFormFields(analysis.forms[0]);
    
    // Update the form URL in the main form if it's empty
    const formUrlInput = document.getElementById('formUrl');
    if (formUrlInput && !formUrlInput.value) {
        formUrlInput.value = analysis.url;
    }
}

/**
 * Display form fields from analysis
 * @param {Object} form - The form data
 */
function displayFormFields(form) {
    const formFieldsContainer = document.getElementById('formFields');
    if (!formFieldsContainer) return;
    
    // Clear previous content
    formFieldsContainer.innerHTML = '';
    
    // Display form purpose
    const purposeElement = document.createElement('div');
    purposeElement.className = 'alert alert-info';
    purposeElement.innerHTML = `<strong>Form Purpose:</strong> ${form.purpose || 'Unknown'}`;
    formFieldsContainer.appendChild(purposeElement);
    
    // Create table for fields
    const table = document.createElement('table');
    table.className = 'table';
    
    // Create table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    ['Field', 'Type', 'Selector', 'Suggested Data'].forEach(text => {
        const th = document.createElement('th');
        th.textContent = text;
        headerRow.appendChild(th);
    });
    
    const actionsHeader = document.createElement('th');
    actionsHeader.textContent = 'Actions';
    headerRow.appendChild(actionsHeader);
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Create table body
    const tbody = document.createElement('tbody');
    
    form.fields.forEach(field => {
        const row = document.createElement('tr');
        
        // Field name/label
        const nameCell = document.createElement('td');
        nameCell.textContent = field.label || field.name || 'Unnamed Field';
        row.appendChild(nameCell);
        
        // Field type
        const typeCell = document.createElement('td');
        typeCell.textContent = field.type || 'text';
        row.appendChild(typeCell);
        
        // Field selector
        const selectorCell = document.createElement('td');
        selectorCell.textContent = field.selector;
        row.appendChild(selectorCell);
        
        // Suggested data type
        const suggestedCell = document.createElement('td');
        suggestedCell.textContent = field.suggested_data_type || 'Unknown';
        row.appendChild(suggestedCell);
        
        // Actions
        const actionsCell = document.createElement('td');
        
        const useButton = document.createElement('button');
        useButton.textContent = 'Use';
        useButton.className = 'btn btn-sm btn-primary';
        useButton.addEventListener('click', function() {
            addSelectorWithValue(field.selector);
        });
        
        actionsCell.appendChild(useButton);
        row.appendChild(actionsCell);
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    formFieldsContainer.appendChild(table);
    
    // Add "Use All Fields" button
    const useAllButton = document.createElement('button');
    useAllButton.textContent = 'Use All Fields';
    useAllButton.className = 'btn btn-primary';
    useAllButton.addEventListener('click', function() {
        // Clear existing selectors
        const selectorsContainer = document.getElementById('selectors');
        if (selectorsContainer) {
            selectorsContainer.innerHTML = '';
        }
        
        // Add all fields
        form.fields.forEach(field => {
            addSelectorWithValue(field.selector);
        });
        
        // Suggest clipboard format
        suggestClipboardFormat(form.fields);
    });
    
    formFieldsContainer.appendChild(useAllButton);
}

/**
 * Suggest clipboard format based on form fields
 * @param {Array} fields - The form fields
 */
function suggestClipboardFormat(fields) {
    const formDataInput = document.getElementById('formData');
    if (!formDataInput) return;
    
    // Create a suggested format with field names
    const fieldNames = fields.map(field => {
        return field.label || field.name || 'Field';
    });
    
    const suggestion = fieldNames.join(' || ');
    
    // Only set if empty
    if (!formDataInput.value) {
        formDataInput.value = suggestion;
    }
    
    // Show a suggestion message
    const suggestionElement = document.getElementById('clipboardSuggestion');
    if (suggestionElement) {
        suggestionElement.textContent = `Suggested format: ${suggestion}`;
        suggestionElement.style.display = 'block';
    }
}

/**
 * Add a selector field with a specific value
 * @param {string} value - The selector value
 */
function addSelectorWithValue(value) {
    const selectorsContainer = document.getElementById('selectors');
    if (!selectorsContainer) return;
    
    const newGroup = document.createElement('div');
    newGroup.className = 'selector-group';
    newGroup.innerHTML = `
        <input type="text" class="form-control" name="selectors[]" required value="${value}">
        <button type="button" class="btn btn-danger remove-selector">-</button>
    `;
    
    selectorsContainer.appendChild(newGroup);
}

/**
 * Add a new selector field
 */
function addSelectorField() {
    const selectorsContainer = document.getElementById('selectors');
    if (!selectorsContainer) return;
    
    const newGroup = document.createElement('div');
    newGroup.className = 'selector-group';
    newGroup.innerHTML = `
        <input type="text" class="form-control" name="selectors[]" required placeholder="#field">
        <button type="button" class="btn btn-danger remove-selector">-</button>
    `;
    
    selectorsContainer.appendChild(newGroup);
}

/**
 * Remove a selector field
 * @param {Element} button - The remove button element
 */
function removeSelector(button) {
    const selectorsContainer = document.getElementById('selectors');
    if (!selectorsContainer || selectorsContainer.children.length <= 1) return;
    
    const selectorGroup = button.closest('.selector-group');
    if (selectorGroup) {
        selectorGroup.remove();
    }
}

/**
 * Handle clipboard paste button click
 */
function handleClipboardPaste() {
    // Check if clipboard API is available
    if (!navigator.clipboard || !navigator.clipboard.readText) {
        showResult('Clipboard access is not available in your browser.', false);
        return;
    }
    
    navigator.clipboard.readText()
        .then(text => {
            const formDataInput = document.getElementById('formData');
            if (formDataInput) {
                formDataInput.value = text;
                
                // If we have form analysis data, try to map the clipboard data
                const formSelector = document.getElementById('formSelector');
                if (formSelector) {
                    const selectedFormIndex = parseInt(formSelector.value);
                    const formAnalysisSection = document.getElementById('formAnalysisSection');
                    
                    if (formAnalysisSection && formAnalysisSection.style.display !== 'none') {
                        // Send request to map clipboard data to form fields
                        mapClipboardToForm(selectedFormIndex, text);
                    }
                }
            }
        })
        .catch(err => {
            showResult(`Error accessing clipboard: ${err.message}`, false);
        });
}

/**
 * Map clipboard data to form fields
 * @param {number} formIndex - The index of the form
 * @param {string} clipboardData - The clipboard data
 */
function mapClipboardToForm(formIndex, clipboardData) {
    // Show loading indicator
    showLoading();
    
    fetch('/api/map-clipboard', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            formIndex,
            clipboardData
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Clear existing selectors
            const selectorsContainer = document.getElementById('selectors');
            if (selectorsContainer) {
                selectorsContainer.innerHTML = '';
            }
            
            // Add mapped fields
            data.mapping.field_mapping.forEach(mapping => {
                addSelectorWithValue(mapping.form_field_selector);
            });
            
            showResult('Clipboard data mapped to form fields.', true);
        } else {
            showResult(`Error mapping clipboard data: ${data.message}`, false);
        }
    })
    .catch(error => {
        showResult(`Error: ${error.message}`, false);
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Handle save template button click
 */
function handleSaveTemplate() {
    const templateNameInput = document.getElementById('templateName');
    if (!templateNameInput) return;
    
    const templateName = templateNameInput.value.trim();
    if (!templateName) {
        showResult('Please enter a template name.', false);
        return;
    }
    
    // Get form data
    const formUrl = document.getElementById('formUrl').value;
    const formData = document.getElementById('formData').value;
    
    // Get selectors
    const selectorInputs = document.querySelectorAll('input[name="selectors[]"]');
    const selectors = Array.from(selectorInputs).map(input => input.value);
    
    // Show loading indicator
    showLoading();
    
    // Send the request
    fetch('/api/save-template', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: templateName,
            formUrl,
            formData,
            selectors
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showResult(`Template "${templateName}" saved successfully.`, true);
            
            // Clear the template name input
            templateNameInput.value = '';
            
            // Hide the save template section
            const saveTemplateSection = document.getElementById('saveTemplateSection');
            if (saveTemplateSection) {
                saveTemplateSection.style.display = 'none';
            }
            
            // Refresh templates list if available
            loadTemplates();
        } else {
            showResult(`Error saving template: ${data.message}`, false);
        }
    })
    .catch(error => {
        showResult(`Error: ${error.message}`, false);
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Load templates from the server
 */
function loadTemplates() {
    const templatesContainer = document.getElementById('templatesContainer');
    if (!templatesContainer) return;
    
    // Show loading indicator
    showLoading();
    
    fetch('/api/templates')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear existing templates
                templatesContainer.innerHTML = '';
                
                if (data.templates.length === 0) {
                    const noTemplatesMessage = document.createElement('div');
                    noTemplatesMessage.className = 'alert alert-info';
                    noTemplatesMessage.textContent = 'No templates found. Save a form configuration to create a template.';
                    templatesContainer.appendChild(noTemplatesMessage);
                } else {
                    // Create template cards
                    data.templates.forEach(template => {
                        const templateCard = document.createElement('div');
                        templateCard.className = 'card template-card mb-3';
                        templateCard.dataset.templateId = template.id;
                        
                        templateCard.innerHTML = `
                            <div class="card-body">
                                <h5 class="card-title">${template.name}</h5>
                                <p class="text-muted">${template.url || 'No URL'}</p>
                                <div class="template-actions">
                                    <button class="btn btn-sm btn-danger delete-template">Delete</button>
                                </div>
                            </div>
                        `;
                        
                        templatesContainer.appendChild(templateCard);
                    });
                }
            } else {
                showResult(`Error loading templates: ${data.message}`, false);
            }
        })
        .catch(error => {
            showResult(`Error: ${error.message}`, false);
        })
        .finally(() => {
            hideLoading();
        });
}

/**
 * Load a template by ID
 * @param {string} templateId - The template ID
 */
function loadTemplate(templateId) {
    // Show loading indicator
    showLoading();
    
    fetch(`/api/templates/${templateId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Fill the form with template data
                const formUrlInput = document.getElementById('formUrl');
                const formDataInput = document.getElementById('formData');
                
                if (formUrlInput) {
                    formUrlInput.value = data.template.formUrl || '';
                }
                
                if (formDataInput) {
                    formDataInput.value = data.template.formData || '';
                }
                
                // Clear existing selectors
                const selectorsContainer = document.getElementById('selectors');
                if (selectorsContainer) {
                    selectorsContainer.innerHTML = '';
                }
                
                // Add selectors from template
                if (data.template.selectors && data.template.selectors.length > 0) {
                    data.template.selectors.forEach(selector => {
                        addSelectorWithValue(selector);
                    });
                } else {
                    // Add at least one empty selector
                    addSelectorField();
                }
                
                showResult(`Template "${data.template.name}" loaded.`, true);
                
                // Switch to the Fill Form tab if available
                const fillFormTab = document.querySelector('.tab[data-tab="fillForm"]');
                if (fillFormTab) {
                    fillFormTab.click();
                }
            } else {
                showResult(`Error loading template: ${data.message}`, false);
            }
        })
        .catch(error => {
            showResult(`Error: ${error.message}`, false);
        })
        .finally(() => {
            hideLoading();
        });
}

/**
 * Delete a template by ID
 * @param {string} templateId - The template ID
 */
function deleteTemplate(templateId) {
    if (!confirm('Are you sure you want to delete this template?')) {
        return;
    }
    
    // Show loading indicator
    showLoading();
    
    fetch(`/api/templates/${templateId}`, {
        method: 'DELETE'
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showResult('Template deleted successfully.', true);
                
                // Refresh templates list
                loadTemplates();
            } else {
                showResult(`Error deleting template: ${data.message}`, false);
            }
        })
        .catch(error => {
            showResult(`Error: ${error.message}`, false);
        })
        .finally(() => {
            hideLoading();
        });
}

/**
 * Activate visual selector mode
 */
function activateVisualSelector() {
    // Show loading indicator
    showLoading();
    
    fetch('/api/activate-visual-selector', {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showResult('Visual selector activated. Click on form fields in the browser.', true);
            } else {
                showResult(`Error activating visual selector: ${data.message}`, false);
            }
        })
        .catch(error => {
            showResult(`Error: ${error.message}`, false);
        })
        .finally(() => {
            hideLoading();
        });
}

/**
 * Initialize tabs functionality
 */
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    if (tabs.length === 0) return;
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Hide all tab content
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Show the corresponding tab content
            const tabId = this.dataset.tab;
            const tabContent = document.querySelector(`.tab-content[data-tab="${tabId}"]`);
            if (tabContent) {
                tabContent.classList.add('active');
            }
            
            // Load templates if templates tab is selected
            if (tabId === 'templates') {
                loadTemplates();
            }
        });
    });
    
    // Activate the first tab by default
    tabs[0].click();
}

/**
 * Initialize dark mode toggle
 */
function initDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (!darkModeToggle) return;
    
    // Check for saved preference
    const darkModeEnabled = localStorage.getItem('darkMode') === 'true';
    
    // Set initial state
    if (darkModeEnabled) {
        document.body.classList.add('dark-mode');
        darkModeToggle.checked = true;
    }
    
    // Add event listener
    darkModeToggle.addEventListener('change', function() {
        if (this.checked) {
            document.body.classList.add('dark-mode');
            localStorage.setItem('darkMode', 'true');
        } else {
            document.body.classList.remove('dark-mode');
            localStorage.setItem('darkMode', 'false');
        }
    });
}

/**
 * Handle URL parameters
 */
function handleUrlParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Check for form URL parameter
    const formUrl = urlParams.get('url');
    if (formUrl) {
        const formUrlInput = document.getElementById('formUrl');
        if (formUrlInput) {
            formUrlInput.value = formUrl;
            
            // Trigger form analysis if analyze parameter is present
            if (urlParams.get('analyze') === 'true') {
                const analyzeButton = document.getElementById('analyzeButton');
                if (analyzeButton) {
                    analyzeButton.click();
                }
            }
        }
    }
    
    // Check for template parameter
    const templateId = urlParams.get('template');
    if (templateId) {
        loadTemplate(templateId);
    }
}

/**
 * Show a result message
 * @param {string} message - The message to display
 * @param {boolean} success - Whether the operation was successful
 */
function showResult(message, success) {
    const resultDiv = document.getElementById('result');
    if (!resultDiv) return;
    
    resultDiv.textContent = message;
    resultDiv.className = success ? 'alert alert-success' : 'alert alert-danger';
    resultDiv.style.display = 'block';
    
    // Scroll to result
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Show loading indicator
 */
function showLoading() {
    let loadingOverlay = document.getElementById('loadingOverlay');
    
    if (!loadingOverlay) {
        loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'loadingOverlay';
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.innerHTML = '<div class="loading-spinner"></div>';
        document.body.appendChild(loadingOverlay);
    }
    
    loadingOverlay.style.display = 'flex';
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}