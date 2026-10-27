import { ApiError } from '../api-error';
import type { ErrorInterceptor } from '../http-client';

/**
 * The single place where status codes become user-facing text. Generic wording
 * here; an endpoint can refine it per request (RequestMeta.messages).
 */
export const STATUS_MESSAGES: Readonly<Record<number, string>> = {
  401: 'Not authorised. Please sign in again.',
  404: 'Not found.',
  422: 'Request rejected as invalid.',
  429: 'Too many requests. Try again in a moment.',
  502: 'Server unreachable. Try again in a moment.',
  503: 'Service unavailable. Try again in a moment.',
  504: 'Server did not answer in time.',
};

export const errorInterceptor: ErrorInterceptor = (err, req) => {
  switch (err.kind) {
    case 'timeout':
      return new ApiError(0, 'timeout', 'Request timed out.');
    case 'network':
      return new ApiError(0, 'network', 'Network error. Is the server reachable?');
    case 'parse':
      return new ApiError(err.status, 'parse', 'Unexpected response from the server.');
    case 'http':
      return new ApiError(err.status, 'http',
        req.meta.messages?.[err.status] ?? STATUS_MESSAGES[err.status] ?? `Request failed (HTTP ${err.status}).`);
  }
};
