// API Types matching backend schemas

// Auth Types
export interface Token {
  access_token: string;
  token_type: string;
  refresh_token?: string;
  expires_in?: number;
}

export interface TokenData {
  username?: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RevokeTokenRequest {
  token: string;
  reason?: string;
}

export interface TokenInfo {
  id: string;
  user_id: string;
  expires_at: string;
  revoked_at?: string;
  revoked_reason?: string;
  device_info?: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  last_used_at?: string;
}

export interface UserCreate {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  organization_id?: string;
  created_at: string;
  updated_at: string;
}

// Paper Types
export enum IngestionStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed"
}

export enum ParserType {
  DOCLING = "docling",
  PYPDF = "pypdf",
  MANUAL = "manual"
}

export enum Visibility {
  PUBLIC = "public",
  ORGANIZATION = "organization",
  PRIVATE = "private"
}

export interface PaperSection {
  title: string;
  content: string;
  level?: number;
}

export interface PaperReference {
  text: string;
  doi?: string;
  arxiv_id?: string;
  title?: string;
}

export interface PaperCreate {
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  categories: string[];
  published_date: string;
  pdf_url: string;
  doi?: string;
  journal_ref?: string;
  comments?: string;
  source?: string;
  tags?: string[];
  keywords?: string[];
  organization_id?: string;
  visibility?: Visibility;
  license?: string;
  version?: string;
  submission_date?: string;
  update_date?: string;
  citation_count?: number;
  view_count?: number;
  download_count?: number;
  arxiv_version?: string;
  primary_category?: string;
}

export interface PaperUpdate {
  title?: string;
  abstract?: string;
  authors?: string[];
  categories?: string[];
  doi?: string;
  journal_ref?: string;
  comments?: string;
  tags?: string[];
  keywords?: string[];
  quality_score?: number;
  ingestion_status?: IngestionStatus;
  organization_id?: string;
  visibility?: Visibility;
  license?: string;
  version?: string;
  submission_date?: string;
  update_date?: string;
  citation_count?: number;
  view_count?: number;
  download_count?: number;
  arxiv_version?: string;
  primary_category?: string;
}

export interface PaperIngestionUpdate {
  raw_text?: string;
  sections?: PaperSection[];
  references?: PaperReference[];
  parser_used?: ParserType;
  parser_metadata?: Record<string, any>;
  pdf_processed?: boolean;
  pdf_processing_date?: string;
  pdf_file_size?: string;
  pdf_page_count?: number;
  ingestion_status: IngestionStatus;
  ingestion_attempts?: number;
  last_ingestion_attempt?: string;
  ingestion_errors?: Record<string, any>[];
}

export interface PaperResponse {
  id: string;
  arxiv_id: string;
  doi?: string;
  title: string;
  authors: string[];
  abstract: string;
  categories: string[];
  published_date: string;
  pdf_url: string;
  raw_text?: string;
  sections?: PaperSection[];
  references?: PaperReference[];
  parser_used?: ParserType;
  parser_metadata?: Record<string, any>;
  pdf_processed?: boolean;
  pdf_processing_date?: string;
  pdf_file_size?: string;
  pdf_page_count?: number;
  tags?: string[];
  keywords?: string[];
  journal_ref?: string;
  comments?: string;
  ingestion_status: IngestionStatus;
  ingestion_attempts?: number;
  last_ingestion_attempt?: string;
  ingestion_errors?: Record<string, any>[];
  created_at: string;
  updated_at: string;
  created_by: string;
  last_modified_by?: string;
  source: string;
  quality_score?: number;
  duplicate_of?: string;
  organization_id?: string;
  visibility: Visibility;
  license?: string;
  version?: string;
  submission_date?: string;
  update_date?: string;
  citation_count?: number;
  view_count?: number;
  download_count?: number;
  arxiv_version?: string;
  primary_category?: string;
}

export interface PaperListResponse {
  papers: PaperResponse[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaperIngestionStats {
  total_papers: number;
  processed_papers: number;
  papers_with_text: number;
  failed_ingestions: number;
  processing_rate: number;
  text_extraction_rate: number;
  average_processing_time?: number;
  last_ingestion_run?: string;
}

// Search Types
export interface SearchRequest {
  query: string;
  mode?: string;
  limit?: number;
  offset?: number;
  filters?: Record<string, any>;
  include_highlights?: boolean;
  search_fields?: string[];
  field_boosts?: Record<string, number>;
}

export interface SearchResult {
  id: string;
  title: string;
  abstract?: string;
  authors?: string[];
  score: number;
  highlights?: Record<string, string[]>;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
  took: number;
}

// RAG Types
export interface RAGRequest {
  query: string;
  context_limit?: number;
  max_tokens?: number;
  temperature?: number;
  search_mode?: string;
}

export interface RAGSource {
  id: string;
  title: string;
  abstract?: string;
  content?: string;
  authors?: string[];
  score: number;
  url?: string;
}

export interface RAGResponse {
  query: string;
  answer: string;
  sources: RAGSource[];
  confidence: number;
  tokens_used: number;
  generation_time?: number;
  model?: string;
  context_length?: number;
  degraded?: boolean;
  timestamp?: string;
}

export interface BatchRAGRequest {
  queries: string[];
  context_limit?: number;
  max_tokens?: number;
  temperature?: number;
  search_mode?: string;
}

export interface BatchRAGResponse {
  results: RAGResponse[];
  total_queries: number;
  total_tokens: number;
  total_time: number;
  timestamp?: string;
}

export interface StreamingRAGResponse {
  type: string;
  content?: string;
  sources?: RAGSource[];
  done?: boolean;
  tokens_used?: number;
  confidence?: number;
}

export interface LLMModelInfo {
  id: string;
  name: string;
  context_length?: number;
  pricing?: Record<string, number>;
}

export interface AvailableModelsResponse {
  models: LLMModelInfo[];
  default_model: string;
  timestamp?: string;
}

export interface HealthStatus {
  service: string;
  healthy: boolean;
  status_code?: number;
  response_time?: number;
  error?: string;
  timestamp?: string;
}

export interface RAGHealthResponse {
  overall_healthy: boolean;
  services: Record<string, HealthStatus>;
  timestamp?: string;
}

export interface UsageStats {
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  errors: number;
  average_response_time?: number;
  last_reset: string;
  timestamp?: string;
}

export interface RAGConfig {
  default_model: string;
  max_context_docs: number;
  context_window_size: number;
  default_temperature: number;
  default_max_tokens: number;
  cache_ttl: number;
  batch_max_queries: number;
  rate_limit_requests_per_minute: number;
  rate_limit_streaming_requests_per_minute: number;
  rate_limit_batch_max_queries_per_minute: number;
}

// Admin Types
export interface SystemStats {
  total_users: number;
  total_papers: number;
  total_searches: number;
  cache_hit_rate: number;
  average_response_time: number;
  system_uptime: number;
}

export interface UserStats {
  active_users: number;
  new_users_today: number;
  top_search_queries: Record<string, number>;
  user_activity_trends: Record<string, any>;
}

export interface SearchStats {
  total_queries: number;
  average_query_time: number;
  popular_categories: Record<string, number>;
  search_success_rate: number;
  index_size: number;
}

// Analytics Types
export interface PerformanceMetrics {
  uptime_seconds: number;
  total_requests: number;
  error_rate: number;
  operations: Record<string, any>;
}

export interface SearchAnalytics {
  total_queries: number;
  average_response_time: number;
  popular_queries: string[];
  search_modes: Record<string, number>;
}

export interface RateLimitInfo {
  requests_remaining: number;
  reset_time: string;
  limit: number;
  window_seconds: number;
}

export interface UsageMetrics {
  user_id: string;
  period: {
    start_date: string;
    end_date: string;
  };
  total_api_calls: number;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  average_response_time: number;
  unique_endpoints_used: number;
  endpoint_breakdown: Record<string, number>;
  rag_usage: {
    total_tokens_used: number;
    average_confidence: number;
    total_sources_retrieved: number;
    rag_queries_count: number;
  };
}

export interface BillingMetrics {
  total_cost: number;
  usage: UsageMetrics;
  billing: Record<string, any>;
}

export interface UsageTrends {
  daily_usage: number[];
  weekly_usage: number[];
  monthly_usage: number[];
  timestamp: string;
}

export interface InvoiceData {
  invoice_number: string;
  organization: {
    id: string;
    name: string;
    subscription_tier: string;
  };
  billing_period: {
    start: string;
    end: string;
  };
  usage: UsageMetrics;
  billing: Record<string, any>;
  generated_at: string;
  due_date: string;
}

export interface CircuitBreakerStats {
  service: string;
  state: string;
  failures: number;
  last_failure_time?: string;
  next_retry_time?: string;
}

// API Error Types
export interface APIError {
  detail: string;
  status_code?: number;
  errors?: Record<string, string[]>;
  rate_limit_info?: RateLimitInfo;
}

// Generic API Response Types
export interface APIResponse<T = any> {
  data?: T;
  message?: string;
  error?: string;
  status_code?: number;
}

// Pagination Types
export interface PaginationParams {
  skip?: number;
  limit?: number;
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}