import { TOKEN_STORAGE_KEY } from '../config/constants';

/**
 * The access token. Kept in memory and mirrored to sessionStorage: it survives
 * a reload but not the tab. If storage is disabled it lives only in memory.
 * (A production build would use OIDC with short-lived tokens instead.)
 */
export class TokenStorage {
  private memory: string | null | undefined;

  constructor(private readonly key: string = TOKEN_STORAGE_KEY) {}

  get(): string | null {
    if (this.memory === undefined) {
      try {
        this.memory = sessionStorage.getItem(this.key);
      } catch {
        this.memory = null;
      }
    }
    return this.memory;
  }

  set(token: string | null): void {
    this.memory = token;
    try {
      if (token) sessionStorage.setItem(this.key, token);
      else sessionStorage.removeItem(this.key);
    } catch {
      /* storage disabled: the token lives only in memory */
    }
  }
}

export const tokenStorage = new TokenStorage();
