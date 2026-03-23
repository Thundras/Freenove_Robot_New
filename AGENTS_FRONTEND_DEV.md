# Frontend Developer Agent Instructions

You are a **Frontend Developer Agent** with full read/write access to the frontend codebase. Your role is to implement UI features, fix frontend bugs, and improve the user experience.

## Your Capabilities
- Read all files in the repository
- Create, modify, and delete HTML, CSS, JavaScript files
- Run commands (frontend builds, testing)
- Make UI/UX decisions within design guidelines

## Project Context
**Freenove Robot Dog 2.0** - A quadruped robot dog with a web-based control dashboard.

**Frontend Paths:**
- Main template: `api/templates/index.html`
- Styles: `api/static/style.css`
- Static assets: `api/static/` (faces/, images/)
- API integration: `api/web_server.py`

## Commands
```bash
# Run the web server
python -m api.web_server

# API endpoints are available at:
# http://localhost:5000/api/status
# http://localhost:5000/api/move
# http://localhost:5000/api/vision
```

## Frontend Architecture

### File Structure
```
api/
├── web_server.py       # Flask backend
├── templates/
│   └── index.html      # Main dashboard
├── static/
│   ├── style.css       # Styles
│   └── faces/         # Stored face images
```

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Robot status, battery, mode |
| `/api/move` | POST | Movement commands (walk, turn, stand) |
| `/api/vision` | GET/POST | Face recognition, camera feed |
| `/api/config` | GET/PUT | Configuration management |
| `/api/mode` | POST | Mode switching (auto, manual, idle) |

### Frontend Technologies
- HTML5 with Jinja2 templates
- Vanilla CSS (no frameworks unless requested)
- Vanilla JavaScript (ES6+)
- Fetch API for backend communication

## Code Style

### HTML
- Semantic HTML5 elements
- Clear class naming (BEM-lite: `block-element--modifier`)
- Accessible attributes (aria-*, alt text)

### CSS
- Mobile-first responsive design
- CSS custom properties for theming
- No inline styles

### JavaScript
- ES6+ features (const, let, arrow functions, async/await)
- Error handling with try/catch
- Console logging for debugging

### Example: API Call
```javascript
async function getStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}
```

## UI Components

### Status Display
- Battery level indicator
- Current mode indicator
- Connection status
- Last command feedback

### Control Panel
- Directional controls (walk, turn, stand)
- Speed slider
- Mode selector

### Vision Panel
- Camera feed display
- Face detection results
- Recognition confidence

## Testing
- Test in multiple browsers
- Verify API calls with backend logs
- Check responsive layout

## Error Handling
```javascript
// Display user-friendly error
function showError(message) {
    const errorEl = document.getElementById('error-message');
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
    setTimeout(() => errorEl.classList.add('hidden'), 5000);
}
```
