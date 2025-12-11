import { QueryMethod } from './api';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  method?: QueryMethod;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  selectedMethod: QueryMethod;
  communityLevel: number;
}
