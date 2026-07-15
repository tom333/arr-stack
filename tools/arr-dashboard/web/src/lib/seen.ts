const KEY = "arrkestra.seen.releases";

function load(): Set<string> {
  try {
    const raw = localStorage.getItem(KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

let seen: Set<string> = load();

export function isSeen(id: string): boolean {
  return seen.has(id);
}

export function markSeen(id: string): void {
  if (seen.has(id)) return;
  seen.add(id);
  try {
    localStorage.setItem(KEY, JSON.stringify([...seen]));
  } catch {
    /* quota/full — ignore, in-memory set still works this session */
  }
}

/** Snapshot the currently-seen ids (used for deferred filtering). */
export function seenSnapshot(): Set<string> {
  return new Set(seen);
}
