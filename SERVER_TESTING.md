# Server testing and shared-drive operation

QUETRANSPORT 0.1.1 can be run from one shared project directory mounted by
Windows or Linux. The toolkit keeps its inputs, configuration, code, and final
outputs on that shared drive. Only intermediate GeoPackage creation uses the
machine's temporary local directory; the completed file is validated and then
published back to the project directory.

This design addresses GeoPackage transaction errors observed when GDAL writes
directly to SMB or NFS storage. It does not create or maintain another copy of
the toolkit.

## Recommended validation on a new machine

1. Install the requirements for the selected toolkit variant.
2. Open that variant's `RUN_QUETRANSPORT.py` in Spyder, or run it with Python
   from the variant directory.
3. Reproduce the included example before changing inputs or configuration.
4. Confirm that the run completes all stages and that the aggregate table,
   location results, diagnostic files, and maps appear under `outputs/`.

The 0.1.1 implementation was validated with complete mixed and Python-only runs
from the same shared deployment on a Windows server, a Linux server, and a
Windows desktop. The economic outputs matched the established reference
outputs; only the intended diagnostic wording and map-legend presentation
differed.

If a run still fails, check that the user can create, replace, and rename files
in both the toolkit's `input/standardized/` and `outputs/` directories and can
write to the operating system's temporary directory.
