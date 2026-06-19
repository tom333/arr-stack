export interface ChainHealth { requested: boolean; grabbed: boolean; downloaded: boolean; imported: boolean; in_jellyfin: boolean; }
export interface StallDiagnosis { cause: string; label: string; host: string | null; recoverable: boolean; }
export interface Download {
  infohash: string; name: string; state: string; progress: number;
  category: string | null; tracker: string | null; save_path: string | null;
  content_path: string | null; size: number | null;
  dl_speed: number | null; eta: number | null;
  num_seeds: number | null; num_complete: number | null;
  num_leechs: number | null; num_incomplete: number | null;
  ratio: number | null; added_on: number | null;
  tracker_status: number | null; tracker_msg: string | null; tracker_host: string | null;
  diagnosis: StallDiagnosis | null;
}
export interface Row {
  key: string; title: string; year: number | null; type: "movie" | "series";
  requested_by: string | null; request_status: string | null;
  arr_app: string | null; arr_id: number | null; monitored: boolean | null; has_file: boolean | null; quality: string | null;
  downloads: Download[]; disk_paths: string[]; in_jellyfin: boolean; chain: ChainHealth; flags: string[];
}
export interface Snapshot { rows: Row[]; generated_at: string | null; stale_sources: string[]; initializing: boolean; }

export interface ActionJob { key: string; title: string; app: string; state: "queued" | "running" | "done" | "failed"; message: string | null; started_at: string | null; size_bytes: number | null; }

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

export async function deleteDownload(key: string, infohash: string): Promise<void> {
  const res = await fetch("/api/actions/delete-download", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, infohash, confirm: true }),
  });
  if (!res.ok) throw new Error(`delete-download ${res.status}`);
}

export async function removeStuck(key: string): Promise<void> {
  const res = await fetch("/api/actions/remove", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, confirm: true }),
  });
  if (!res.ok) throw new Error(`remove ${res.status}`);
}

export async function jellyfinScan(key: string): Promise<void> {
  const res = await fetch("/api/actions/jellyfin-scan", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key }),
  });
  if (!res.ok) throw new Error(`jellyfin-scan ${res.status}`);
}
