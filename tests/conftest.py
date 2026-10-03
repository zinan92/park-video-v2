import pytest


@pytest.fixture(autouse=True)
def _no_user_defaults(tmp_path, monkeypatch):
    """测试不读 Park 机器上 ~/.config/park-video-v2/defaults.yaml。"""
    monkeypatch.setenv("PV2_USER_DEFAULTS", str(tmp_path / "user-defaults.yaml"))
