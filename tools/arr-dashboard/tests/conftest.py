def sources(**overrides):
    base = {
        "radarr_movies": [],
        "sonarr_series": [],
        "radarr_queue": [],
        "sonarr_queue": [],
        "qbit_torrents": [],
        "seerr_requests": [],
        "jellyfin_items": [],
    }
    base.update(overrides)
    return base
