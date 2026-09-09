export interface ChatSession {
  session_id: string
  model: string
  expires_in_seconds: number
  memory_limit_turns: number
  memory_max_characters: number
}

export interface ChatMessageRequest {
  session_id: string
  message: string
  request_id: string
}

export interface ChatMessageResponse {
  request_id: string
  reply: string
  model: string
  memory_turns: number
  expires_in_seconds: number
}
