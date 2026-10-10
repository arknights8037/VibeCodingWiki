import { MICRO_AGENT_TOOLS, type MicroCompletion, type MicroMessage, type MicroToolCall } from '@my-notebook/vue-block-editor/editor';
import { api } from '@/services/api';

type StreamDelta = {
  role?: string;
  content?: unknown;
  reasoning_content?: unknown;
  tool_calls?: unknown;
  function_call?: unknown;
};

function csrfToken(): string | undefined {
  return document.cookie
    .split('; ')
    .find((item) => item.startsWith('csrf_token='))
    ?.split('=').slice(1).join('=');
}

function completionUrl(): string {
  const base = api.defaults.baseURL || '/api/v1';
  return `${base.replace(/\/$/, '')}/admin/ai/completions`;
}

function asToolCall(value: unknown, fallbackIndex: number): { index: number; call: MicroToolCall } | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  const fn = item.function && typeof item.function === 'object' ? item.function as Record<string, unknown> : {};
  const name = typeof fn.name === 'string' ? fn.name : '';
  const args = typeof fn.arguments === 'string' ? fn.arguments : JSON.stringify(fn.arguments ?? {});
  const id = typeof item.id === 'string' ? item.id : `stream-call-${fallbackIndex}`;
  const index = typeof item.index === 'number' ? item.index : fallbackIndex;
  if (!name && !args) return null;
  return {
    index,
    call: {
      id,
      type: 'function',
      function: { name, arguments: args },
    },
  };
}

function parseMessage(message: unknown, onDelta?: (text: string) => void): MicroMessage {
  if (!message || typeof message !== 'object') throw new Error('AI 服务返回了不兼容的消息格式。');
  const value = message as Record<string, unknown>;
  if (value.role !== 'assistant' || (value.content != null && typeof value.content !== 'string')) {
    throw new Error('AI 服务返回了不兼容的消息格式。');
  }
  if (typeof value.content === 'string') onDelta?.(value.content);
  return {
    role: 'assistant',
    content: value.content as string | null ?? null,
    ...(Array.isArray(value.tool_calls) ? { tool_calls: value.tool_calls as MicroToolCall[] } : {}),
    ...(typeof value.reasoning_content === 'string' ? { reasoning_content: value.reasoning_content } : {}),
  } as MicroMessage;
}

function hasInvalidToolArguments(message: MicroMessage): boolean {
  return message.tool_calls?.some((call) => {
    if (typeof call.function?.arguments !== 'string') return true;
    try {
      JSON.parse(call.function.arguments);
      return false;
    } catch {
      return true;
    }
  }) ?? false;
}

async function responseError(response: Response): Promise<Error> {
  let detail = '';
  try {
    const data = await response.json() as { detail?: unknown; error?: { message?: unknown } };
    detail = typeof data.detail === 'string' ? data.detail : typeof data.error?.message === 'string' ? data.error.message : '';
  } catch {
    // Keep the status-based error below when the service did not return JSON.
  }
  return new Error(detail || `AI 服务请求失败（${response.status}）。`);
}

/** Consume an OpenAI-compatible Chat Completion.
 *
 * The editor needs the complete tool-call message before it can execute a
 * read/write operation. Some thinking providers emit reasoning-only SSE
 * chunks before the tool call and their proxy responses can omit the final
 * tool-call frame, so request the complete JSON message here.
 */
export function createAdminAiCompletion(): MicroCompletion {
  return async (messages, signal, onDelta) => {
    // Block editing expects a plain Markdown completion. Sending the agent's
    // read/write tools here lets the model choose a tool call instead of
    // returning replacement text, which the block editor cannot apply.
    const isBlockEdit = messages.some(
      (message) => message.role === 'system' && typeof message.content === 'string' && message.content.includes('块内编辑助手'),
    );
    let requestMessages = messages;
    let response: Response | undefined;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      response = await fetch(completionUrl(), {
        method: 'POST',
        credentials: 'include',
        signal,
        headers: {
          Accept: 'text/event-stream, application/json',
          'Content-Type': 'application/json',
          ...(csrfToken() ? { 'X-CSRF-Token': decodeURIComponent(csrfToken()!) } : {}),
        },
        body: JSON.stringify({
          messages: requestMessages,
          ...(isBlockEdit ? {} : { tools: MICRO_AGENT_TOOLS, tool_choice: 'auto' }),
          stream: false,
        }),
      });
      if (!response.ok) throw await responseError(response);

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('text/event-stream')) {
        const data = await response.json() as { choices?: Array<{ message?: unknown }> };
        const message = parseMessage(data.choices?.[0]?.message, onDelta);
        if (!hasInvalidToolArguments(message) || attempt === 1) return message;
        requestMessages = [{
          role: 'system',
          content: '上一次工具调用参数不是合法 JSON。请重新生成工具调用，arguments 必须是可被 JSON.parse 解析的严格 JSON 字符串，不要省略逗号、引号或转义换行。',
        }, ...messages];
        continue;
      }

      // Streaming responses cannot be retried after the body has started; keep
      // the existing parser and surface a clear error if the provider sends one.
      break;
    }

    if (!response?.body) throw new Error('AI 服务没有返回可读取的流。');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const toolCalls = new Map<number, MicroToolCall>();
    let content = '';
    let reasoningContent = '';
    let role: 'assistant' = 'assistant';
    let buffer = '';
    let eventData: string[] = [];

    const consumeEvent = (raw: string): void => {
      const data = raw.trim();
      if (!data || data === '[DONE]') return;
      let payload: { choices?: Array<{ delta?: StreamDelta; message?: StreamDelta }> };
      try {
        payload = JSON.parse(data) as typeof payload;
      } catch {
        throw new Error('AI 流式响应包含无效 JSON。');
      }
      const choice = payload.choices?.[0];
      const delta = choice?.delta ?? choice?.message;
      if (!delta) return;
      if (delta.role === 'assistant') role = 'assistant';
      if (typeof delta.content === 'string') {
        content += delta.content;
        onDelta?.(delta.content);
      }
      if (typeof delta.reasoning_content === 'string') reasoningContent += delta.reasoning_content;
      const streamedCalls = Array.isArray(delta.tool_calls)
        ? delta.tool_calls
        : delta.function_call ? [delta.function_call] : [];
      streamedCalls.forEach((item, index) => {
        const parsed = asToolCall(item, index);
        if (!parsed) return;
        const existing = toolCalls.get(parsed.index);
        if (!existing) {
          toolCalls.set(parsed.index, parsed.call);
          return;
        }
        if (parsed.call.id && !existing.id.startsWith('stream-call-')) existing.id = parsed.call.id;
        if (parsed.call.function.name) existing.function.name += parsed.call.function.name;
        existing.function.arguments += parsed.call.function.arguments;
      });
    };

    const consumeLines = (text: string): void => {
      buffer += text;
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        if (!line) {
          consumeEvent(eventData.join('\n'));
          eventData = [];
        } else if (line.startsWith('data:')) {
          eventData.push(line.slice(5).trimStart());
        }
      }
    };

    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      consumeLines(decoder.decode(chunk.value, { stream: true }));
    }
    consumeLines(decoder.decode());
    if (eventData.length) consumeEvent(eventData.join('\n'));

    return {
      role,
      content: content || null,
      ...(toolCalls.size ? { tool_calls: [...toolCalls.entries()].sort(([a], [b]) => a - b).map(([, call]) => call) } : {}),
      // DeepSeek thinking models require the assistant's reasoning_content to
      // be echoed on the next tool-call turn, even when the stream reports an
      // empty reasoning string. Keep the field present so multi-step editing
      // tasks do not fail after the initial read call.
      reasoning_content: reasoningContent,
    } as MicroMessage;
  };
}
