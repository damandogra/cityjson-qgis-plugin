# Export Feature — Development Log

Decisions and dead ends, newest first. Not a release changelog (`Changelog.md` is that, and
gets one entry at PR time). Keep entries short — what changed, why, what's blocked.

---

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
