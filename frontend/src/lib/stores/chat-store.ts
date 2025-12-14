import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Message, QueryMethod } from '@/types';
import * as chatApi from '@/lib/api/chat';

// Polyfill for crypto.randomUUID in environments where it's not available
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback implementation
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

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
  input: string;

  // Database sync state
  dbEnabled: boolean;
  dbSyncing: boolean;
  dbError: string | null;

  // Computed
  currentSession: () => ChatSession | undefined;
  messages: () => Message[];

  // Session actions
  createSession: (name?: string) => Promise<string>;
  switchSession: (sessionId: string) => void;
  renameSession: (sessionId: string, name: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;

  // Message actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => Promise<void>;
  setLoading: (loading: boolean) => void;
  setThinking: (thinking: ThinkingState | null) => void;
  setMethod: (method: QueryMethod) => void;
  setCommunityLevel: (level: number) => void;
  setInput: (input: string) => void;
  clearHistory: () => void;

  // Database actions
  initFromDatabase: () => Promise<void>;
  checkDbStatus: () => Promise<void>;
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
      input: '',
      dbEnabled: false,
      dbSyncing: false,
      dbError: null,

      // Computed getters
      currentSession: () => {
        const state = get();
        return state.sessions.find(s => s.id === state.currentSessionId);
      },

      messages: () => {
        const session = get().currentSession();
        return session?.messages || [];
      },

      // Check database status
      checkDbStatus: async () => {
        try {
          const status = await chatApi.getChatStatus();
          set({ dbEnabled: status.enabled, dbError: null });
        } catch {
          set({ dbEnabled: false, dbError: 'Failed to check database status' });
        }
      },

      // Initialize sessions from database
      initFromDatabase: async () => {
        const state = get();
        if (!state.dbEnabled) return;

        set({ dbSyncing: true });
        try {
          const remoteSessions = await chatApi.getSessions();

          // Convert API response to local format
          const sessions: ChatSession[] = remoteSessions.map(s => ({
            id: s.id,
            name: s.name,
            messages: [], // Messages loaded on demand
            createdAt: new Date(s.createdAt),
            updatedAt: new Date(s.updatedAt),
          }));

          // Merge with local sessions (prefer remote)
          const localOnlySessions = state.sessions.filter(
            local => !sessions.some(remote => remote.id === local.id)
          );

          set({
            sessions: [...sessions, ...localOnlySessions],
            dbSyncing: false,
            dbError: null,
          });

          // If current session is from DB, load its messages
          if (state.currentSessionId) {
            const currentInRemote = sessions.find(s => s.id === state.currentSessionId);
            if (currentInRemote) {
              try {
                const fullSession = await chatApi.getSession(state.currentSessionId);
                if (fullSession?.messages) {
                  set(prev => ({
                    sessions: prev.sessions.map(s =>
                      s.id === state.currentSessionId
                        ? {
                            ...s,
                            messages: fullSession.messages!.map(m => ({
                              id: m.id,
                              role: m.role,
                              content: m.content,
                              timestamp: new Date(m.timestamp),
                              method: m.method as QueryMethod | undefined,
                              sourceDocuments: m.sourceDocuments,
                            })),
                          }
                        : s
                    ),
                  }));
                }
              } catch {
                // Ignore - use cached messages
              }
            }
          }
        } catch (error) {
          set({
            dbSyncing: false,
            dbError: error instanceof Error ? error.message : 'Failed to load sessions'
          });
        }
      },

      // Create a new chat session
      createSession: async (name?: string) => {
        const id = generateUUID();
        const now = new Date();
        const sessionCount = get().sessions.length;
        const sessionName = name || `Chat ${sessionCount + 1}`;

        const newSession: ChatSession = {
          id,
          name: sessionName,
          messages: [],
          createdAt: now,
          updatedAt: now,
        };

        // Update local state immediately
        set((state) => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: id,
        }));

        // Sync to database if enabled
        const state = get();
        if (state.dbEnabled) {
          try {
            await chatApi.createSession(sessionName, id);
          } catch (error) {
            console.error('Failed to sync session to database:', error);
            // Don't fail - local session still works
          }
        }

        return id;
      },

      // Switch to a different session
      switchSession: (sessionId: string) => {
        set({ currentSessionId: sessionId });

        // Load messages from DB if enabled
        const state = get();
        if (state.dbEnabled) {
          chatApi.getSession(sessionId)
            .then(fullSession => {
              if (fullSession?.messages) {
                set(prev => ({
                  sessions: prev.sessions.map(s =>
                    s.id === sessionId
                      ? {
                          ...s,
                          messages: fullSession.messages!.map(m => ({
                            id: m.id,
                            role: m.role,
                            content: m.content,
                            timestamp: new Date(m.timestamp),
                            method: m.method as QueryMethod | undefined,
                            sourceDocuments: m.sourceDocuments,
                          })),
                        }
                      : s
                  ),
                }));
              }
            })
            .catch(() => {
              // Ignore - use cached messages
            });
        }
      },

      // Rename a session
      renameSession: async (sessionId: string, name: string) => {
        // Update local state immediately
        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === sessionId ? { ...s, name, updatedAt: new Date() } : s
          ),
        }));

        // Sync to database if enabled
        const state = get();
        if (state.dbEnabled) {
          try {
            await chatApi.renameSession(sessionId, name);
          } catch (error) {
            console.error('Failed to sync rename to database:', error);
          }
        }
      },

      // Delete a session
      deleteSession: async (sessionId: string) => {
        // Update local state immediately
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

        // Sync to database if enabled
        const state = get();
        if (state.dbEnabled) {
          try {
            await chatApi.deleteSession(sessionId);
          } catch (error) {
            console.error('Failed to delete session from database:', error);
          }
        }
      },

      // Add a message to the current session
      addMessage: async (message) => {
        const state = get();
        const messageId = generateUUID();
        const timestamp = new Date();

        // Create a session if none exists
        if (!state.currentSessionId || !state.sessions.find(s => s.id === state.currentSessionId)) {
          const sessionId = generateUUID();
          const now = new Date();
          const newMessage: Message = {
            ...message,
            id: messageId,
            timestamp: now,
          };

          // Generate session name from first user message
          const sessionName = message.role === 'user'
            ? message.content.slice(0, 30) + (message.content.length > 30 ? '...' : '')
            : `Chat ${state.sessions.length + 1}`;

          const newSession: ChatSession = {
            id: sessionId,
            name: sessionName,
            messages: [newMessage],
            createdAt: now,
            updatedAt: now,
          };

          set({
            sessions: [newSession, ...state.sessions],
            currentSessionId: sessionId,
          });

          // Sync to database if enabled
          if (state.dbEnabled) {
            try {
              await chatApi.createSession(sessionName, sessionId);
              await chatApi.addMessage(sessionId, {
                id: messageId,
                role: message.role,
                content: message.content,
                method: message.method,
                sourceDocuments: message.sourceDocuments,
                timestamp: timestamp.toISOString(),
              });
            } catch (error) {
              console.error('Failed to sync message to database:', error);
            }
          }

          return;
        }

        // Add to existing session (local)
        const newMessage: Message = {
          ...message,
          id: messageId,
          timestamp,
        };

        // Get current session to check message count
        const currentSession = state.sessions.find(s => s.id === state.currentSessionId);
        const isFirstAssistantResponse = message.role === 'assistant' &&
          currentSession &&
          currentSession.messages.length === 1 &&
          currentSession.messages[0].role === 'user';

        set({
          sessions: state.sessions.map(s =>
            s.id === state.currentSessionId
              ? {
                  ...s,
                  messages: [...s.messages, newMessage],
                  updatedAt: new Date(),
                }
              : s
          ),
        });

        // Sync to database if enabled
        if (state.dbEnabled && state.currentSessionId) {
          try {
            await chatApi.addMessage(state.currentSessionId, {
              id: messageId,
              role: message.role,
              content: message.content,
              method: message.method,
              sourceDocuments: message.sourceDocuments,
              timestamp: timestamp.toISOString(),
            });
          } catch (error) {
            console.error('Failed to sync message to database:', error);
          }
        }

        // Generate AI title after first assistant response
        if (isFirstAssistantResponse && currentSession) {
          const userMessage = currentSession.messages[0].content;
          try {
            const title = await chatApi.generateChatTitle(userMessage);
            // Update session name locally
            set(prev => ({
              sessions: prev.sessions.map(s =>
                s.id === state.currentSessionId
                  ? { ...s, name: title, updatedAt: new Date() }
                  : s
              ),
            }));
            // Sync to database if enabled
            if (state.dbEnabled && state.currentSessionId) {
              await chatApi.renameSession(state.currentSessionId, title);
            }
          } catch (error) {
            console.error('Failed to generate chat title:', error);
          }
        }
      },

      setLoading: (loading) => set({ isLoading: loading }),

      setThinking: (thinking) => set({ thinking }),

      setMethod: (method) => set({ selectedMethod: method }),

      setCommunityLevel: (level) => set({ communityLevel: level }),

      setInput: (input) => set({ input }),

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
        // Don't persist dbEnabled - check on each load
      }),
    }
  )
);
