# Future Capabilities — architectural paths

None of these are implemented. Each entry says where it would attach to
the current architecture so that today's decisions do not close the door.

| Capability | Attaches to | Path |
|---|---|---|
| CAD integration (FreeCAD scripting, Fusion/SolidWorks exports) | `Attachment(kind=CAD)` on `ComponentRevision` | A `cad/` module that ingests STEP/DXF, extracts metadata (bounding box, mass properties) into `ComponentRevision.dimensions`, and links the generating file by SHA-256. FreeCAD runs as a separate worker process invoked by a script, not inside the API. |
| Automatic drawing metadata extraction | `Attachment(kind=DRAWING)` | Title-block parsing of PDFs/DXF on upload; results proposed, not written, until confirmed. |
| Timegrapher automatic ingestion | `TestRun` / `Measurement` | An importer per device format (CSV, serial, screenshot OCR) producing `TIMEGRAPHER` measurements. The `TestType` payload schema is the contract. |
| Digital caliper / metrology ingestion | `Measurement(DIMENSIONAL_INSPECTION)` | Same importer pattern; USB/serial bridge script posts to `POST /measurements`. |
| Microscope image analysis, computer-vision inspection | `Attachment(kind=PHOTO)` + `TestRun(VISUAL_INSPECTION)` | Vision jobs read attachments through `FileStorage`, write findings as measurements with a `model_version` in the payload. |
| AI engineering assistant ("why does P017 have lower amplitude than P016?") | Everything | The data model already links prototype → build record → part instances → revisions → measurements → experiments. The assistant is a read-only tool-using agent over the REST API plus a `GET /prototypes/{id}/dossier` endpoint that assembles the full digital thread in one document. Environmental conditions live on `TestRun.conditions`. |
| AI-assisted failure analysis | `Nonconformance`, `Issue`, `TestRun` | Same agent; adds a `Nonconformance` module first. |
| CNC job tracking, manufacturing travelers, MES | `ProcessRoute`, `PartInstance` | A `manufacturing/` module: `ManufacturingOrder` → `Operation` rows following a `ProcessRoute`; each `PartInstance` gets a traveler = its operation history. |
| QR codes on parts and trays | `PartInstance.identifier`, `Prototype.identifier` | QR encodes the human identifier and a URL; a scan page resolves identifier → record. |
| Supplier RFQs, inventory, cost accounting | `Supplier`, `ComponentRevision`, `PartInstance` | `procurement/` module: `Rfq`, `Quote`, `PurchaseOrder`, `StockLocation`, `StockMove`. Costs roll up through the BOM resolver. |
| Watch service records, customer ownership, certificates, public provenance pages | `Watch` | `ownership/` and `service/` modules; a public read-only site renders a redacted dossier per serial; certificate PDFs generated from build record + final test run. |
| Statistical process control, tolerance analysis | `Measurement`, `ComponentRevision.tolerances` | Analytics module reading measurements by test type and component revision; SPC charts in the web app; tolerance stack-ups from `dimensions`/`tolerances` JSON. |
| Movement simulation, gear-train calculators, mainspring sizing, escapement geometry | `Caliber.specification` | A pure-Python `horology/` package (no DB dependency) with functions over caliber specification; exposed as `POST /calibers/{id}/calculations/*`. Tooth counts and pinion counts already have a home in `specification`. |
| Full audit log | `AuditMixin` | Row-level history table populated by a SQLAlchemy `after_flush` listener, or Postgres triggers. The `created_by/updated_by` primitives and `Actor` boundary are already in place. |
| Authentication and users | `core/auth.py` | Replace `get_actor()` with a token-validating dependency; add a `users` table; `Actor.id` becomes the user id. Nothing else changes. |
| Object storage | `core/storage.py` | `S3FileStorage` / `AzureBlobFileStorage` implementing the same interface, selected by `NEMETH_STORAGE_BACKEND`. |
| Portfolio site integration (arthurnemeth.com) | Public read API | A small read-only, cache-friendly endpoint set (`/public/watches/{serial}`, `/public/calibers/{id}`) returning a redacted subset, consumed by the portfolio site at build time. |
