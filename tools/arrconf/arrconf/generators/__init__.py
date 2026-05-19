"""Phase 10 generator module — Categories→per-app resource expansion (D-01).

Public API: pure-function generators that take RootConfig and produce typed
lists of per-app resources. No I/O, no client calls.
"""

from arrconf.generators.categories import (
    RadarrDerived,
    SonarrDerived,
    generate_anime_tag_labels,
    generate_jellyfin_libraries,
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)

__all__ = [
    "RadarrDerived",
    "SonarrDerived",
    "generate_anime_tag_labels",
    "generate_jellyfin_libraries",
    "generate_qbit_categories",
    "generate_radarr_resources",
    "generate_sonarr_resources",
]
