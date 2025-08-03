# Browser Agent UI Component

A professional React component that provides a terminal-style chat interface with real-time browser automation capabilities.

## Features

- ✨ Terminal-style UI with professional styling
- 🔄 Real-time WebSocket communication
- 🌐 Embedded browser automation view
- 🚀 Project creation and management
- 📱 Responsive design
- 🎨 GitHub-inspired dark theme
- ⚡ Auto-connecting WebSocket with reconnection
- 🖥️ Split-view layout (chat + browser)

## Installation

1. Copy the files to your React project:
   - `StreamingChat.jsx` - Main React component
   - `StreamingChat.css` - Complete styling

2. Install peer dependencies:
```bash
npm install react react-dom
```

## Usage

```jsx
import React from 'react';
import StreamingChat from './StreamingChat';

function App() {
  return (
    <StreamingChat
      websocketUrl="ws://localhost:8080/ws"
      defaultProvider="openai"
      defaultModel="gpt-4"
      onMessage={(data) => console.log('Received:', data)}
    />
  );
}

export default App;
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `websocketUrl` | string | required | WebSocket endpoint URL |
| `defaultProvider` | string | `'openai'` | Default AI provider |
| `defaultModel` | string | `'gpt-4'` | Default AI model |
| `onMessage` | function | optional | Callback for WebSocket messages |

## WebSocket Message Format

### Outgoing (to your backend):
```json
{
  "type": "chat_message",
  "content": "user message",
  "provider": "openai",
  "model": "gpt-4",
  "use_agents": true,
  "session_id": "session_123"
}
```

### Incoming (from your backend):
```json
{
  "type": "ai_response",
  "content": "AI response text",
  "provider": "openai",
  "model": "gpt-4",
  "browser_action": {...},
  "screenshot": "base64_image_data",
  "project_created": {...},
  "needs_browser": true
}
```

## Features Overview

### 1. Terminal Interface
- Professional terminal-style design
- User and AI message differentiation
- Provider/model badges
- Timestamps and session info

### 2. Browser Automation
- Real-time browser view with screenshots
- Auto-toggle based on `needs_browser` flag
- Minimizable browser panel
- Live connection status

### 3. Project Management
- Project creation indicators
- Project counter in header
- Project details display
- Template and file information

### 4. WebSocket Integration
- Auto-connecting WebSocket
- Reconnection on disconnect
- Connection status indicator
- Real-time message handling

## Styling

The component uses a complete CSS file (`StreamingChat.css`) with:
- GitHub-inspired dark theme
- Terminal-style fonts (Monaco, Menlo, Ubuntu Mono)
- Responsive design
- Smooth animations
- Custom scrollbars
- Professional color scheme

## Browser Compatibility

- Modern browsers with WebSocket support
- Mobile responsive design
- CSS Grid and Flexbox support required

## Customization

### Colors
The CSS uses CSS custom properties pattern. Main colors:
- Background: `#0d1117` (GitHub dark)
- Secondary: `#161b22`
- Borders: `#30363d`
- Text: `#c9d1d9`
- Accent: `#58a6ff` (blue)
- Success: `#3fb950` (green)
- Warning: `#ffa657` (orange)

### Layout
- Split-view: 50/50 chat and browser
- Full-view: 100% chat when browser hidden
- Mobile: Stacked layout

## Advanced Features

### Message Rendering
- Markdown-like formatting
- Code block support
- Bullet point detection
- Header formatting

### Browser Integration
- Base64 image display
- Screenshot handling
- Browser action indicators
- Real-time status updates

### Project Integration
- Project creation flow
- File count display
- Template information
- Status indicators

## Development

The component is self-contained with:
- No external dependencies (except React)
- Complete CSS styling included
- WebSocket handling built-in
- Error handling and reconnection

## License

MIT License - Use freely in your projects.