export interface ChainHealth { requested: boolean; grabbed: boolean; downloaded: boolean; imported: boolean; in_jellyfin: boolean; }
export interface Download { infohash: string; name: string; state: string; progress: number; category: string | null; tracker: string | null; save_path: string | null; }
export interface Row {
  key: string; title: string; year: number | null; type: "movie" | "series";
  requested_by: string | null; request_status: string | null;
  arr_app: string | null; monitored: boolean | null; has_file: boolean | null; quality: string | null;
  downloads: Download[]; disk_paths: string[]; in_jellyfin: boolean; chain: ChainHealth; flags: string[];
}
export interface Snapshot { rows: Row[]; generated_at: string | null; stale_sources: string[]; initializing: boolean; }

export async function getDashboard(): Promise<Snapshot> {
  const res = await fetch("/api/dashboard");
  if (!res.ok) throw new Error(`dashboard ${res.status}`);
  return res.json();
}
