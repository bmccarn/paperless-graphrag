import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Message, QueryMethod } from '@/types';

export interface ChatSession {
  id: string;
  name: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface ThinkingState {
  message: string;
  detail?: string;
}

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  thinking: ThinkingState | null;
  selectedMethod: QueryMethod;
  communityLevel: number;

  // Computed
  currentSession: () => ChatSession | undefined;
  messages: () => Message[];

  // Session actions
  createSession: (name?: string) => string;
  switchSession: (sessionId: string) => void;
  renameSession: (sessionId: string, name: string) => void;
  deleteSession: (sessionId: string) => void;

  // Message actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  setLoading: (loading: boolean) => void;
  setThinking: (thinking: ThinkingState | null) => void;
  setMethod: (method: QueryMethod) => void;
  setCommunityLevel: (level: number) => void;
  clearHistory: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      isLoading: false,
      thinking: null,
      selectedMethod: 'local',
      communityLevel: 2,

      // Computed getters
      currentSession: () => {
        const state = get();
        return state.sessions.find(s => s.id === state.currentSessionId);
      },

      messages: () => {
        const session = get().currentSession();
        return session?.messages || [];
      },

      // Create a new chat session
      createSession: (name?: string) => {
        const id = crypto.randomUUID();
        const now = new Date();
        const sessionCount = get().sessions.length;
        const newSession: ChatSession = {
          id,
          name: name || `Chat ${sessionCount + 1}`,
          messages: [],
          createdAt: now,
          updatedAt: now,
        };

        set((state) => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: id,
        }));

        return id;
      },

      // Switch to a different session
      switchSession: (sessionId: string) => {
        set({ currentSessionId: sessionId });
      },

      // Rename a session
      renameSession: (sessionId: string, name: string) => {
        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === sessionId ? { ...s, name, updatedAt: new Date() } : s
          ),
        }));
      },

      // Delete a session
      deleteSession: (sessionId: string) => {
        set((state) => {
          const newSessions = state.sessions.filter(s => s.id !== sessionId);
          const needsNewCurrent = state.currentSessionId === sessionId;

          return {
            sessions: newSessions,
            currentSessionId: needsNewCurrent
              ? (newSessions[0]?.id || null)
              : state.currentSessionId,
          };
        });
      },

      // Add a message to the current session
      addMessage: (message) =>
        set((state) => {
          // Create a session if none exists
          if (!state.currentSessionId || !state.sessions.find(s => s.id === state.currentSessionId)) {
            const id = crypto.randomUUID();
            const now = new Date();
            const newMessage = {
              ...message,
              id: crypto.randomUUID(),
              timestamp: now,
            };

            // Generate session name from first user message
            const sessionName = message.role === 'user'
              ? message.content.slice(0, 30) + (message.content.length > 30 ? '...' : '')
              : `Chat ${state.sessions.length + 1}`;

            const newSession: ChatSession = {
              id,
              name: sessionName,
              messages: [newMessage],
              createdAt: now,
              updatedAt: now,
            };

            return {
              sessions: [newSession, ...state.sessions],
              currentSessionId: id,
            };
          }

          // Add to existing session
          return {
            sessions: state.sessions.map(s =>
              s.id === state.currentSessionId
                ? {
                    ...s,
                    messages: [
                      ...s.messages,
                      {
                        ...message,
                        id: crypto.randomUUID(),
                        timestamp: new Date(),
                      },
                    ],
                    updatedAt: new Date(),
                  }
                : s
            ),
          };
        }),

      setLoading: (loading) => set({ isLoading: loading }),

      setThinking: (thinking) => set({ thinking }),

      setMethod: (method) => set({ selectedMethod: method }),

      setCommunityLevel: (level) => set({ communityLevel: level }),

      // Clear current session's messages
      clearHistory: () =>
        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === state.currentSessionId
              ? { ...s, messages: [], updatedAt: new Date() }
              : s
          ),
        })),
    }),
    {
      name: 'paperless-graphrag-chat',
      partialize: (state) => ({
        sessions: state.sessions.slice(0, 20).map(s => ({
          ...s,
          messages: s.messages.slice(-50), // Keep last 50 messages per session
        })),
        currentSessionId: state.currentSessionId,
        selectedMethod: state.selectedMethod,
        communityLevel: state.communityLevel,
      }),
    }
  )
);
