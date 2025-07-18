// Check authentication on page load
checkAuth();

// Get DOM elements
const chatMessages = document.getElementById('chatMessages');
const questionInput = document.getElementById('questionInput');
const sendButton = document.getElementById('sendQuestion');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');

// Add message to chat
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = role === 'user' ? 'bg-blue-50 p-3 rounded-lg' : 'bg-green-50 p-3 rounded-lg';
    // Replace newlines with <br> for assistant
    if (role === 'assistant') {
        content = content.replace(/\n/g, '<br>');
    }
    messageDiv.innerHTML = `<p class="text-${role === 'user' ? 'blue' : 'green'}-800">${content}</p>`;
    chatMessages.querySelector('.space-y-4').appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return messageDiv;
}

// Send question to backend (streaming)
async function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;

    try {
        // Disable input while processing
        questionInput.disabled = true;
        sendButton.disabled = true;
        errorSection.classList.add('hidden');

        // Add user message to chat
        addMessage('user', question);
        questionInput.value = '';

        // Add placeholder for assistant's streaming response
        const assistantDiv = addMessage('assistant', '');
        let answer = '';

        // Send question to backend (streaming)
        const response = await fetch('/api/qa', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ question })
        });

        if (!response.ok || !response.body) {
            // Try to read the error message from the stream
            let errorMsg = 'Failed to get answer';
            if (response.body) {
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let errorText = '';
                let done = false;
                while (!done) {
                    const { value, done: doneReading } = await reader.read();
                    done = doneReading;
                    if (value) {
                        errorText += decoder.decode(value, { stream: true });
                    }
                }
                if (errorText) errorMsg = errorText;
            }
            throw new Error(errorMsg);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let done = false;
        while (!done) {
            const { value, done: doneReading } = await reader.read();
            done = doneReading;
            if (value) {
                answer += decoder.decode(value, { stream: true });
                assistantDiv.innerHTML = `<p class="text-green-800">${answer.replace(/\n/g, '<br>')}</p>`;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }
        // Final update
        assistantDiv.innerHTML = `<p class="text-green-800">${answer.trim().replace(/\n/g, '<br>')}</p>`;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (error) {
        showError(error.message);
    } finally {
        questionInput.disabled = false;
        sendButton.disabled = false;
    }
}

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
}

// Event listeners
sendButton.addEventListener('click', sendQuestion);
questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendQuestion();
    }
}); 