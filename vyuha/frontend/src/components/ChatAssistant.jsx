import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  Send,
  Bot,
  User,
  Sparkles,
  Clock,
  Calendar,
  Users,
  AlertCircle,
  Plus
} from 'lucide-react';
import {
  sendChatMessage,
  getFeatureFlags,
  createChatSession,
  getChatSessionMessages,
} from '../lib/api';
import './ChatAssistant.css';

const CHAT_SESSION_STORAGE_KEY = 'vyuha_chat_session_id';

const WELCOME_MESSAGE = {
    id: 1,
    type: 'bot',
    content: 'Hello! I\'m your Smart Timetable Assistant. I can help you with:\n\n• Generating timetables\n• Finding substitute teachers\n• Managing leave requests\n• Checking room availability\n• Answering scheduling questions\n\nHow can I help you today?',
    timestamp: new Date()
  };

const ChatAssistant = () => {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [assistantMode, setAssistantMode] = useState('manual');
  const [substitutionTargets, setSubstitutionTargets] = useState([]);
  const [substitutionFaculty, setSubstitutionFaculty] = useState('');
  const [sessionId, setSessionId] = useState('');
  const messagesEndRef = useRef(null);
  const navigate = useNavigate();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const loadFeatureFlags = async () => {
      try {
        const flags = await getFeatureFlags();
        const aiEnabled = flags?.ai_chat !== false;
        setAssistantMode(aiEnabled ? 'ai' : 'manual');
      } catch (err) {
        console.error('Error loading feature flags:', err);
        setAssistantMode('manual');
      }
    };

    loadFeatureFlags();
  }, []);

  useEffect(() => {
    const initSession = async () => {
      try {
        let existingSessionId = localStorage.getItem(CHAT_SESSION_STORAGE_KEY) || '';
        if (!existingSessionId) {
          const created = await createChatSession('Timetable Assistant Session');
          existingSessionId = created.session_id;
        }
        if (existingSessionId) {
          const historyRes = await getChatSessionMessages(existingSessionId, 50);
          const loaded = (historyRes.messages || []).map((msg, idx) => ({
            id: idx + 1,
            type: msg.role === 'user' ? 'user' : 'bot',
            content: msg.content,
            timestamp: new Date(),
          }));
          if (loaded.length > 0) {
            setMessages(loaded);
          }
          localStorage.setItem(CHAT_SESSION_STORAGE_KEY, existingSessionId);
          setSessionId(existingSessionId);
        }
      } catch (err) {
        console.error('Failed to initialize chat session:', err);
      }
    };

    initSession();
  }, []);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    try {
      // Connect to real backend response
      const conversationHistory = [...messages, userMessage]
        .slice(-8)
        .map((msg) => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.content,
        }));

      const response = await sendChatMessage(inputMessage, conversationHistory, {
        substitution_targets: substitutionTargets,
        substitution_faculty: substitutionFaculty,
      }, sessionId || null);
      if (response.session_id) {
        setSessionId(response.session_id);
        localStorage.setItem(CHAT_SESSION_STORAGE_KEY, response.session_id);
      }
      const replyContent = response.reply || response.response || response.message || response;
      const aiAvailable =
        typeof response.ai_enabled === 'boolean'
          ? response.ai_enabled
          : response.mode === 'ai';
      const responseMode = response.mode || (aiAvailable ? 'ai' : 'manual');
      setAssistantMode(responseMode === 'ai' ? 'ai' : 'manual');

      if (typeof replyContent === 'string' && /substitute|absent faculty/i.test(replyContent)) {
        const nextTargets = extractSubstitutionTargets(replyContent);
        if (nextTargets.length) {
          setSubstitutionTargets(nextTargets);
        }
        const absent = extractAbsentFaculty(replyContent);
        if (absent) {
          setSubstitutionFaculty(absent);
        }
      }

      setMessages(prev => [...prev, {
        id: prev.length + 1,
        type: 'bot',
        content: typeof replyContent === 'string' ? replyContent : JSON.stringify(replyContent),
        timestamp: new Date()
      }]);
    } catch (error) {
      console.error('Chat error:', error);
      setAssistantMode('manual');
      setSubstitutionTargets([]);
      setMessages(prev => [...prev, {
        id: prev.length + 1,
        type: 'bot',
        content: 'I could not process that request. Try again with a teacher name, day, time, or replacement teacher.',
        timestamp: new Date()
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const quickActions = [
    { icon: Calendar, label: 'Generate Timetable', action: 'Generate a new timetable for semester 5' },
    { icon: Users, label: 'Find Substitute', action: 'Find a substitute for tomorrow' },
    { icon: Clock, label: 'Check Schedule', action: 'Show me today\'s schedule' },
    { icon: AlertCircle, label: 'View Conflicts', action: 'Are there any scheduling conflicts?' }
  ];

  const handleQuickAction = (action) => {
    setInputMessage(action);
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const extractSubstitutionTargets = (text) => {
    let absentFaculty = '';
    const absentMatch = String(text || '').match(/Absent faculty:\s*\*\*([^*]+)\*\*/i);
    if (absentMatch) {
      absentFaculty = absentMatch[1].trim().toLowerCase();
    }

    const targets = [];
    for (const line of String(text || '').split('\n')) {
      const match = line.match(/\*\*([A-Za-z][A-Za-z0-9 .'-]{1,80})\*\*/);
      if (match) {
        const name = match[1].trim();
        if (name.toLowerCase() !== absentFaculty) {
          targets.push(name);
        }
        continue;
      }

      const candidates = line.split(':').slice(1).join(':').split(',');
      for (const candidate of candidates) {
        const candidateMatch = candidate.trim().match(/^([A-Za-z][A-Za-z0-9 .'-]{1,80})\s+\(score/i);
        if (!candidateMatch) continue;
        const name = candidateMatch[1].trim();
        if (name.toLowerCase() !== absentFaculty) {
          targets.push(name);
        }
      }
    }
    return [...new Map(targets.map((name) => [name.toLowerCase(), name])).values()];
  };

  const extractAbsentFaculty = (text) => {
    const match = String(text || '').match(/Absent faculty:\s*\*\*([^*]+)\*\*/i);
    return match ? match[1].trim() : '';
  };

  const handleNewChat = async () => {
    localStorage.removeItem(CHAT_SESSION_STORAGE_KEY);
    setMessages([{ ...WELCOME_MESSAGE, id: 1, timestamp: new Date() }]);
    setSubstitutionTargets([]);
    setSubstitutionFaculty('');
    try {
      const created = await createChatSession('Timetable Assistant Session');
      if (created.session_id) {
        setSessionId(created.session_id);
        localStorage.setItem(CHAT_SESSION_STORAGE_KEY, created.session_id);
      }
    } catch (err) {
      console.error('Failed to create new session:', err);
    }
  };

  /**
   * Lightweight markdown renderer for bot messages.
   * Supports: **bold**, newlines, and - list items.
   */
  const renderMarkdown = (text) => {
    if (!text) return '';
    // Escape HTML first
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    // Bold: **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Split into lines for list handling
    const lines = html.split('\n');
    const result = [];
    let inList = false;
    for (const line of lines) {
      const trimmed = line.trim();
      if (/^[-•]\s/.test(trimmed)) {
        if (!inList) {
          result.push('<ul>');
          inList = true;
        }
        result.push(`<li>${trimmed.replace(/^[-•]\s+/, '')}</li>`);
      } else {
        if (inList) {
          result.push('</ul>');
          inList = false;
        }
        result.push(trimmed === '' ? '<br/>' : `<p>${line}</p>`);
      }
    }
    if (inList) result.push('</ul>');
    return result.join('');
  };

  return (
    <div className="chat-assistant">
      {/* Header */}
      <div className="chat-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ChevronLeft size={20} />
          Back to Dashboard
        </button>
        <div className="chat-title">
          <div className="bot-avatar">
            <Bot size={24} />
          </div>
          <div className="title-text">
            <h1>AI Assistant</h1>
            <span className="status">
              <span className="status-dot"></span>
              Assistant ready
            </span>
          </div>
        </div>
          <div className="header-actions">
            <button className="action-btn new-chat-btn" onClick={handleNewChat}>
              <Plus size={18} />
              New Chat
            </button>
            <div className={`assistant-mode-pill ${assistantMode === 'ai' ? 'ai' : 'manual'}`}>
              Substitution tools ready
            </div>
          </div>
      </div>

      {/* Chat Container */}
      <div className="chat-container">
        {/* Messages */}
        <div className="messages-area">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.type}`}
            >
              <div className="message-avatar">
                {message.type === 'bot' ? (
                  <div className="avatar-bot">
                    <Bot size={20} />
                  </div>
                ) : (
                  <div className="avatar-user">
                    <User size={20} />
                  </div>
                )}
              </div>
              <div className="message-content">
                <div className="message-bubble">
                  {message.type === 'bot' ? (
                    <div dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
                  ) : (
                    <p>{message.content}</p>
                  )}
                </div>
                <span className="message-time">{formatTime(message.timestamp)}</span>
              </div>
            </div>
          ))}
          
          {isTyping && (
            <div className="message bot typing">
              <div className="message-avatar">
                <div className="avatar-bot">
                  <Bot size={20} />
                </div>
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Actions */}
        <div className="quick-actions">
          {quickActions.map((action, index) => {
            const Icon = action.icon;
            return (
              <button
                key={index}
                className="quick-action-btn"
                onClick={() => handleQuickAction(action.action)}
              >
                <Icon size={16} />
                {action.label}
              </button>
            );
          })}
        </div>

        {/* Input Area */}

        <div className="input-area">
          <form onSubmit={handleSendMessage} className="input-form">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Type your message or ask me anything..."
              className="message-input"
            />
            <button
              type="submit"
              className="send-btn"
              disabled={!inputMessage.trim() || isTyping}
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatAssistant;
