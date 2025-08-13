import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    root = Path(__file__).parent.parent
    files = os.listdir(root)
    assert "pyproject.toml" in files, "pyproject.toml not found in project root"
    return root


@pytest.fixture
def config_file(project_root: Path) -> Path:
    """Get the path to the config file."""
    config_path = project_root / "config.yml"
    if not config_path.exists():
        pytest.skip("config.yml not found in project root")
    return config_path


@pytest.fixture
def exporter_module_path(project_root: Path) -> Path:
    """Get the path to the exporter module."""
    return project_root / "src" / "pool_exporter" / "exporter.py"


def test_e2e_exporter_loads_config_and_serves_metrics(
    project_root: Path, config_file: Path, exporter_module_path: Path
) -> None:
    """
    Test that exporter.py can load the configuration
    file and serve metrics endpoint.
    """
    # Change to project root directory so config.yml can be found
    original_cwd = os.getcwd()
    try:
        os.chdir(project_root)

        # Run the exporter module as a subprocess
        process = subprocess.Popen(
            [sys.executable, str(exporter_module_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Let it run to allow metrics server to start and collect data
        time.sleep(10)

        # Check if the process is still running (it should be)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(
                f"Process terminated unexpectedly. stdout: {stdout}, stderr: {stderr}"
            )

        try:
            # Test the metrics endpoint
            response = requests.get("http://localhost:8000/metrics", timeout=5)
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to access metrics endpoint: {e}")
        else:
            assert response.status_code == 200, (
                f"Metrics endpoint returned {response.status_code}"
            )
            metrics_content = response.text

            for regex in [
                (
                    r'zurich_pools_water_temperature\{pool_name="Freibad Seebach",'
                    r'pool_uid="SSD-11"\} ([0-9]*\.?[0-9]+)'
                ),
                (
                    r'zurich_pools_max_space\{pool_name="Freibad Seebach",'
                    r'pool_uid="SSD-11"\} ([0-9]*\.?[0-9]+)'
                ),
            ]:
                match = re.search(regex, metrics_content)
                assert match is not None, (
                    f"Expected metric pattern '{regex}' not found in metrics output. "
                    f"Got: {metrics_content}"
                )

        # Terminate the process
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

        # Should see the metrics server startup message
        expected_metrics_msg = "Metrics server started at http://localhost:8000/metrics"
        assert expected_metrics_msg in stderr or expected_metrics_msg in stdout

        assert "WARNING" not in stderr and "WARNING" not in stdout

    finally:
        # Make sure the process is terminated
        if process.poll() is None:
            process.terminate()
            try:
                process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
        os.chdir(original_cwd)
