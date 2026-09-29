import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from tfhub_models import get_backbone
from train_tfhub_classifier import balanced_class_weights, parser, resolve_dataset_dirs, should_keep_fine_tuned, training_stages


def test_tfhub_backbones_have_deployable_contracts():
    router = get_backbone("mobilenet_v3_small")
    larger_specialist = get_backbone("mobilenet_v3_large")
    efficientnet_v2 = get_backbone("efficientnet_v2_b0")
    specialist = get_backbone("efficientnet_lite0")
    assert router.image_size == larger_specialist.image_size == efficientnet_v2.image_size == specialist.image_size == 224
    assert router.fine_tune_supported is True
    assert larger_specialist.fine_tune_supported is True
    assert efficientnet_v2.fine_tune_supported is True
    assert specialist.fine_tune_supported is False
    assert router.handle.startswith("https://tfhub.dev/")
    assert larger_specialist.handle.startswith("https://tfhub.dev/")
    assert efficientnet_v2.handle.startswith("https://tfhub.dev/")
    assert specialist.handle.startswith("https://tfhub.dev/")


def test_mobilenet_transfer_learning_warms_head_before_fine_tuning():
    assert training_stages(
        epochs=8,
        head_epochs=2,
        freeze_backbone=False,
        fine_tune_supported=True,
    ) == (2, 6)


def test_frozen_tfhub_backbone_uses_head_only_for_all_epochs():
    assert training_stages(
        epochs=8,
        head_epochs=2,
        freeze_backbone=True,
        fine_tune_supported=True,
    ) == (8, 0)


def test_tfhub_trainer_defaults_to_the_fine_tunable_specialist():
    assert parser().get_default("backbone") == "mobilenet_v3_large"


def test_balanced_class_weights_upweight_the_smaller_class_without_changing_mean_scale():
    weights = balanced_class_weights([100, 25])
    assert weights == {0: 0.625, 1: 2.5}
    assert sum(count * weights[index] for index, count in enumerate([100, 25])) / 125 == 1


def test_fine_tuning_must_not_replace_a_more_accurate_warmup_checkpoint():
    assert should_keep_fine_tuned(warmup_accuracy=0.91, fine_tuned_accuracy=0.92) is True
    assert should_keep_fine_tuned(warmup_accuracy=0.91, fine_tuned_accuracy=0.91) is True
    assert should_keep_fine_tuned(warmup_accuracy=0.91, fine_tuned_accuracy=0.89) is False


def test_tfhub_trainer_accepts_reviewed_validation_name_without_ambiguity(tmp_path):
    (tmp_path / "train").mkdir()
    (tmp_path / "validation").mkdir()
    assert resolve_dataset_dirs(tmp_path) == (tmp_path / "train", tmp_path / "validation")
    (tmp_path / "val").mkdir()
    with pytest.raises(ValueError, match="both val/ and validation"):
        resolve_dataset_dirs(tmp_path)
