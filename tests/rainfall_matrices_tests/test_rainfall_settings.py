from config import Settings


def test_chirps_collection_comes_from_chirps_id(monkeypatch):
    monkeypatch.setenv("CHIRPS_ID", "UCSB-CHG/CHIRPS/DAILY")
    assert Settings(_env_file=None).chirps_collection == "UCSB-CHG/CHIRPS/DAILY"


def test_chirps_collection_has_a_default(monkeypatch):
    monkeypatch.delenv("CHIRPS_ID", raising=False)
    monkeypatch.delenv("CHIRPS_COLLECTION", raising=False)
    assert Settings(_env_file=None).chirps_collection
