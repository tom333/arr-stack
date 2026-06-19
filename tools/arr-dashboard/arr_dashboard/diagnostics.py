from arr_dashboard.models import Download, StallDiagnosis


def diagnose_stall(d: Download) -> StallDiagnosis | None:
    """Classify why a download is not progressing. Returns None when the download is
    progressing (dl_speed > 0), already complete (progress >= 1.0), or has no qBit
    speed signal (dl_speed is None). Pure: no I/O."""
    if d.dl_speed is None or d.dl_speed > 0 or d.progress >= 1.0:
        return None

    if d.state == "metaDL":
        return StallDiagnosis(cause="metadata", label="métadonnées", recoverable=True)
    if d.state == "queuedDL":
        return StallDiagnosis(cause="queued", label="en file qBit", recoverable=True)
    if d.tracker_status == 4 and d.tracker_msg:
        return StallDiagnosis(
            cause="tracker-refused",
            label=f"tracker refuse: {d.tracker_msg}",
            host=d.tracker_host,
            recoverable=True,
        )
    if d.tracker_status in (2, 3) and d.num_complete == 0:
        return StallDiagnosis(cause="no-source", label="aucun seed", recoverable=False)
    return StallDiagnosis(cause="stalled", label="bloqué (cause inconnue)", recoverable=True)
