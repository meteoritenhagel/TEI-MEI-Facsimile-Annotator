# TEI/MEI Facsimile Annotator

Annotating facsimile page images with rectangular zones for TEI/MEI export. Documents are saved as a single
`.fca` file containing msgpack-encoded nested document, surface, and zone data.

## Install Dependencies

```bash
pip install -e .
```

## Run

```bash
python -m app.main
```

## Developer Information

### Install Dependencies (Including Dev Dependencies)

```bash
pip install -e .[dev]
```

### Test

```bash
pytest
```

### Architecture

The app uses MVVM adapted for Qt Widgets, with service and repository layers:

```text
Widgets -> Services -> ViewModels -> Qt signals -> Widgets
```

Widgets never mutate viewmodels directly. They call service methods in response to user actions, then update from
viewmodel or service signals. Services are the only layer that writes observable state.

Models in `app/models/document.py` are frozen dataclasses for persisted content only: `Document`, `Surface`, and `Zone`.
They have no Qt imports and no derived fields.

Viewmodels in `app/viewmodels/` represent the whole observable application state, including transient UI state such as
`selected_zone_index`, `dirty`, and `file_path`. Viewmodels never store model instances as fields; they contain other
viewmodels (`DocumentViewModel` -> `SurfaceViewModel` -> `ZoneViewModel`).

Model/viewmodel conversion lives in `app/services/mapping_service.py` and is called only by services. Mapping functions
touch only persistable fields. Transient viewmodel fields, including `selected_zone_index`, are not persisted and are
not modified by mapping.

### Signal Scope

Signals fire at the narrowest scope that changed:

- Updating one zone rectangle emits only that `ZoneViewModel.rect_changed`.
- Adding, removing, or reordering zones emits only the owning `SurfaceViewModel.zones_changed`.
- Adding, removing, reordering pages, or opening a new document emits `DocumentViewModel.surfaces_changed`.

This keeps the UI from rebuilding unrelated page and zone objects when only one nested item changed.

### Persistence

`DocumentRepository` is stateless. It loads and saves explicit paths only, and it does not drive UI state. Saves are
atomic: data is packed with `msgpack`, written to a sibling `.tmp` file, then replaced into place.

### XML IDs

`xml:id` values are never stored in the model, viewmodel, or `.fca` file. They are derived on demand by `XmlIdService`
from current positions, such as `facs_1` and `facs_3_zone_2`. The same service will back future TEI/MEI export logic.
