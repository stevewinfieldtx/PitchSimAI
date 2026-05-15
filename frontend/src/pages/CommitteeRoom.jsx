import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import {
  ArrowLeft, Send, Mic, MicOff, Volume2, VolumeX,
  Users, Bot, User, Wifi, WifiOff, Circle
} from 'lucide-react';

// ──────────────────────────────────────────────
// Color palette for persona avatars
// ──────────────────────────────────────────────
const PERSONA_COLORS = [
  { bg: 'bg-blue-100', text: 'text-blue-700', ring: 'ring-blue-300' },
  { bg: 'bg-purple-100', text: 'text-purple-700', ring: 'ring-purple-300' },
  { bg: 'bg-emerald-100', text: 'text-emerald-700', ring: 'ring-emerald-300' },
  { bg: 'bg-orange-100', text: 'text-orange-700', ring: 'ring-orange-300' },
  { bg: 'bg-rose-100', text: 'text-rose-700', ring: 'ring-rose-300' },
  { bg: 'bg-cyan-100', text: 'text-cyan-700', ring: 'ring-cyan-300' },
  { bg: 'bg-amber-100', text: 'text-amber-700', ring: 'ring-amber-300' },
  { bg: 'bg-indigo-100', text: 'text-indigo-700', ring: 'ring-indigo-300' },
];

function getPersonaColor(index) {
  return PERSONA_COLORS[index % PERSONA_COLORS.length];
}

function getInitials(name) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
}

// ──────────────────────────────────────────────
// Speech-to-Text hook (Web Speech API)
// ──────────────────────────────────────────────
function useSpeechRecognition() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      if (finalTranscript) {
        setTranscript(prev => prev + finalTranscript);
      }
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
  }, []);

  const startListening = useCallback(() => {
    if (recognitionRef.current) {
      setTranscript('');
      recognitionRef.current.start();
      setIsListening(true);
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  }, []);

  return { isListening, transcript, startListening, stopListening, setTranscript };
}

// ──────────────────────────────────────────────
// Audio playback for ElevenLabs TTS
// ──────────────────────────────────────────────
function useAudioPlayer() {
  const queueRef = useRef([]);
  const playingRef = useRef(false);
  const [isMuted, setIsMuted] = useState(false);

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0 || playingRef.current) return;

    playingRef.current = true;
    const audioBase64 = queueRef.current.shift();

    try {
      const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`);
      audio.onended = () => {
        playingRef.current = false;
        playNext();
      };
      audio.onerror = () => {
        playingRef.current = false;
        playNext();
      };
      audio.play().catch(() => {
        playingRef.current = false;
        playNext();
      });
    } catch {
      playingRef.current = false;
      playNext();
    }
  }, []);

  const enqueueAudio = useCallback((base64) => {
    if (isMuted || !base64) return;
    queueRef.current.push(base64);
    playNext();
  }, [isMuted, playNext]);

  return { enqueueAudio, isMuted, setIsMuted };
}

// ──────────────────────────────────────────────
// Main Component
// ──────────────────────────────────────────────
export default function CommitteeRoom() {
  const { id: roomId } = useParams();
  const [room, setRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [connected, setConnected] = useState(false);
  const [typingPersonas, setTypingPersonas] = useState(new Set());
  const [loading, setLoading] = useState(true);

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const personaColorMap = useRef({});

  const { isListening, transcript, startListening, stopListening, setTranscript } = useSpeechRecognition();
  const { enqueueAudio, isMuted, setIsMuted } = useAudioPlayer();

  // Assign colors to personas
  const getColor = (personaId) => {
    if (!personaColorMap.current[personaId]) {
      const idx = Object.keys(personaColorMap.current).length;
      personaColorMap.current[personaId] = getPersonaColor(idx);
    }
    return personaColorMap.current[personaId];
  };

  // Load room data
  useEffect(() => {
    api.getRoom(roomId)
      .then((data) => {
        setRoom(data);
        // Pre-load existing conversation
        if (data.conversation_history?.length) {
          setMessages(data.conversation_history);
        }
        // Pre-assign colors
        data.participants?.forEach((p, i) => {
          personaColorMap.current[p.id] = getPersonaColor(i);
        });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [roomId]);

  // WebSocket connection
  useEffect(() => {
    if (!room) return;

    const ws = api.connectRoomWebSocket(roomId);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'room_info':
          // Room info received on connect
          break;

        case 'typing':
          setTypingPersonas(prev => new Set([...prev, data.persona_name]));
          // Clear typing after 3s
          setTimeout(() => {
            setTypingPersonas(prev => {
              const next = new Set(prev);
              next.delete(data.persona_name);
              return next;
            });
          }, 3000);
          break;

        case 'message':
          // Clear typing indicator
          setTypingPersonas(prev => {
            const next = new Set(prev);
            next.delete(data.persona_name);
            return next;
          });
          // Add message
          setMessages(prev => [...prev, {
            role: 'assistant',
            persona_id: data.persona_id,
            persona_name: data.persona_name,
            persona_title: data.persona_title,
            content: data.content,
            timestamp: data.timestamp,
          }]);
          // Play audio if available
          if (data.audio_base64) {
            enqueueAudio(data.audio_base64);
          }
          break;

        case 'error':
          console.error('Room error:', data.content);
          break;

        default:
          break;
      }
    };

    return () => {
      ws.close();
    };
  }, [room, roomId, enqueueAudio]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typingPersonas]);

  // Update input when speech transcript changes
  useEffect(() => {
    if (transcript) {
      setInput(prev => prev + transcript);
      setTranscript('');
    }
  }, [transcript, setTranscript]);

  // Send message
  const handleSend = () => {
    if (!input.trim() || !connected) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message locally
    setMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    }]);

    // Send via WebSocket
    wsRef.current?.send(JSON.stringify({
      type: 'message',
      content: userMessage,
    }));
  };

  const handleMicToggle = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-gray-400">Loading room...</div>
      </div>
    );
  }

  if (!room) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Room not found</p>
        <Link to="/" className="text-primary-600 hover:underline mt-2 inline-block">Back to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* ===== Sidebar — Participants ===== */}
      <div className="w-64 shrink-0 bg-white rounded-xl border border-gray-200 p-4 flex flex-col">
        <div className="flex items-center gap-2 mb-4">
          <Users className="h-5 w-5 text-primary-600" />
          <h2 className="font-semibold text-sm">{room.room_name}</h2>
        </div>

        <div className="flex items-center gap-1.5 mb-4">
          {connected ? (
            <>
              <Wifi className="h-3.5 w-3.5 text-green-500" />
              <span className="text-xs text-green-600">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="h-3.5 w-3.5 text-red-400" />
              <span className="text-xs text-red-500">Disconnected</span>
            </>
          )}
        </div>

        <div className="space-y-3 flex-1 overflow-y-auto">
          {room.participants?.map((p, i) => {
            const color = getColor(p.id);
            const isTyping = typingPersonas.has(p.name);
            return (
              <div key={p.id} className="flex items-center gap-2.5">
                <div className={`relative w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold ${color.bg} ${color.text} ${isTyping ? `ring-2 ${color.ring} animate-pulse` : ''}`}>
                  {getInitials(p.name)}
                  {isTyping && (
                    <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-green-400 rounded-full border-2 border-white"></span>
                  )}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{p.name}</p>
                  <p className="text-xs text-gray-400 truncate">{p.title}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Voice controls */}
        <div className="border-t border-gray-100 pt-3 mt-3 flex justify-center gap-3">
          <button
            onClick={() => setIsMuted(!isMuted)}
            className={`p-2 rounded-lg transition ${isMuted ? 'bg-red-50 text-red-500' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            title={isMuted ? 'Unmute voices' : 'Mute voices'}
          >
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* ===== Main Chat Area ===== */}
      <div className="flex-1 flex flex-col bg-white rounded-xl border border-gray-200">
        {/* Chat Header */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-gray-100">
          <Link to={`/simulation/${room.simulation_id}`} className="text-gray-400 hover:text-gray-600">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="font-semibold">{room.room_name}</h1>
            <p className="text-xs text-gray-400">
              {room.participants?.length} participants · {room.room_type === 'role' ? `Role: ${room.role_filter}` : `Table ${(room.table_index || 0) + 1}`}
            </p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <Users className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">The room is ready.</p>
              <p className="text-gray-400 text-sm">Start the conversation — ask a question, pitch an idea, or challenge the committee.</p>
            </div>
          )}

          {messages.map((msg, i) => {
            if (msg.role === 'user') {
              return (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[65%] flex items-end gap-2">
                    <div className="bg-primary-600 text-white px-4 py-2.5 rounded-2xl rounded-br-sm text-sm">
                      {msg.content}
                    </div>
                    <div className="p-1.5 bg-gray-200 rounded-full shrink-0">
                      <User className="h-3.5 w-3.5 text-gray-600" />
                    </div>
                  </div>
                </div>
              );
            }

            // Persona message
            const color = getColor(msg.persona_id);
            return (
              <div key={i} className="flex gap-2.5">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${color.bg} ${color.text}`}>
                  {getInitials(msg.persona_name || '??')}
                </div>
                <div className="max-w-[65%]">
                  <div className="flex items-baseline gap-2 mb-0.5">
                    <span className="text-xs font-semibold text-gray-800">{msg.persona_name}</span>
                    <span className="text-xs text-gray-400">{msg.persona_title}</span>
                  </div>
                  <div className="bg-gray-50 border border-gray-100 px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm text-gray-800">
                    {msg.content}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Typing indicators */}
          {typingPersonas.size > 0 && (
            <div className="flex gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center shrink-0">
                <Bot className="h-4 w-4 text-gray-400" />
              </div>
              <div className="bg-gray-50 border border-gray-100 px-4 py-2.5 rounded-2xl rounded-tl-sm">
                <p className="text-xs text-gray-500 mb-1">
                  {[...typingPersonas].join(', ')} {typingPersonas.size === 1 ? 'is' : 'are'} typing...
                </p>
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-100 px-5 py-3">
          <div className="flex gap-2 items-end">
            {/* Mic button */}
            <button
              onClick={handleMicToggle}
              className={`p-2.5 rounded-xl transition shrink-0 ${
                isListening
                  ? 'bg-red-500 text-white animate-pulse'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
              title={isListening ? 'Stop recording' : 'Start recording'}
            >
              {isListening ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5" />}
            </button>

            {/* Text input */}
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={isListening ? 'Listening... speak now' : 'Ask the committee anything...'}
                rows={1}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none text-sm"
                disabled={!connected}
                style={{ minHeight: '42px', maxHeight: '120px' }}
              />
            </div>

            {/* Send button */}
            <button
              onClick={handleSend}
              disabled={!input.trim() || !connected}
              className="bg-primary-600 text-white p-2.5 rounded-xl hover:bg-primary-700 transition disabled:opacity-50 shrink-0"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>

          {isListening && (
            <p className="text-xs text-red-500 mt-1.5 flex items-center gap-1">
              <Circle className="h-2 w-2 fill-red-500" /> Recording — click mic to stop and send
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
