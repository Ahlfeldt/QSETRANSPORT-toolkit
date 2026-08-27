"""Portable geospatial output helpers for local and network-backed projects."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import geopandas as gpd


class GeoPackageWriteError(OSError):
    """Raised when a completed local GeoPackage cannot be published safely."""


def _validate_geopackage(path: Path, *, layer: str, expected_features: int) -> None:
    """Confirm that GDAL can reopen a layer and that no features were lost."""
    check = gpd.read_file(path, layer=layer)
    if len(check) != expected_features:
        raise GeoPackageWriteError(
            f"GeoPackage validation failed for {path}: expected "
            f"{expected_features} features, found {len(check)}."
        )


def write_geopackage(frame: gpd.GeoDataFrame, target: str | Path, *, layer: str) -> Path:
    """Publish a complete GeoPackage without transacting on the project drive.

    GeoPackage is an SQLite container. Some SMB/NFS filesystems cannot reliably
    support its transaction locks. The database is therefore created in the
    operating system's local temporary directory, validated, copied as ordinary
    bytes beside the destination, validated again from the project drive, and
    only then used to replace the previous file.
    """
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    publishing = destination.with_name(
        f".{destination.stem}.{uuid4().hex}.copying{destination.suffix}"
    )

    try:
        with tempfile.TemporaryDirectory(prefix="quetransport_gpkg_") as temp_dir:
            local_file = Path(temp_dir) / destination.name
            frame.to_file(local_file, layer=layer, driver="GPKG")
            _validate_geopackage(local_file, layer=layer, expected_features=len(frame))

            shutil.copyfile(local_file, publishing)
            if publishing.stat().st_size != local_file.stat().st_size:
                raise GeoPackageWriteError(
                    f"Incomplete network copy for {destination}: file sizes differ."
                )
            _validate_geopackage(publishing, layer=layer, expected_features=len(frame))
            os.replace(publishing, destination)
    except Exception as exc:
        try:
            publishing.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, GeoPackageWriteError):
            raise
        raise GeoPackageWriteError(f"Could not write GeoPackage {destination}: {exc}") from exc

    return destination
