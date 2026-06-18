export interface ChainHealth { requested: boolean; grabbed: boolean; downloaded: boolean; imported: boolean; in_jellyfin: boolean; }
export interface Download { infohash: string; name: string; state: string; progress: number; category: string | null; tracker: string | null; save_path: string | null; size: number | null; }
export interface Row {
  key: string; title: string; year: number | null; type: "movie" | "series";
  requested_by: string | null; request_status: string | null;
  arr_app: string | null; arr_id: number | null; monitored: boolean | null; has_file: boolean | null; quality: string | null;
  downloads: Download[]; disk_paths: string[]; in_jellyfin: boolean; chain: ChainHealth; flags: string[];
}
export interface Snapshot { rows: Row[]; generated_at: string | null; stale_sources: string[]; initializing: boolean; }

export interface ActionJob { key: string; title: string; app: string; state: "queued" | "running" | "done" | "failed"; message: string | null; }

export async function getDashboard(): Promise<Snapshot> {
  const res = await fetch("/api/dashboard");
  if (!res.ok) throw new Error(`dashboard ${res.status}`);
  return res.json();
}

export async function postImport(key: string): Promise<ActionJob> {
  const res = await fetch("/api/actions/import", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, confirm: true }),
  });
  if (!res.ok) throw new Error(`import ${res.status}`);
  return res.json();
}

export async function getActions(): Promise<ActionJob[]> {
  const res = await fetch("/api/actions");
  if (!res.ok) throw new Error(`actions ${res.status}`);
  return res.json();
}
