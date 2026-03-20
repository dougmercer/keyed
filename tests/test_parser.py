from pathlib import Path

from keyed.parser import SceneEvaluator


def test_scene_evaluator_sets_file_globals_for_scene_files(tmp_path: Path) -> None:
    data_path = tmp_path / "snippet.py"
    data_path.write_text("value = 42\n")

    scene_path = tmp_path / "scene.py"
    scene_path.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "from keyed import Scene",
                "",
                'content = Path(__file__).with_name("snippet.py").read_text().strip()',
                "scene = Scene(scene_name=content, num_frames=1, width=10, height=10)",
            ]
        )
    )

    scene = SceneEvaluator().evaluate_file(scene_path)

    assert scene.scene_name == "value = 42"


def test_scene_evaluator_allows_imports_from_scene_directory(tmp_path: Path) -> None:
    helper_path = tmp_path / "helper_module.py"
    helper_path.write_text('SCENE_NAME = "imported helper"\n')

    scene_path = tmp_path / "scene.py"
    scene_path.write_text(
        "\n".join(
            [
                "from helper_module import SCENE_NAME",
                "from keyed import Scene",
                "",
                "scene = Scene(scene_name=SCENE_NAME, num_frames=1, width=10, height=10)",
            ]
        )
    )

    scene = SceneEvaluator().evaluate_file(scene_path)

    assert scene.scene_name == "imported helper"
