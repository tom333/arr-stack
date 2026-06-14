import httpx

from arrconf_mcp import clients
from arrconf_mcp.server import (
    add_movie,
    add_series,
    request_media,
    search_media,
    trigger_search_missing,
)


def _radarr_env(monkeypatch):
    monkeypatch.setenv("RADARR_API_KEY", "rk")
    monkeypatch.setenv("RADARR_URL", "http://radarr.test:7878")


def _sonarr_env(monkeypatch):
    monkeypatch.setenv("SONARR_API_KEY", "sk")
    monkeypatch.setenv("SONARR_URL", "http://sonarr.test:8989")


def test_search_media_movie(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    mock_api.get("http://radarr.test:7878/api/v3/movie/lookup").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"title": "Dune", "year": 2021, "tmdbId": 438631, "overview": "x" * 300},
                {"title": "Dune Part Two", "year": 2024, "tmdbId": 693134, "overview": "y"},
            ],
        )
    )
    out = search_media("dune", "movie")
    assert out[0] == {
        "title": "Dune",
        "year": 2021,
        "tmdbId": 438631,
        "overview": "x" * 200,
    }
    assert len(out) == 2


def test_search_media_series(monkeypatch, mock_api):
    _sonarr_env(monkeypatch)
    clients.reset()
    mock_api.get("http://sonarr.test:8989/api/v3/series/lookup").mock(
        return_value=httpx.Response(
            200,
            json=[{"title": "Frieren", "year": 2023, "tvdbId": 424536, "overview": "z"}],
        )
    )
    out = search_media("frieren", "series")
    assert out[0]["tvdbId"] == 424536
    assert out[0]["title"] == "Frieren"


def test_search_media_caps_at_five(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    mock_api.get("http://radarr.test:7878/api/v3/movie/lookup").mock(
        return_value=httpx.Response(
            200,
            json=[{"title": f"M{i}", "year": 2000 + i, "tmdbId": i} for i in range(10)],
        )
    )
    assert len(search_media("m", "movie")) == 5


def test_add_movie(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    mock_api.get("http://radarr.test:7878/api/v3/qualityprofile").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 1, "name": "MULTi.VF"},
                {"id": 2, "name": "Family"},
            ],
        )
    )
    mock_api.get("http://radarr.test:7878/api/v3/rootfolder").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"path": "/media/films"},
                {"path": "/media/films-family"},
            ],
        )
    )
    mock_api.get("http://radarr.test:7878/api/v3/movie/lookup").mock(
        return_value=httpx.Response(
            200,
            json=[{"title": "Encanto", "tmdbId": 568124, "year": 2021, "images": []}],
        )
    )
    posted = {}

    def _capture(request):
        import json as _json

        posted.update(_json.loads(request.content))
        return httpx.Response(201, json={"id": 99, "title": "Encanto"})

    mock_api.post("http://radarr.test:7878/api/v3/movie").mock(side_effect=_capture)

    out = add_movie(568124, "family")

    assert out == {"title": "Encanto", "id": 99}
    assert posted["qualityProfileId"] == 2  # Family
    assert posted["rootFolderPath"] == "/media/films-family"  # path contains "family"
    assert posted["tmdbId"] == 568124
    assert posted["monitored"] is True
    assert posted["addOptions"] == {"searchForMovie": True}
    assert posted["title"] == "Encanto"


def test_add_movie_general_falls_back_to_first_rootfolder(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    mock_api.get("http://radarr.test:7878/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "MULTi.VF"}])
    )
    mock_api.get("http://radarr.test:7878/api/v3/rootfolder").mock(
        return_value=httpx.Response(
            200, json=[{"path": "/media/films"}, {"path": "/media/films-enfants"}]
        )
    )
    mock_api.get("http://radarr.test:7878/api/v3/movie/lookup").mock(
        return_value=httpx.Response(200, json=[{"title": "Dune", "tmdbId": 438631}])
    )
    mock_api.post("http://radarr.test:7878/api/v3/movie").mock(
        return_value=httpx.Response(201, json={"id": 7, "title": "Dune"})
    )
    out = add_movie(438631, "general")
    assert out == {"title": "Dune", "id": 7}


def test_add_series(monkeypatch, mock_api):
    _sonarr_env(monkeypatch)
    clients.reset()
    mock_api.get("http://sonarr.test:8989/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "name": "Anime"}])
    )
    mock_api.get("http://sonarr.test:8989/api/v3/rootfolder").mock(
        return_value=httpx.Response(200, json=[{"path": "/media/series-zoe"}])
    )
    mock_api.get("http://sonarr.test:8989/api/v3/series/lookup").mock(
        return_value=httpx.Response(
            200, json=[{"title": "Frieren", "tvdbId": 424536, "year": 2023}]
        )
    )
    posted = {}

    def _capture(request):
        import json as _json

        posted.update(_json.loads(request.content))
        return httpx.Response(201, json={"id": 42, "title": "Frieren"})

    mock_api.post("http://sonarr.test:8989/api/v3/series").mock(side_effect=_capture)

    out = add_series(424536, "anime")

    assert out == {"title": "Frieren", "id": 42}
    assert posted["qualityProfileId"] == 3
    assert posted["rootFolderPath"] == "/media/series-zoe"
    assert posted["tvdbId"] == 424536
    assert posted["monitored"] is True
    assert posted["addOptions"] == {"searchForMissingEpisodes": True}


def test_request_media_strips_id(monkeypatch, mock_api):
    monkeypatch.setenv("SEERR_API_KEY", "ek")
    monkeypatch.setenv("SEERR_URL", "http://seerr.test:5055")
    clients.reset()
    posted = {}

    def _capture(request):
        import json as _json

        posted.update(_json.loads(request.content))
        # Seerr echoes back a body that includes a read-only id
        return httpx.Response(201, json={"id": 555, "mediaId": 438631, "status": 1})

    mock_api.post("http://seerr.test:5055/api/v1/request").mock(side_effect=_capture)

    out = request_media(438631, "movie")

    assert posted == {"mediaType": "movie", "mediaId": 438631}
    assert "id" not in out  # read-only id stripped from echoed body
    assert out["mediaId"] == 438631


def test_trigger_search_missing_sonarr(monkeypatch, mock_api):
    _sonarr_env(monkeypatch)
    clients.reset()
    posted = {}

    def _capture(request):
        import json as _json

        posted.update(_json.loads(request.content))
        return httpx.Response(201, json={"name": "MissingEpisodeSearch", "id": 1})

    mock_api.post("http://sonarr.test:8989/api/v3/command").mock(side_effect=_capture)

    out = trigger_search_missing("sonarr")
    assert posted == {"name": "MissingEpisodeSearch"}
    assert out == {"triggered": "MissingEpisodeSearch"}


def test_trigger_search_missing_radarr(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    posted = {}

    def _capture(request):
        import json as _json

        posted.update(_json.loads(request.content))
        return httpx.Response(201, json={"name": "MissingMoviesSearch", "id": 1})

    mock_api.post("http://radarr.test:7878/api/v3/command").mock(side_effect=_capture)

    out = trigger_search_missing("radarr")
    assert posted == {"name": "MissingMoviesSearch"}
    assert out == {"triggered": "MissingMoviesSearch"}
