const elements = {
    chat: {
        container: document.getElementById('chatContainer'),
        box: document.getElementById('chatbox'),
        input: document.getElementById('userInput'),
        sendBtn: document.getElementById('sendBtn'),
        features: document.querySelectorAll('.feature-item')
    },
    todo: {
        panel: document.getElementById('todoPanel'),
        toggleBtn: document.getElementById('todoToggleBtn'),
        input: document.getElementById('taskInput'),
        addBtn: document.getElementById('addTaskBtn'),
        list: document.getElementById('taskList'),
        counter: document.getElementById('taskCount'),
        clearBtn: document.getElementById('clearCompletedBtn'),
        filters: document.querySelectorAll('.filter-btn')
    }
};

// App State
const state = {
    tasks: JSON.parse(localStorage.getItem('tasks')) || [],
    filter: 'all',
    isTyping: false
};

// Initialize the app
function init() {
    loadTodoList();
    setupEventListeners();
}

function loadTodoList() {
    renderTasks();
    updateTaskCounter();
}

function setupEventListeners() {
    // Chat functionality
    elements.chat.sendBtn.addEventListener('click', handleSendMessage);
    elements.chat.input.addEventListener('keypress', e => e.key === 'Enter' && handleSendMessage());
    elements.chat.features?.forEach(item => {
        item.addEventListener('click', () => {
            elements.chat.input.value = item.dataset.query;
            handleSendMessage();
        });
    });

    // Todo functionality
    elements.todo.toggleBtn.addEventListener('click', toggleTodoPanel);
    elements.todo.addBtn.addEventListener('click', addNewTask);
    elements.todo.input.addEventListener('keypress', e => e.key === 'Enter' && addNewTask());
    elements.todo.clearBtn.addEventListener('click', clearCompletedTasks);
    elements.todo.filters.forEach(btn => {
        btn.addEventListener('click', () => setFilter(btn.dataset.filter));
    });
}

// ============== CHAT FUNCTIONS ==============
async function handleSendMessage() {
    const message = elements.chat.input.value.trim();
    if (!message || state.isTyping) return;

    try {
        // Add user message
        addChatMessage(message, 'user');
        elements.chat.input.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        // Get bot response
        const response = await getBotResponse(message);
        addChatMessage(response.reply, 'bot', response.links);
    } catch (error) {
        showErrorMessage(error.message);
    } finally {
        removeTypingIndicator();
    }
}

function addChatMessage(content, sender, links = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    // Function to get reliability indicator
    const getReliabilityIndicator = reliability => {
        if (!reliability || reliability >= 0.95) return '';
        
        const reliabilityClass = reliability >= 0.85 ? 'high' : reliability >= 0.7 ? 'medium' : 'low';
        return `<span class="reliability-indicator ${reliabilityClass}" title="Link reliability: ${Math.round(reliability * 100)}%">
            ${reliability >= 0.85 ? '✓' : reliability >= 0.7 ? '⚠️' : '⚠️'}
        </span>`;
    };

    // Function to detect link type and format appropriately
    const getLinkIcon = url => {
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
            return '<i class="fab fa-youtube link-icon youtube-icon"></i>';
        } else if (url.includes('w3schools')) {
            return '<i class="fas fa-code link-icon w3-icon"></i>';
        } else {
            return '<i class="fas fa-external-link-alt link-icon"></i>';
        }
    };
    
    const linksHTML = links.length ? `
        <div class="note-links">
            ${links.map(link => `
                <div class="note-link ${link.reliability < 0.85 ? 'reduced-reliability' : ''} ${link.url.includes('youtube') ? 'youtube-link' : ''}">
                    <a href="${link.url}" target="_blank">
                        ${getLinkIcon(link.url)}
                        <strong>${link.title}</strong>
                        ${getReliabilityIndicator(link.reliability)}
                    </a>
                    <p>${link.description}</p>
                </div>
            `).join('')}
        </div>
    ` : '';

    messageDiv.innerHTML = `
        <div class="message-content">
            <p>${content}</p>
            ${linksHTML}
        </div>
        <div class="message-time">
            ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
        </div>
    `;

    elements.chat.box.appendChild(messageDiv);
    scrollChatToBottom();
    
    // Add CSS for links and icons
    if (!document.getElementById('link-styles')) {
        const style = document.createElement('style');
        style.id = 'link-styles';
        style.textContent = `
            .reliability-indicator {
                margin-left: 6px;
                font-size: 12px;
                padding: 2px 4px;
                border-radius: 3px;
            }
            .reliability-indicator.high { color: #28a745; }
            .reliability-indicator.medium { color: #ffc107; }
            .reliability-indicator.low { color: #dc3545; }
            .reduced-reliability { opacity: 0.85; }
            .reduced-reliability::after {
                content: " (Reliability check: Passed)";
                font-size: 11px;
                color: #666;
            }
            .link-icon {
                margin-right: 8px;
                font-size: 16px;
            }
            .youtube-icon {
                color: #FF0000;
            }
            .w3-icon {
                color: #04AA6D;
            }
            .youtube-link {
                border-left: 4px solid #FF0000 !important;
            }
        `;
        document.head.appendChild(style);
    }
}

async function getBotResponse(message) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    try {
        const response = await fetch('http://localhost:5000/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message }),
            signal: controller.signal
        });

        clearTimeout(timeout);

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Server error');
        }

        return await response.json();
    } catch (error) {
        throw new Error(error.name === 'AbortError' ? 
            'Request timed out' : 
            'Failed to get response');
    }
}

// ============== TODO FUNCTIONS ==============
function addNewTask() {
    const text = elements.todo.input.value.trim();
    if (!text) return;

    state.tasks.push({
        id: Date.now(),
        text,
        completed: false,
        createdAt: new Date()
    });

    saveTasks();
    renderTasks();
    elements.todo.input.value = '';
}

function toggleTaskStatus(id) {
    state.tasks = state.tasks.map(task => 
        task.id === id ? {...task, completed: !task.completed} : task
    );
    saveTasks();
    renderTasks();
}

function deleteTask(id) {
    state.tasks = state.tasks.filter(task => task.id !== id);
    saveTasks();
    renderTasks();
}

function clearCompletedTasks() {
    state.tasks = state.tasks.filter(task => !task.completed);
    saveTasks();
    renderTasks();
}

function setFilter(filter) {
    state.filter = filter;
    elements.todo.filters.forEach(btn => 
        btn.classList.toggle('active', btn.dataset.filter === filter)
    );
    renderTasks();
}

function renderTasks() {
    elements.todo.list.innerHTML = '';

    const filteredTasks = state.tasks.filter(task => 
        state.filter === 'all' || 
        (state.filter === 'active' && !task.completed) ||
        (state.filter === 'completed' && task.completed)
    );

    filteredTasks.sort((a, b) => b.createdAt - a.createdAt);

    filteredTasks.forEach(task => {
        const taskEl = document.createElement('li');
        taskEl.className = `task-item ${task.completed ? 'completed' : ''}`;
        taskEl.innerHTML = `
            <input type="checkbox" class="task-checkbox" ${task.completed ? 'checked' : ''}>
            <span class="task-text">${task.text}</span>
            <button class="delete-task">
                <i class="fas fa-trash-alt"></i>
            </button>
        `;

        taskEl.querySelector('.task-checkbox').addEventListener('change', 
            () => toggleTaskStatus(task.id));
        taskEl.querySelector('.delete-task').addEventListener('click', 
            () => deleteTask(task.id));

        elements.todo.list.appendChild(taskEl);
    });

    updateTaskCounter();
}

// ============== UTILITY FUNCTIONS ==============
function showTypingIndicator() {
    state.isTyping = true;
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-content">
            <p>Searching....
                <span class="dots">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </span>
            </p>
        </div>
    `;
    elements.chat.box.appendChild(typingDiv);
    scrollChatToBottom();
}

function removeTypingIndicator() {
    state.isTyping = false;
    document.querySelector('.typing-indicator')?.remove();
}

function showErrorMessage(message) {
    addChatMessage(`Error: ${message}`, 'bot');
}

function scrollChatToBottom() {
    elements.chat.container.scrollTop = elements.chat.container.scrollHeight;
}

function toggleTodoPanel() {
    elements.todo.panel.classList.toggle('collapsed');
}

function updateTaskCounter() {
    const count = state.tasks.filter(t => !t.completed).length;
    elements.todo.counter.textContent = `${count} task${count !== 1 ? 's' : ''} left`;
}

function saveTasks() {
    localStorage.setItem('tasks', JSON.stringify(state.tasks));
    updateTaskCounter();
}

// Initialize the app
document.addEventListener('DOMContentLoaded', init);
// Autocomplete Integration (added to existing code)
document.addEventListener('DOMContentLoaded', function() {
    // Create autocomplete list container
    const autocompleteList = document.createElement('div');
    autocompleteList.className = 'autocomplete-list';
    autocompleteList.style.cssText = `
        position: absolute;
        z-index: 100;
        width: calc(100% - 30px);
        max-height: 200px;
        overflow-y: auto;
        background: white;
        border-radius: 0 0 10px 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        margin-top: 5px;
        display: none;
    `;
    document.querySelector('.input-container').appendChild(autocompleteList);

    // Sort names in ascending order
    const sortedNames = [
        "App", "html", "perl", "c++", "c", "sql", "java",
        "css", "javascript", "fsharp", "Averest","AWK","axum", "bash", "cython", "dataflex",
        "emerald", "Game Maker Language", "Google Apps Script", "IDL", "JavaFX Script", "Machine code",
        "PowerShell", "Qalb", "Wyvern", "Z++", "YQL", "Python","react","UNITY","kotlin"
    ].sort();

    // Reference to input
    const input = document.getElementById("userInput");

    // Execute function on keyup
    input.addEventListener("keyup", (e) => {
        // Initially remove all elements
        removeElements();
        for (let i of sortedNames) {
            // Convert input to lowercase and compare with each string
            if (i.toLowerCase().startsWith(input.value.toLowerCase()) && input.value != "") {
                // Create div element (using div instead of li for better compatibility)
                let listItem = document.createElement("div");
                listItem.className = "list-items";
                listItem.style.cssText = `
                    padding: 10px 15px;
                    cursor: pointer;
                    transition: background-color 0.2s;
                `;
                listItem.addEventListener("click", function() {
                    input.value = i;
                    removeElements();
                });
                
                // Display matched part in bold
                let word = "<b>" + i.substr(0, input.value.length) + "</b>";
                word += i.substr(input.value.length);
                listItem.innerHTML = word;
                autocompleteList.appendChild(listItem);
                autocompleteList.style.display = "block";
            }
        }
    });

    function removeElements() {
        autocompleteList.style.display = "none";
        while (autocompleteList.firstChild) {
            autocompleteList.removeChild(autocompleteList.firstChild);
        }
    }

    // Close autocomplete when clicking outside
    document.addEventListener("click", function(e) {
        if (e.target !== input) {
            removeElements();
        }
    });
});