// ==================== User ====================
export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'editor' | 'viewer';
  is_active: boolean;
  preferred_language: string;
  created_at: string;
}

// ==================== Meeting ====================
export type MeetingStatus =
  | 'uploaded'
  | 'preprocessing'
  | 'processing'
  | 'completed'
  | 'failed';

export interface Meeting {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  source_language: string;
  file_path?: string;
  file_type?: 'video' | 'audio';
  file_size_bytes?: number;
  duration_seconds?: number;
  status: MeetingStatus;
  created_at: string;
  updated_at: string;
}

export interface MeetingCreate {
  title: string;
  description?: string;
  source_language: string;
  file_path: string;
  file_type: 'video' | 'audio';
  file_size_bytes: number;
  duration_seconds?: number;
}

export interface MeetingListParams {
  page?: number;
  page_size?: number;
  status?: MeetingStatus;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ==================== Task ====================
export type TaskType =
  | 'audio_preprocess'
  | 'asr'
  | 'diarization'
  | 'translation'
  | 'summary';

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'retrying'
  | 'dlq';

export interface MeetingTask {
  id: string;
  meeting_id: string;
  task_type: TaskType;
  celery_task_id?: string;
  priority: number;
  status: TaskStatus;
  progress: number;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface TaskLog {
  id: string;
  task_id: string;
  level: string;
  message: string;
  timestamp: string;
}

// ==================== Subtitle ====================
export interface Subtitle {
  id: string;
  meeting_id: string;
  meeting_title?: string;  // From search results (join)
  speaker_label: string;
  language: string;
  start_time_ms: number;
  end_time_ms: number;
  text: string;
  headline?: string;  // Highlighted text from ts_headline (search results)
  rank?: number;       // Search relevance rank
  is_candidate: boolean;
  confidence: number;
  created_at: string;
}

export interface SubtitleListParams {
  format?: 'vtt' | 'srt' | 'json';
  lang?: string;
  speaker?: string;
}

// ==================== Translation ====================
export interface Translation {
  id: string;
  subtitle_id: string;
  meeting_id: string;
  target_language: string;
  translated_text: string;
  model_used: string;
  token_count_input: number;
  token_count_output: number;
  cost: number;
  translation_hash: string;
  created_at: string;
}

export interface TranslationRequest {
  meeting_id: string;
  target_language: string;
}

// ==================== Model Config ====================
export type ModelType = 'asr' | 'translation' | 'summary';

export interface ModelConfig {
  id: string;
  model_type: ModelType;
  provider: string;
  model_name: string;
  api_key_encrypted?: string;
  endpoint_url?: string;
  parameters: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelConfigUpdate {
  model_name?: string;
  api_key_encrypted?: string;
  endpoint_url?: string;
  parameters?: Record<string, unknown>;
  is_active?: boolean;
}

// ==================== Token Usage ====================
export interface TokenUsage {
  id: string;
  user_id: string;
  meeting_id?: string;
  model_config_id: string;
  operation_type: string;
  tokens_input: number;
  tokens_output: number;
  tokens_total: number;
  cost: number;
  request_id?: string;
  created_at: string;
}

export interface TokenUsageStats {
  total_tokens: number;
  total_cost: number;
  by_model: Record<string, { tokens: number; cost: number }>;
  by_operation: Record<string, { tokens: number; cost: number }>;
}

// ==================== API Key ====================
export interface ApiKey {
  id: string;
  user_id: string;
  key_name: string;
  prefix: string;
  scopes: string[];
  rate_limit: number;
  expires_at?: string;
  is_active: boolean;
  last_used_at?: string;
  created_at: string;
}

export interface ApiKeyCreate {
  key_name: string;
  scopes?: string[];
  rate_limit?: number;
  expires_at?: string;
}

export interface ApiKeyCreateResponse {
  id: string;
  key_name: string;
  api_key: string; // only returned once
  prefix: string;
  message?: string;
}

// ==================== Search ====================
export interface SearchResult {
  items: Subtitle[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  highlights?: Record<string, string>;
}

export interface SearchParams {
  q: string;
  meeting_id?: string;
  speaker?: string;
  time_from?: number;
  time_to?: number;
  page?: number;
  page_size?: number;
}

// ==================== SSE ====================
export interface TaskProgressEvent {
  task_id: string;
  meeting_id: string;
  task_type: TaskType;
  status: TaskStatus;
  progress: number;
  current_step: string;
  message: string;
  timestamp: string;
  error_detail?: string;
}

// ==================== Export ====================
export interface ExportRequest {
  meeting_id: string;
  format: 'srt' | 'vtt' | 'json' | 'txt' | 'csv';
  lang?: string;
}

// ==================== Auth ====================
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user_id: string;
  username: string;
  role: string;
}

// ==================== Upload ====================
export interface SignUrlResponse {
  upload_url: string;
  object_key: string;
  expires_in: number;
}

export interface UploadCompleteRequest {
  object_key: string;
  file_name: string;
  file_size: number;
  file_type: 'video' | 'audio';
}
