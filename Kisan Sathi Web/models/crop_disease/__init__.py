"""Offline-first crop-disease model registry and inference subsystem.

`VERIFIED_DOWNLOADABLE` means the upstream source/artifact is known and can be
cached locally. It never means agronomist approval or Indian field validation.
"""

from .router import CropDiseaseRouter

__all__ = ["CropDiseaseRouter"]
