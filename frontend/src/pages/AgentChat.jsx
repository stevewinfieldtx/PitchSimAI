import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { ArrowLeft, Send, User, Bot } from 'lucide-react';

export default function AgentChat() {
  const { id: simulationId, personaId } = useParams();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [persona, setPersona] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Load persona info and chat history
    Promise.all([
      api.getSimulationResponses(simulationId),
      api.getChatHistory(simulationId, personaId),
    ]).then(([responses, history]) => {
      const p = responses.find(r => r.persona_id === personaId);
      if (p) {
        setPersona(p);
        // Add initial reaction as first message if no history
        if (!history.messages?.length) {
          setMessages([{
            role: 'assistant',
            content: p.initial_reaction || 'Hello, I reviewed your pitch. What would you like to discuss?',
          }]);
        } else {
          setMessages(history.messages);
        }
      }
    }).catch(console.error);
  }, [simulationId, personaId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setSending(true);

    try {
      const response = await api.sendChatMessage(simulationId, personaId, userMessage);
      setMessages(prev => [...prev, { role: 'assistant', content: response.response }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center gap-4 pb-4 border-b border-gray-200">
        <Link to={`/simulation/${simulationId}`} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-50 rounded-full">
            <Bot className="h-5 w-5 text-primary-600" />
          </div>
          <div>
            <h2 className="font-semibold">{persona?.persona_name || 'Loading...'}</h2>
            <p className="text-sm text-gray-500">{persona?.persona_title} · {persona?.industry}</p>
          </div>
        </div>
        {persona && (
          <span className={`ml-auto text-sm font-medium px-2 py-0.5 rounded-full ${
            persona.sentiment?.includes('positive') ? 'bg-green-50 text-green-700' :
            persona.sentiment === 'neutral' ? 'bg-yellow-50 text-yellow-700' :
            'bg-red-50 text-red-700'
          }`}>{persona.sentiment} · {persona.engagement_score?.toFixed(0)}/100</span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
              <div className="p-1.5 bg-primary-50 rounded-full h-fit">
                <Bot className="h-4 w-4 text-primary-600" />
              </div>
            )}
            <div className={`max-w-[70%] px-4 py-2.5 rounded-2xl text-sm ${
              msg.role === 'user'
                ? 'bg-primary-600 text-white rounded-br-sm'
                : 'bg-gray-100 text-gray-800 rounded-bl-sm'
            }`}>
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="p-1.5 bg-gray-200 rounded-full h-fit">
                <User className="h-4 w-4 text-gray-600" />
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="flex gap-3">
            <div className="p-1.5 bg-primary-50 rounded-full h-fit">
              <Bot className="h-4 w-4 text-primary-600" />
            </div>
            <div className="bg-gray-100 px-4 py-2.5 rounded-2xl rounded-bl-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 pt-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about their concerns, test responses..."
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="bg-primary-600 text-white p-2.5 rounded-xl hover:bg-primary-700 transition disabled:opacity-50"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
