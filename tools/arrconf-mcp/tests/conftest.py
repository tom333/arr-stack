import pytest
import respx


@pytest.fixture
def mock_api():
    with respx.mock(assert_all_called=False) as router:
        yield router
