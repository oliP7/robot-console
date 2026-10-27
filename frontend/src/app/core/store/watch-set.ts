/** The ids this client asks the server for: visible rows plus robots with a command in flight. */
export class WatchSet {
  private ids = new Set<string>();

  has(id: string): boolean {
    return this.ids.has(id);
  }

  toArray(): string[] {
    return [...this.ids];
  }

  /** Replaces the set. Returns false when the membership is unchanged. */
  update(visible: readonly string[], extra: Iterable<string>): boolean {
    const next = new Set(visible);
    for (const id of extra) next.add(id);
    if (next.size === this.ids.size && [...next].every((id) => this.ids.has(id))) return false;
    this.ids = next;
    return true;
  }
}
