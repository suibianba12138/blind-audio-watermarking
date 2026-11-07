from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github/workflows/v3-container-ci.yml"


def _job_body(workflow: str, job: str) -> str:
    lines = workflow.splitlines()
    marker = f"  {job}:"
    assert marker in lines, f"missing CI job {job}"
    start = lines.index(marker) + 1
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("  ") and not lines[index].startswith("    ")),
        len(lines),
    )
    return "\n".join(lines[start:end])


def test_v3_and_v4_tests_use_separate_jobs_and_docker_keeps_v3_gate() -> None:
    workflow = WORKFLOW.read_text()
    v3 = _job_body(workflow, "v3_unit")
    v4 = _job_body(workflow, "v4_unit")
    docker = _job_body(workflow, "docker")

    assert "tests/test_v3_api_behavior.py" in v3
    assert "tests/test_v4_p4_audio_processing.py" not in v3
    assert "-r requirements-v4-dev.txt" in v4
    assert "V3_SOURCE_ROOT: ${{ github.workspace }}" in v4
    assert "PYTHONPATH=src:. pytest -q" in v4
    assert "tests/test_v4_p4_audio_processing.py" in v4
    assert "SILENTCIPHER_SOURCE_ROOT" not in v4
    assert "needs: v3_unit" in docker
    assert "needs: v4_unit" not in docker
