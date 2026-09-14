/// <reference types="vite/client" />
import { PipelineRequest, PipelineResult, PipelineProgressEvent } from '../types/api';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

/**
 * Format currency and numerical estimates gracefully (supports Crores/Lakhs for INR, Millions/Billions for USD).
 */
export function formatCurrencyValue(
  value: number | null | undefined,
  currency: string = 'INR',
  unitSuffix: string = ''
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'Not calculated';
  }

  const curr = String(currency || 'INR').toUpperCase();

  if (curr === 'INR' || curr === 'RS' || curr === 'RUPEES') {
    const absVal = Math.abs(value);
    if (absVal >= 10000000) {
      const cr = value / 10000000;
      return `₹${cr.toLocaleString('en-IN', { maximumFractionDigits: 2 })} Cr${unitSuffix ? ` ${unitSuffix}` : ''}`;
    } else if (absVal >= 100000) {
      const lakh = value / 100000;
      return `₹${lakh.toLocaleString('en-IN', { maximumFractionDigits: 2 })} Lakh${unitSuffix ? ` ${unitSuffix}` : ''}`;
    } else {
      return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}${unitSuffix ? ` ${unitSuffix}` : ''}`;
    }
  }

  // USD / Generic currency
  const symbol = curr === 'USD' ? '$' : curr === 'EUR' ? '€' : `${curr} `;
  const absVal = Math.abs(value);
  if (absVal >= 1000000000) {
    const b = value / 1000000000;
    return `${symbol}${b.toLocaleString('en-US', { maximumFractionDigits: 2 })}B${unitSuffix ? ` ${unitSuffix}` : ''}`;
  } else if (absVal >= 1000000) {
    const m = value / 1000000;
    return `${symbol}${m.toLocaleString('en-US', { maximumFractionDigits: 2 })}M${unitSuffix ? ` ${unitSuffix}` : ''}`;
  } else {
    return `${symbol}${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}${unitSuffix ? ` ${unitSuffix}` : ''}`;
  }
}

export function formatNumberOnly(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A';
  }
  return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

/**
 * Standard HTTP POST call to /api/v1/pipeline/analyze
 */
export async function analyzeMarket(request: PipelineRequest): Promise<PipelineResult> {
  const url = `${API_BASE_URL}/api/v1/pipeline/analyze`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      let errorMessage = `Server error (${response.status})`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
          } else {
            errorMessage = errorData.detail;
          }
        }
      } catch {
        // use fallback text
      }

      if (response.status === 400 || response.status === 422) {
        throw new Error(`Input validation error: ${errorMessage}`);
      } else if (response.status === 503) {
        throw new Error(`Market analysis service is temporarily unavailable. Please verify the AI backend is running.`);
      } else if (response.status >= 500) {
        throw new Error(`Market analysis could not be completed because an internal processing error occurred: ${errorMessage}`);
      }
      throw new Error(errorMessage);
    }

    const data: PipelineResult = await response.json();
    return data;
  } catch (err: any) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(
        'Unable to connect to the backend server. Please ensure the API is running at http://localhost:8000.'
      );
    }
    throw err;
  }
}

/**
 * Streaming pipeline analysis via SSE endpoint POST /api/v1/pipeline/analyze/stream
 */
export function streamPipeline(
  request: PipelineRequest,
  onEvent: (event: PipelineProgressEvent) => void,
  onComplete: (result: PipelineResult) => void,
  onError: (error: Error) => void
): () => void {
  const controller = new AbortController();
  const url = `${API_BASE_URL}/api/v1/pipeline/analyze/stream`;

  (async () => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Stream connection failed with status ${response.status}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported by response');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          const trimmed = block.trim();
          if (!trimmed) continue;

          let eventName = 'message';
          let eventData = '';

          for (const line of trimmed.split('\n')) {
            if (line.startsWith('event:')) {
              eventName = line.replace('event:', '').trim();
            } else if (line.startsWith('data:')) {
              eventData = line.replace('data:', '').trim();
            }
          }

          if (eventData) {
            try {
              const parsed = JSON.parse(eventData);
              if (eventName === 'progress') {
                onEvent(parsed as PipelineProgressEvent);
              } else if (eventName === 'complete') {
                onComplete(parsed as PipelineResult);
                return;
              } else if (eventName === 'error') {
                onError(new Error(parsed.message || 'Pipeline encountered an error.'));
                return;
              }
            } catch (e) {
              console.warn('Failed to parse SSE payload:', eventData, e);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        onError(err instanceof Error ? err : new Error(String(err)));
      }
    }
  })();

  return () => controller.abort();
}
