from src.workers.profile_manager import ProfileManager


def test_profile_clone_skips_session_restore_and_extension_state(tmp_path):
    source_profile = tmp_path / "source-profile"
    dest_profile = tmp_path / "dest-profile"
    source_profile.mkdir()

    (source_profile / "Preferences").write_text("{}", encoding="utf-8")
    (source_profile / "History").write_text("history", encoding="utf-8")

    sessions_dir = source_profile / "Sessions"
    sessions_dir.mkdir()
    (sessions_dir / "Current Session").write_text("restored-tabs", encoding="utf-8")

    extension_state_dir = source_profile / "Extension State"
    extension_state_dir.mkdir()
    (extension_state_dir / "state").write_text("background-worker", encoding="utf-8")

    manager = ProfileManager(
        cleanup_on_exit=False,
        temp_directory=tmp_path / "pm-temp",
    )

    manager._copy_profile_directory(str(source_profile), str(dest_profile))

    assert (dest_profile / "Preferences").exists()
    assert (dest_profile / "History").exists()
    assert not (dest_profile / "Sessions").exists()
    assert not (dest_profile / "Extension State").exists()
