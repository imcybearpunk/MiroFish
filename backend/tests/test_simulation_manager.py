import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch

from app.services.simulation_manager import (
    SimulationManager,
    SimulationState,
    SimulationStatus,
    PlatformType,
)


@pytest.fixture
def sim_manager(tmp_path):
    """Create a SimulationManager with a temporary data directory."""
    manager = SimulationManager()
    manager.SIMULATION_DATA_DIR = str(tmp_path / "simulations")
    os.makedirs(manager.SIMULATION_DATA_DIR, exist_ok=True)
    return manager


class TestSimulationStatusEnum:
    """Tests for the SimulationStatus enum."""

    def test_simulation_status_enum_values(self):
        """Verify all 8 enum values are correct strings."""
        assert SimulationStatus.CREATED.value == "created"
        assert SimulationStatus.PREPARING.value == "preparing"
        assert SimulationStatus.READY.value == "ready"
        assert SimulationStatus.RUNNING.value == "running"
        assert SimulationStatus.PAUSED.value == "paused"
        assert SimulationStatus.STOPPED.value == "stopped"
        assert SimulationStatus.COMPLETED.value == "completed"
        assert SimulationStatus.FAILED.value == "failed"

    def test_simulation_status_enum_has_eight_members(self):
        """Verify all 8 status values exist."""
        statuses = list(SimulationStatus)
        assert len(statuses) == 8


class TestPlatformTypeEnum:
    """Tests for the PlatformType enum."""

    def test_platform_type_enum(self):
        """Verify twitter and reddit values are correct."""
        assert PlatformType.TWITTER.value == "twitter"
        assert PlatformType.REDDIT.value == "reddit"

    def test_platform_type_enum_has_two_members(self):
        """Verify exactly two platform types exist."""
        platforms = list(PlatformType)
        assert len(platforms) == 2


class TestSimulationStateDefaults:
    """Tests for SimulationState initialization and defaults."""

    def test_simulation_state_defaults(self):
        """Verify default values after construction."""
        state = SimulationState(
            simulation_id="sim_test123",
            project_id="proj_001",
            graph_id="graph_001",
        )

        assert state.simulation_id == "sim_test123"
        assert state.project_id == "proj_001"
        assert state.graph_id == "graph_001"
        assert state.enable_twitter is True
        assert state.enable_reddit is True
        assert state.status == SimulationStatus.CREATED
        assert state.entities_count == 0
        assert state.profiles_count == 0
        assert state.entity_types == []
        assert state.config_generated is False
        assert state.config_reasoning == ""
        assert state.current_round == 0
        assert state.twitter_status == "not_started"
        assert state.reddit_status == "not_started"
        assert state.error is None

    def test_simulation_state_custom_values(self):
        """Verify SimulationState accepts custom values."""
        state = SimulationState(
            simulation_id="sim_custom",
            project_id="proj_custom",
            graph_id="graph_custom",
            enable_twitter=False,
            enable_reddit=True,
            status=SimulationStatus.RUNNING,
            entities_count=50,
            profiles_count=25,
            entity_types=["bot", "user"],
            current_round=5,
        )

        assert state.enable_twitter is False
        assert state.enable_reddit is True
        assert state.status == SimulationStatus.RUNNING
        assert state.entities_count == 50
        assert state.profiles_count == 25
        assert state.entity_types == ["bot", "user"]
        assert state.current_round == 5


class TestSimulationStateSerialization:
    """Tests for SimulationState serialization methods."""

    def test_simulation_state_to_dict_has_all_keys(self):
        """Verify to_dict() contains all expected keys."""
        state = SimulationState(
            simulation_id="sim_001",
            project_id="proj_001",
            graph_id="graph_001",
            entities_count=10,
            profiles_count=5,
            entity_types=["bot"],
            current_round=1,
            twitter_status="active",
            error="test_error",
        )

        state_dict = state.to_dict()

        expected_keys = {
            "simulation_id",
            "project_id",
            "graph_id",
            "enable_twitter",
            "enable_reddit",
            "status",
            "entities_count",
            "profiles_count",
            "entity_types",
            "config_generated",
            "config_reasoning",
            "current_round",
            "twitter_status",
            "reddit_status",
            "created_at",
            "updated_at",
            "error",
        }

        assert set(state_dict.keys()) == expected_keys
        assert state_dict["simulation_id"] == "sim_001"
        assert state_dict["entities_count"] == 10
        assert state_dict["current_round"] == 1
        assert state_dict["error"] == "test_error"

    def test_simulation_state_to_simple_dict_subset(self):
        """Verify to_simple_dict() contains only expected subset of keys."""
        state = SimulationState(
            simulation_id="sim_001",
            project_id="proj_001",
            graph_id="graph_001",
            entities_count=10,
            profiles_count=5,
            entity_types=["bot"],
            config_generated=True,
            current_round=1,
            twitter_status="active",
            error="test_error",
        )

        simple_dict = state.to_simple_dict()

        expected_keys = {
            "simulation_id",
            "project_id",
            "graph_id",
            "status",
            "entities_count",
            "profiles_count",
            "entity_types",
            "config_generated",
            "error",
        }

        assert set(simple_dict.keys()) == expected_keys
        assert simple_dict["simulation_id"] == "sim_001"
        assert simple_dict["entities_count"] == 10
        assert simple_dict["config_generated"] is True
        assert simple_dict["error"] == "test_error"

        # Verify excluded fields are not present
        assert "current_round" not in simple_dict
        assert "twitter_status" not in simple_dict
        assert "reddit_status" not in simple_dict
        assert "created_at" not in simple_dict
        assert "updated_at" not in simple_dict
        assert "config_reasoning" not in simple_dict


class TestSimulationManagerCreation:
    """Tests for SimulationManager.create_simulation()."""

    def test_create_simulation_returns_state(self, sim_manager):
        """Verify create_simulation returns a SimulationState object."""
        result = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        assert isinstance(result, SimulationState)
        assert result.project_id == "proj_001"
        assert result.graph_id == "graph_001"
        assert result.status == SimulationStatus.CREATED

    def test_create_simulation_id_format(self, sim_manager):
        """Verify simulation_id starts with 'sim_'."""
        result = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        assert result.simulation_id.startswith("sim_")
        # Verify it's a valid format: sim_XXXX where X is hex
        sim_id_suffix = result.simulation_id[4:]  # Remove 'sim_' prefix
        assert len(sim_id_suffix) == 12
        assert all(c in "0123456789abcdef" for c in sim_id_suffix)

    def test_create_simulation_saves_to_disk(self, sim_manager):
        """Verify state.json file exists after creation."""
        result = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        state_file = Path(sim_manager.SIMULATION_DATA_DIR) / result.simulation_id / "state.json"
        assert state_file.exists()

        # Verify the file contains valid JSON
        with open(state_file, "r") as f:
            saved_data = json.load(f)

        assert saved_data["simulation_id"] == result.simulation_id
        assert saved_data["project_id"] == "proj_001"
        assert saved_data["graph_id"] == "graph_001"

    def test_create_simulation_with_platform_flags(self, sim_manager):
        """Verify create_simulation respects platform enable flags."""
        result = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
            enable_twitter=False,
            enable_reddit=True,
        )

        assert result.enable_twitter is False
        assert result.enable_reddit is True

    def test_create_simulation_unique_ids(self, sim_manager):
        """Verify each created simulation has a unique ID."""
        result1 = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )
        result2 = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        assert result1.simulation_id != result2.simulation_id


class TestSimulationManagerRetrieval:
    """Tests for SimulationManager.get_simulation()."""

    def test_get_simulation_returns_none_for_missing(self, sim_manager):
        """Verify non-existent ID returns None."""
        result = sim_manager.get_simulation("sim_nonexistent")
        assert result is None

    def test_get_simulation_loads_saved_state(self, sim_manager):
        """Verify create then get returns matching simulation state."""
        created = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        retrieved = sim_manager.get_simulation(created.simulation_id)

        assert retrieved is not None
        assert retrieved.simulation_id == created.simulation_id
        assert retrieved.project_id == created.project_id
        assert retrieved.graph_id == created.graph_id
        assert retrieved.status == created.status

    def test_get_simulation_preserves_all_fields(self, sim_manager):
        """Verify get_simulation preserves all fields from saved state."""
        created = sim_manager.create_simulation(
            project_id="proj_test",
            graph_id="graph_test",
            enable_twitter=False,
            enable_reddit=True,
        )

        # Manually update the saved state with more data
        state_file = (
            Path(sim_manager.SIMULATION_DATA_DIR)
            / created.simulation_id
            / "state.json"
        )
        with open(state_file, "r") as f:
            state_data = json.load(f)

        state_data["entities_count"] = 42
        state_data["current_round"] = 3
        state_data["status"] = "running"

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        retrieved = sim_manager.get_simulation(created.simulation_id)

        assert retrieved.entities_count == 42
        assert retrieved.current_round == 3
        assert retrieved.status == SimulationStatus.RUNNING


class TestSimulationManagerList:
    """Tests for SimulationManager.list_simulations()."""

    def test_list_simulations_empty(self, sim_manager):
        """Verify empty data dir returns empty list."""
        result = sim_manager.list_simulations()
        assert result == []

    def test_list_simulations_returns_created(self, sim_manager):
        """Verify list_simulations returns created simulations."""
        created = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        result = sim_manager.list_simulations()

        assert len(result) == 1
        assert result[0].simulation_id == created.simulation_id
        assert result[0].project_id == "proj_001"

    def test_list_simulations_multiple(self, sim_manager):
        """Verify list_simulations returns multiple simulations."""
        sim1 = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )
        sim2 = sim_manager.create_simulation(
            project_id="proj_002",
            graph_id="graph_002",
        )
        sim3 = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_003",
        )

        result = sim_manager.list_simulations()

        assert len(result) == 3
        sim_ids = {sim.simulation_id for sim in result}
        assert sim_ids == {sim1.simulation_id, sim2.simulation_id, sim3.simulation_id}

    def test_list_simulations_filters_by_project(self, sim_manager):
        """Verify list_simulations filters by project_id when provided."""
        sim1 = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )
        sim2 = sim_manager.create_simulation(
            project_id="proj_002",
            graph_id="graph_002",
        )
        sim3 = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_003",
        )

        result = sim_manager.list_simulations(project_id="proj_001")

        assert len(result) == 2
        sim_ids = {sim.simulation_id for sim in result}
        assert sim_ids == {sim1.simulation_id, sim3.simulation_id}

        # Verify all returned sims have correct project_id
        for sim in result:
            assert sim.project_id == "proj_001"

    def test_list_simulations_filter_returns_empty(self, sim_manager):
        """Verify list_simulations returns empty list for non-matching project_id."""
        sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        result = sim_manager.list_simulations(project_id="proj_nonexistent")

        assert result == []


class TestSimulationManagerProfiles:
    """Tests for SimulationManager.get_profiles()."""

    def test_get_profiles_returns_empty_list_when_no_file(self, sim_manager):
        """Verify get_profiles returns empty list when profile file doesn't exist."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        result = sim_manager.get_profiles(sim.simulation_id)

        assert result == []

    def test_get_profiles_raises_for_missing_sim(self, sim_manager):
        """Verify get_profiles raises ValueError for unknown simulation_id."""
        with pytest.raises(ValueError):
            sim_manager.get_profiles("sim_nonexistent")

    def test_get_profiles_loads_existing_file(self, sim_manager):
        """Verify get_profiles loads and returns profiles from file."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        # Create a profiles file
        profiles_data = [
            {"id": "user_1", "platform": "reddit", "name": "User1"},
            {"id": "user_2", "platform": "reddit", "name": "User2"},
        ]

        sim_dir = Path(sim_manager.SIMULATION_DATA_DIR) / sim.simulation_id
        profiles_file = sim_dir / "profiles.json"

        with open(profiles_file, "w") as f:
            json.dump(profiles_data, f)

        result = sim_manager.get_profiles(sim.simulation_id)

        assert len(result) == 2
        assert result[0]["id"] == "user_1"
        assert result[1]["name"] == "User2"

    def test_get_profiles_with_platform_filter(self, sim_manager):
        """Verify get_profiles can filter by platform."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        # Create a profiles file with mixed platforms
        profiles_data = [
            {"id": "user_1", "platform": "reddit", "name": "RedditUser"},
            {"id": "user_2", "platform": "twitter", "name": "TwitterUser"},
        ]

        sim_dir = Path(sim_manager.SIMULATION_DATA_DIR) / sim.simulation_id
        profiles_file = sim_dir / "profiles.json"

        with open(profiles_file, "w") as f:
            json.dump(profiles_data, f)

        # Get reddit profiles
        result = sim_manager.get_profiles(sim.simulation_id, platform="reddit")

        assert len(result) == 1
        assert result[0]["platform"] == "reddit"


class TestSimulationManagerConfig:
    """Tests for SimulationManager.get_simulation_config()."""

    def test_get_simulation_config_returns_none_when_missing(self, sim_manager):
        """Verify get_simulation_config returns None if config file doesn't exist."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        result = sim_manager.get_simulation_config(sim.simulation_id)

        assert result is None

    def test_get_simulation_config_loads_existing_file(self, sim_manager):
        """Verify get_simulation_config loads and returns config from file."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        config_data = {
            "simulation_id": sim.simulation_id,
            "platforms": {"reddit": True, "twitter": True},
            "rounds": 10,
            "entity_types": ["bot", "user"],
        }

        sim_dir = Path(sim_manager.SIMULATION_DATA_DIR) / sim.simulation_id
        config_file = sim_dir / "config.json"

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        result = sim_manager.get_simulation_config(sim.simulation_id)

        assert result is not None
        assert result["simulation_id"] == sim.simulation_id
        assert result["rounds"] == 10
        assert result["platforms"]["reddit"] is True


class TestSimulationManagerRunInstructions:
    """Tests for SimulationManager.get_run_instructions()."""

    def test_get_run_instructions_returns_dict(self, sim_manager):
        """Verify get_run_instructions returns a dict with expected keys."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        result = sim_manager.get_run_instructions(sim.simulation_id)

        assert isinstance(result, dict)
        expected_keys = {"simulation_dir", "scripts_dir", "config_file", "commands", "instructions"}
        assert set(result.keys()) == expected_keys

    def test_get_run_instructions_paths_are_correct(self, sim_manager):
        """Verify get_run_instructions returns correct paths."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        result = sim_manager.get_run_instructions(sim.simulation_id)

        sim_dir = Path(sim_manager.SIMULATION_DATA_DIR) / sim.simulation_id
        assert result["simulation_dir"] == str(sim_dir)
        assert result["scripts_dir"] == str(sim_dir / "scripts")
        assert result["config_file"] == str(sim_dir / "config.json")

    def test_get_run_instructions_commands_is_list(self, sim_manager):
        """Verify get_run_instructions returns commands as a list."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        result = sim_manager.get_run_instructions(sim.simulation_id)

        assert isinstance(result["commands"], list)

    def test_get_run_instructions_instructions_is_string(self, sim_manager):
        """Verify get_run_instructions returns instructions as a string."""
        sim = sim_manager.create_simulation(
            project_id="proj_001",
            graph_id="graph_001",
        )

        result = sim_manager.get_run_instructions(sim.simulation_id)

        assert isinstance(result["instructions"], str)
