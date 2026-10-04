from fsffl.product.acceptance_startup import production_acceptance_startup_enabled


def test_customer_cold_start_does_not_run_engineering_acceptance_by_default() -> None:
    assert not production_acceptance_startup_enabled({})
    assert not production_acceptance_startup_enabled(
        {"FSFFL_RUN_RUNTIME_AVAILABILITY_ACCEPTANCE": "1"}
    )
    assert not production_acceptance_startup_enabled(
        {
            "FSFFL_RUN_RUNTIME_AVAILABILITY_ACCEPTANCE": "1",
            "FSFFL_RUN_STATE_FIRST_ACCEPTANCE": "1",
        }
    )


def test_engineering_acceptance_requires_separate_explicit_startup_gate() -> None:
    assert production_acceptance_startup_enabled(
        {
            "FSFFL_ENABLE_PRODUCTION_ACCEPTANCE_STARTUP": "true",
            "FSFFL_RUN_RUNTIME_AVAILABILITY_ACCEPTANCE": "1",
        }
    )
    assert not production_acceptance_startup_enabled(
        {
            "FSFFL_ENABLE_PRODUCTION_ACCEPTANCE_STARTUP": "1",
            "FSFFL_RUN_STATE_FIRST_ACCEPTANCE": "false",
        }
    )
