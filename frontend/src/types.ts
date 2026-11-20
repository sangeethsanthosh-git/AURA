export interface WikiArticle {
  title: string;
  url: string;
  extract: string;
}

export interface WikiImage {
  url: string;
  original_url?: string;
  title: string;
  caption: string;
}

export interface WikiResult {
  query: string;
  articles: WikiArticle[];
  images: WikiImage[];
}

export type WikiGenre = 'auto' | 'biography' | 'landmark' | 'archival' | 'folio';

export interface SystemAction {
  action:
    | 'volume'
    | 'battery'
    | 'system_specs'
    | 'app_launch'
    | 'media'
    | 'clipboard'
    | 'web_search'
    | 'screen_vision'
    | 'document_search'
    | 'timer'
    | 'sandbox_blocked'
    | 'window_management'
    | 'app_close'
    | 'active_window'
    | 'running_apps'
    | 'file_search'
    | 'file_organize'
    | 'large_files'
    | 'duplicate_files'
    | 'storage_analysis'
    | 'read_document'
    | 'git_status'
    | 'git_diff'
    | 'unit_tests'
    | 'composite_workflow'
    | 'permission_checkpoint';
  tool_type?: string;
  type?: string;
  title: string;
  message: string;
  spoken_response?: string;
  data: Record<string, any>;
}

export interface MessageItem {
  id: string;
  role: 'user' | 'aura';
  text: string;
  wiki?: WikiResult;
  action?: SystemAction;
  isStreaming?: boolean;
}

export type AssistantState = 'idle' | 'listening' | 'thinking' | 'speaking';
export type CompanionType = 'ember' | 'frost' | 'clara';
export type ConversationMode = 'companion' | 'stream';

export interface ModelProfile {
  id: string;
  name: string;
  desc: string;
  badge: string;
  tag: string;
}

export interface VoiceOption {
  id: string;
  name: string;
  label: string;
  sub: string;
  gender: string;
  engine: string;
}
