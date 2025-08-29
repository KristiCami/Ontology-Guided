import evaluation.repair_efficiency as reff


def test_aggregate_repair_efficiency_with_prompt_data():
    """Ensure mean iterations and bucket distribution are computed correctly."""
    # Simulate outputs from RepairLoop with known prompt stats
    stats_list = [
        {
            "iterations": 1,
            "first_conforms_iteration": 1,
            "prompt_count": 2,
            "prompt_success_rate": 0.5,
        },
        {
            "iterations": 2,
            "first_conforms_iteration": 2,
            "prompt_count": 4,
            "prompt_success_rate": 0.5,
        },
        {
            "iterations": 3,
            "first_conforms_iteration": 3,
            "prompt_count": 6,
            "prompt_success_rate": 0.5,
        },
        {
            "iterations": 4,
            "first_conforms_iteration": 4,
            "prompt_count": 8,
            "prompt_success_rate": 0.5,
        },
    ]

    efficiency = reff.aggregate_repair_efficiency(stats_list)

    assert efficiency.case_count == 4
    assert efficiency.mean_iterations == 2.5
    assert efficiency.distribution == {"1": 1, "2": 1, "3": 1, ">3": 1}
    assert efficiency.avg_prompts_per_iteration == 2.0
    # Success rate cannot be derived from prompt_success_rate alone
    assert efficiency.success_rate_per_prompt is None
