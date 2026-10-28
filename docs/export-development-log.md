# Export Feature — Development Log

Decisions and dead ends, newest first. Not a release changelog (`Changelog.md` is that, and
gets one entry at PR time). Keep entries short — what changed, why, what's blocked.

---

## 2026-10-28 — X9: geometry checker and 3D BAG baseline

- `scripts/check_geometry.py`: flags non-planar, degenerate and self-intersecting
  faces in a CityJSON file. 30 tests in `tests/test_check_geometry.py`, no QGIS needed.
- Planarity: Newell normal + centroid, max corner distance to the plane.
  Default tolerance 1 cm = val3dity `planarity_d2p_tol` default; report also
  counts at 1 mm and 5 cm. Known limit: one corner lifted by h shows as ≈ h/4.
- Baseline, unedited 3D BAG tile `10-284-560` (23,156 faces):
  - non-planar: 0 > 1 cm, 16 > 1 mm, worst 0.35 cm
  - degenerate (repeated corner): 18 faces in 5 buildings
  - self-intersecting (touching edges): 1 face in 1 building
- Cross-checked against the tile's own `b3_val3dity_lod22`: every flagged face
  is in a building val3dity also flags (102 / 104), no false alarms.
  Missed: 2 buildings with 102 (val3dity likely snaps corners within 1 mm; the
  checker uses exact equality), and shell-level 302/303 (out of scope, the
  checker works per face).
- **Clean at 1 cm**, so any non-planar face after a QGIS edit is caused by the edit.
- Next: the experiment. Load this tile in QGIS, do the 4 edits, check each.


## 2026-10-25 — X6: one object, many rows

- **Problem:** one CityObject can become several QGIS rows (per LoD via
  `LodFeatureDecorator`, per face via `SemanticSurfaceFeatureDecorator`). Export only
  collected uids, so it couldn't tell which LoD or how many faces were deleted.
- `_count_rows()`: `{(uid, lod): n}`, `lod = None` when the layer has no `lod` field.
  `get_surviving_ids()` now reads its uids from it.
- **Rule 1 (LoD rows):** the object survives if any row survives; geometry entries whose
  LoD was loaded but lost its row are dropped, before `process_geometry`. Skipped when
  `lod_as="NONE"` (no `lod` field). LoD compared as `str()`, since the field is text and
  CityJSON 1.0 stores numbers.
- **Rule 2 (surface rows):** new `semantic_surfaces=False` flag; the layers don't show
  whether surfaces were split into rows (no `surface.*` fields if the model has no
  surface attributes), so the caller must say so. `_check_surface_rows()` compares rows
  to faces in the original: all gone → dropped, none missing → kept, some missing →
  `ValueError` naming the object. Runs before any copying.
- Faces counted with `read_boundaries(boundaries, None, None)` (index-only), not
  `get_polygons`: with the exporter's empty `VerticesCache`, `get_polygons` swallows the
  `IndexError` and returns 0. `GeometryInstance` counted via its template. Expected is
  at least 1, matching the loader's `len(polygons) > 1` split.
- Objects without a `geometry` key no longer get `"geometry": []` added (fixed in the
  X7b drop loop too).
- **Known behaviour:** a parent whose row was deleted but whose child survives is kept,
  with its loaded geometry dropped.
- **Still open:** pass `semantic_surfaces` from the UI or Processing algorithm (X14, X15).
- **Tests:** (a) delete house_a's LoD1 row → only LoD2 kept, house_b untouched;
  (b) delete one surface row of building1 → raises; (c) delete all of building2's
  surface rows → building2 dropped, building1 kept. Helpers `_delete_lod_row`,
  `_delete_all_rows`.
- 268 passed.


## 2026-10-24 — X7: fidelity test

- `_cube_solid(first_vertex)` + `_fidelity_citymodel()`: building1 = LoD2 Solid with
  semantics + material 1, plus LoD1 MultiSurface; building2 = same shape, material 0.
  Two materials, metadata.
- Test: load `lod="2"`, delete building2, export with `loaded_lod="2"`. Passed with no
  exporter changes: Solid kept (1 shell, 6 faces), semantics unchanged, materials reduced
  to the used one and renumbered 1 → 0, unloaded LoD1 kept, metadata unchanged.
- Covers the appearance / metadata branches of `export()` flagged as unexercised on 19 Oct.
- cjval: 100% valid.
- Geometry not checked with val3dity: export copies it verbatim, so it would only test the
  fixture. Use val3dity from X9 onward, when export changes coordinates.
- Regression net for X10–X13.
- 265 passed.


## 2026-10-23 — X7b: unloaded LoDs on export

- **Problem:** loading at one LoD (e.g. `lod="1"`) skips objects with no geometry at that
  LoD (`core/loading.py:182`), so they never get a QGIS row. Export treated "no row" as
  "deleted", so a LoD2-only object (e.g. a tree) was silently dropped, while unloaded
  LoDs of loaded objects were kept. Inconsistent, and the user never deleted it.
- **Fix (export-side only):** `CityJSONExporter` takes `loaded_lod` (default `"All"`) and
  `keep_unloaded` (default `True`). It re-checks each object with the loader's own
  `GeometryReader.has_lod()`:
  - has loaded LoD + no row → deleted by user → dropped
  - no loaded LoD → never loaded → kept if `keep_unloaded`, else dropped
- **Drop mode** also removes unloaded geometry entries from surviving objects, before
  `process_geometry`, so their vertices are compacted out.
- Commits: `719eb4c` (keep), `2849ddb` (drop).
- **Tests:** fixture `_unloaded_lod_citymodel()` (house_a, house_b: LoD1+LoD2; tree:
  LoD2 only). Keep test: tree kept, house_b gone, house_a has 2 LoDs. Drop test: tree
  gone, house_a only LoD1. Load via `loader.load()`, not manual `add_object`, or the
  skip at line 182 is bypassed.
- **Gotcha:** `has_lod` matches exactly `"All"`; a default of `"ALL"` resurrected every
  deleted object (3 tests failed).
- 264 passed.
- **Next:** `loaded_lod` / `keep_unloaded` need to be exposed in the UI (X14 parameter,
  X15 dialog); run cjval on both outputs.



## 2026-10-19 — X8: cjval validation

- Validated round-trip output (two cubes, building2 deleted) at validator.cityjson.org (cjval WASM, schemas v2.0.2).
- Output: 100% valid — no errors, no warnings. `unused vertices` clean → `process_geometry` compaction works.
- Input fixture: valid, 4 `duplicate vertices` warnings — the cubes share a face at x=1000 and `_cube_vertices` writes each cube's corners separately. Fixture quirk, not exporter.
- Exporter doesn't dedup; it inherits whatever the original had.
- Limits: cjval checks schema/structure only, not geometry (planarity, solids → val3dity). Fixture has no Solids/semantics/appearance, so those checks weren't exercised.
- Next: re-run on X7's fixture once it exists.


## 2026-10-19 — X4 and X5 done, tests repaired

- X4: export() deepcopies each surviving CityObject (`5e79164`, 23 Sept).
  get_subset_cotype assigns by reference and process_geometry rewrites
  indices in place, so without it export corrupts the live model.
- X4 test: delete building1, export twice, assert both outputs equal and
  the original unchanged. Verified red with the deepcopy removed.
  Needed the delete — with both cubes surviving, indices 0-15 compact onto
  0-15 and the bug is invisible.
- X5: apply_attribute_edits only writes a field if it differs from the
  stringified original, so untouched values keep their type (int stays int,
  missing stays missing). Edited dicts/lists go through json.loads; invalid
  JSON raises ValueError naming the object and field.
- Fixed in exporting.py: uid lookup ran before its `in` guard.
- Fixed in test_export.py: one test was nested inside another and never
  ran; attribute test used `f["uid"] = ...` (assignment) instead of `==`.
- 262 passed.

Still open:
- transform and metadata are copied by reference (harmless today).
- Coverage: appearance / metadata / geometry-templates branches in export()
  are never exercised. That's X7.
- Parent resurrection one level deep, process_templates KeyError on
  geometry-less objects (from 20 Sept) — unchanged.
- Correction: the 2026-08-13 entry says `cityjson-writter-copy`; the branch
  is `cityjson-export`.



## 2026-09-20 — X3 done, round-trip green

- export() builds the subset: createCityJSON, copy version/transform, copy
  surviving CityObjects, then process_geometry / process_templates /
  process_appearance, then metadata. Mirrors get_subset_cotype.
- Guarded process_templates behind "geometry-templates" in citymodel, and
  dropped the empty `subset_cm["appearance"] = {}` line — process_appearance
  uses setdefault. Both are deliberate divergences from get_subset_cotype.
- prune_dangling_children: filters each surviving object's "children" down to
  surviving ids, deletes the key when empty. Only children — get_surviving_ids
  already resurrects parents, so a parents filter is dead code today.
- First round-trip assertion (only checked CityObjects keys) passed with
  vertices == []. Added `len(output["vertices"]) == 8` to make the test
  actually prove something.
- 256 passed.

Open gaps found while building this:
- deepcopy (X4) is now more urgent: prune deletes keys from CityObject dicts
  shared with self.citymodel, so export mutates the live model's structure,
  not just its indices.
- Parent resurrection in get_surviving_ids is one level deep — it loops a
  snapshot (`list(uids)`), so a resurrected parent's own parents are never
  walked. Building -> BuildingPart -> BuildingInstallation leaves a dangling
  "parents" ref. Fix transitively, or add the parents filter as a net.
- process_templates does j2["CityObjects"][each]["geometry"] with no .get() —
  KeyError on a CityObject with no geometry, which the spec allows.


## 2026-09-09 — Phase 1 done (C0.2, C1.1, C1.2, C1.3)

- Synced with upstream (now at v1.0.1). Merged writter + develop into
  cityjson-export, no conflicts.
- Built the fixture in tests/test_export.py: two Buildings, MultiSurface
  cubes, 16 quantized vertices, scale 0.001. Imports as 1 layer / 2 features.
- Round-trip test written and failing on purpose:
  ModuleNotFoundError: No module named 'core.exporting'. Committed red.
- API now pinned by its first caller: CityJSONExporter(layers, citymodel=...)
  .export() -> dict, and save_cityjson_model(dict, path).

Next: C2.1, the vertices writer — inverse of VerticesCache.


## 2026-08-13

Branch: `cityjson-writter-copy`

**Done**

- Branch set up off `cityjson-writter`; fork + local synced with upstream.
- Repo symlinked into the QGIS plugin dir — edits run live.
- Confirmed the export dialog loads on the post-restructure codebase. Was untested.

**Decided**

- Build on `cityjson-writter`: Gina merged `develop` into it on 7 Aug (`98d21c2`), so it's
  `develop` + 7 scaffold files. Verified — zero `develop` commits missing.
- One branch for the whole feature. The work is sequential (serializer needs
  `GeometryWriter`), so stacked branches would be overhead.
- Don't touch `Changelog.md` until PR — it's a release log, edits conflict on every release.

**Corrected**

- Single-polygon features aren't dropped by `SemanticSurfaceFeatureDecorator` — they land
  with **null geometry** (`setGeometry` never called).
- The `# TODO: This is wrong!` is about the dict value being a bare polygon instead of a
  geometry, not about the missing `semantic.values` index.

**Open**

- Is Gina still on `cityjson-writter`? Collision risk.
- Processing algorithm as well as the menu action?
- Are QGIS-authored new CityObjects in scope?
- `resources.py` generated but missing from `.gitignore`. Left for now.

**Next**

- Round-trip test as spec: import → delete one CityObject → export → re-import → assert
  only that object is gone.

---