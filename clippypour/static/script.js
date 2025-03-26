document.addEventListener('DOMContentLoaded', function() {
    // Add selector button
    document.getElementById('addSelector').addEventListener('click', function() {
        const selectorsDiv = document.getElementById('selectors');
        const newGroup = document.createElement('div');
        newGroup.className = 'selector-group';
        newGroup.innerHTML = `
            <input type="text" class="form-control" name="selectors[]" required placeholder="#field">
            <button type="button" class="btn btn-danger remove-selector">-</button>
        `;
        selectorsDiv.appendChild(newGroup);
    });
    
    // Remove selector button
    document.getElementById('selectors').addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-selector')) {
            const selectorsDiv = document.getElementById('selectors');
            if (selectorsDiv.children.length > 1) {
                e.target.parentElement.remove();
            }
        }
    });
    
    // Form submission
    document.getElementById('fillForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formUrl = document.getElementById('formUrl').value;
        const formData = document.getElementById('formData').value;
        const headless = document.getElementById('headless').checked;
        
        const selectorInputs = document.querySelectorAll('input[name="selectors[]"]');
        const selectors = Array.from(selectorInputs).map(input => input.value);
        
        // Validate that the number of fields matches the number of selectors
        const fields = formData.split('||');
        if (fields.length !== selectors.length) {
            showResult(`Error: Number of fields (${fields.length}) does not match number of selectors (${selectors.length}).`, false);
            return;
        }
        
        // Disable form during submission
        const submitButton = this.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';
        
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
        })
        .catch(error => {
            showResult(`Error: ${error.message}`, false);
        })
        .finally(() => {
            // Re-enable the form
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        });
    });
    
    function showResult(message, success) {
        const resultDiv = document.getElementById('result');
        resultDiv.textContent = message;
        resultDiv.className = success ? 'success' : 'error';
        resultDiv.style.display = 'block';
    }
});