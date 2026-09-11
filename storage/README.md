# storage/

Engineering file storage for local development. This directory is the root
of the `LocalFileStorage` backend (see ADR-003). Only this README and the
`.gitkeep` files are tracked; everything else is data.

| Folder | Contents |
|---|---|
| `cad/` | STEP, STL, native CAD exports |
| `drawings/` | PDF, DXF, DWG drawings |
| `photos/` | Photos, microscope images |
| `test-results/` | Timegrapher exports, CSV, JSON |
| `manufacturing/` | CAM programs, setup sheets, travelers |
| `certificates/` | Material certs, plating certs, final certificates |

Files are written by the API under server-generated keys
(`{category}/{yyyy}/{mm}/{uuid}{ext}`); do not rely on human-readable
names here. The database holds the original filename, SHA-256 and the
linked entity.

Back this directory up together with the database. In production the same
interface points at object storage.
