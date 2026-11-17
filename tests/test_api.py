
import pytest
from src import MovieStorage
import main


def test_movies_persist(client, test_storage, uploaded_movies):
    reopened = MovieStorage(test_storage.db_path)
    df = reopened.get()
    assert reopened.count_movies() == 20
    assert len(df) == 20
    assert list(df.columns) == ["title", "release_year", "rating", "genre"]
    assert df["title"].tolist() == [
        "Movie A", "Movie B", "Movie B", "Movie C", "Movie D",
        "Movie D", "Movie E", "Movie F", "Movie G", "Movie H",
        "Movie I", "Movie J", "Movie K", "Movie L", "Movie M",
        "Movie N", "Movie O", "Movie P", "Movie Q", "Movie R",]
    stored = reopened.select_columns(["title"], limit=100)
    stored_ids = [row["id"] for row in stored]

    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    api_ids = [row["id"] for row in response.json()["data"]]

    assert stored_ids == list(range(1, 21))
    assert api_ids == list(range(1, 21))

    # Check 20 rows, all four DataFrame columns, and the original title order.
    # Compare IDs from that object's select_columns() with GET /movies?limit=100.
    # Both should return IDs 1 through 20 in row order.

def test_cache_and_processing(client, uploaded_movies, processing_body):
    # TODO 1: GET /movies with limits 100 and 1.
    # Check 200 and that main.cache.get(limit) equals each response body.
    response_100 = client.get("/movies", params={"limit": 100})
    assert response_100.status_code == 200
    assert main.cache.get(100) == response_100.json()

    response_1 = client.get("/movies", params={"limit": 1})
    assert response_1.status_code == 200
    assert main.cache.get(1) == response_1.json()
    # TODO 2: repeat limit=100 and check the same response.
    repeat = client.get("/movies", params={"limit": 100})
    assert repeat.status_code == 200
    assert repeat.json() == response_100.json()
    # TODO 3: POST /movies/process using json=processing_body.
    # Check 200, zero validation removals, and the 20 -> 16 cleaning report.
    # Confirm both old cache entries are None.
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    assert response.json()["validation_rows_removed"] == 0
    assert response.json()["cleaning_report"]["rows_before"] == 20
    assert response.json()["cleaning_report"]["rows_after"] == 16
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None
    # TODO 4: retrieve again; check total_rows=16 and titles Movie A through Movie P, in order.
#   Check IDs 1 through 16 in the retrieved records.
#   Check that the new response is cached.
    after = client.get("/movies", params={"limit": 100})
    assert after.status_code == 200
    assert after.json()["total_rows"] == 16

    titles = [row["title"] for row in after.json()["data"]]
    assert titles == [
        "Movie A", "Movie B", "Movie C", "Movie D",
        "Movie E", "Movie F", "Movie G", "Movie H",
        "Movie I", "Movie J", "Movie K", "Movie L",
        "Movie M", "Movie N", "Movie O", "Movie P",
    ]

    ids = [row["id"] for row in after.json()["data"]]
    assert ids == list(range(1, 17))

    assert main.cache.get(100) == after.json()


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    first = client.get("/movies", params={"limit": 100})
    assert first.status_code == 200
    def fail_if_called(*args, **kwargs):
        pytest.fail("A cache hit should not query the database").select_columns()
    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)
    second = client.get("/movies", params={"limit": 100})
    assert second.status_code == 200
    assert second.json() == first.json()