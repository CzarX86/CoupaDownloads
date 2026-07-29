from src.core.eta import AdaptiveEwmaEtaStrategy, ETAEstimator


def test_eta_estimator_stays_in_warmup_before_minimum_completions() -> None:
    estimator = ETAEstimator(strategy=AdaptiveEwmaEtaStrategy())
    estimator.configure_total_items(10)

    for timestamp in (0.0, 30.0, 60.0, 90.0):
        estimator.record_completion(timestamp)

    state = estimator.build_state(processed_items=4, active_items=1, now=120.0)

    assert state.confidence_state == "warming_up"
    assert state.eta_seconds is None
    assert state.eta_display == "calculating"


def test_eta_estimator_becomes_numeric_after_warmup() -> None:
    estimator = ETAEstimator(strategy=AdaptiveEwmaEtaStrategy())
    estimator.configure_total_items(10)

    for timestamp in (0.0, 60.0, 120.0, 180.0, 240.0):
        estimator.record_completion(timestamp)

    state = estimator.build_state(processed_items=5, active_items=1, now=300.0)

    assert state.confidence_state == "stable"
    assert state.eta_seconds is not None
    assert 250.0 <= state.eta_seconds <= 350.0
    assert state.eta_display in {"5m 0s", "4m 59s", "5m 1s"}


def test_eta_estimator_reacts_to_productivity_drop_without_spiking() -> None:
    estimator = ETAEstimator(strategy=AdaptiveEwmaEtaStrategy())
    estimator.configure_total_items(12)

    for timestamp in (0.0, 30.0, 60.0, 90.0, 120.0):
        estimator.record_completion(timestamp)

    baseline = estimator.build_state(processed_items=5, active_items=1, now=150.0)
    estimator.record_completion(300.0)
    dropped = estimator.build_state(processed_items=6, active_items=1, now=330.0)

    assert baseline.eta_seconds is not None
    assert dropped.eta_seconds is not None
    assert dropped.eta_seconds > baseline.eta_seconds
    assert dropped.eta_seconds < baseline.eta_seconds * 1.30


def test_eta_estimator_waits_when_no_active_work_but_items_remain() -> None:
    estimator = ETAEstimator(strategy=AdaptiveEwmaEtaStrategy())
    estimator.configure_total_items(8)

    for timestamp in (0.0, 30.0, 60.0, 90.0, 120.0):
        estimator.record_completion(timestamp)

    state = estimator.build_state(processed_items=5, active_items=0, now=200.0)

    assert state.confidence_state == "volatile"
    assert state.eta_seconds is None
    assert state.eta_display == "waiting"


def test_eta_estimator_keeps_last_eta_during_short_idle_gap() -> None:
    estimator = ETAEstimator(strategy=AdaptiveEwmaEtaStrategy())
    estimator.configure_total_items(8)

    for timestamp in (0.0, 30.0, 60.0, 90.0, 120.0):
        estimator.record_completion(timestamp)

    active_state = estimator.build_state(processed_items=5, active_items=1, now=145.0)
    idle_state = estimator.build_state(processed_items=5, active_items=0, now=126.0)

    assert active_state.eta_seconds is not None
    assert idle_state.confidence_state == "volatile"
    assert idle_state.eta_seconds == active_state.eta_seconds
    assert idle_state.eta_display == active_state.eta_display
