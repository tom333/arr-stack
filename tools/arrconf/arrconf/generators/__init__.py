"""Generator module — pure-function resource expansion.

Phase 10 (D-01): Categories → per-app resource lists (qBittorrent, Sonarr,
Radarr, Jellyfin, Seerr animeTags).

Phase 28 (INTENT-02): CrossSeedConfig → config.js JS literal (D-03 proving
slice — demonstrates the generator framework supports non-YAML output formats).

Public API: pure functions only. No I/O, no client calls.
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
from arrconf.generators.intent import generate_cross_seed
from arrconf.generators.sagas import SagasDesiredState, generate_sagas_desired

__all__ = [
    "RadarrDerived",
    "SagasDesiredState",
    "SonarrDerived",
    "generate_anime_tag_labels",
    "generate_cross_seed",
    "generate_jellyfin_libraries",
    "generate_qbit_categories",
    "generate_radarr_resources",
    "generate_sagas_desired",
    "generate_sonarr_resources",
]
