/** Above this many changes one full sort beats many splices. */
const SORT_THRESHOLD = 64;

const byId = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

function lowerBound(arr: readonly string[], id: string): number {
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if ((arr[mid] as string) < id) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/**
 * The sorted list of every robot id, plus the search filter over it.
 * Arrays are replaced, never mutated, so a reference compare tells React
 * whether anything changed.
 */
export class RobotIndex {
  private ids: string[] = [];
  private idSet = new Set<string>();
  private filter = '';
  private filtered: string[] | null = null;

  has(id: string): boolean {
    return this.idSet.has(id);
  }

  get total(): number {
    return this.ids.length;
  }

  getFilter(): string {
    return this.filter;
  }

  /** Sorted ids matching the current filter. Same array until something changes. */
  getIds(): string[] {
    if (this.filtered === null) {
      const q = this.filter;
      this.filtered = q ? this.ids.filter((id) => id.toLowerCase().includes(q)) : this.ids;
    }
    return this.filtered;
  }

  /** Returns false when the normalized query did not change. */
  setFilter(q: string): boolean {
    const next = q.trim().toLowerCase();
    if (next === this.filter) return false;
    this.filter = next;
    this.filtered = null;
    return true;
  }

  replace(ids: string[]): void {
    const sorted = [...new Set(ids)].sort(byId);
    this.ids = sorted;
    this.idSet = new Set(sorted);
    this.filtered = null;
  }

  /** Applies an idempotent diff. Returns the ids actually removed, or null if nothing changed. */
  patch(add: string[], rm: string[]): string[] | null {
    const adds = [...new Set(add)].filter((id) => !this.idSet.has(id));
    const rms = [...new Set(rm)].filter((id) => this.idSet.has(id));
    if (adds.length === 0 && rms.length === 0) return null;
    for (const id of rms) this.idSet.delete(id);
    for (const id of adds) this.idSet.add(id);
    if (adds.length + rms.length > SORT_THRESHOLD) {
      this.ids = [...this.idSet].sort(byId);
    } else {
      const next = this.ids.slice();
      for (const id of rms) next.splice(lowerBound(next, id), 1);
      for (const id of adds) next.splice(lowerBound(next, id), 0, id);
      this.ids = next;
    }
    this.filtered = null;
    return rms;
  }
}
