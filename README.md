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

## How to Use

1. After starting the application, go to `File > Add Page Images...` to add pages to the document. Note that when
   adding multiple pages at once, the ordering is according to the selection in the file select dialog. If the order
   is wrong, add the images one by one.
2. Navigate the page canvas:
   - When holding `Ctrl`, the mouse wheel results in zooming in or out the page, and you can drag the image around
     while left-clicking to change the panning.
   - Create a new zone by drawing a rectangle using right-click to define one corner and drop the click at the other
     corner. The new zone is registered in the zone viewer on the right. The zone can also be dragged around by
     left-clicking it, changing its position.
   - Zones can be removed by selecting a zone (using left click or in the zone viewer on the right) and either pressing
     the `DEL` key or clicking the button `Delete Zone` on the right.
3. Navigate through the pages using the toolbar buttons `Previous Page` and `Next Page`. Individual pages can be
   removed and added using the `Add Pages` and `Remove Page` buttons.
4. Change your document type in the `Type:` selector to either `TEI` or `MEI`. This will affect the format the
   XML is exported as.
5. When wanting to pause and resume later, go to `File > Save` and close the application. Using `File > Open...`,
   the work can be continued at the same position where stopped last.
6. When all zones are added correctly on each page, click `Export TEI/MEI` to export the document in the correct
   format. This generates a valid minimal TEI or MEI XML document endowed with all facsimile/surface/zone data and
   milestone markers (such as `<pb/>`, `<lb/>` or `<sb/>`).

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

- Repositories (`app/repositories/`) encapsulate persistance mechanisms, most notably writing/reading to/from the file
  system or to Qt settings objects.
  - `app/repositories/document_repository.py`: Reading/saving documents from/to file system.
  - `app/repositories/settings_repository.py`: Reading/saving settings from/to Qt settings.
  - `app/repositories/text_repository.py`: Saving text data to file system.
- Models (`app/models/`) are frozen dataclasses for persisted content only. For example, for document content, the file
  `app/models/document.py` contains the dataclasses `Document`, `Surface`, and `Zone`. Models are not meant to hold
  live application states (see viewmodels), data manipulation methods (see services), or widgets (see views).
  Models exclusively contain the data that is serialized/deserialized by the repositories.
  - `app/models/document.py`: The state of a persisted document file. Contains surfaces, zones, etc.
  - `app/models/settings.py`: The state of persisted settings. Contains image settings, display options, etc.
- Viewmodels (`app/viewmodels/`) hold the whole observable application state, including transient UI state such as
  `selected_zone_index`, `dirty`, and `file_path`. Viewmodels never store model instances as fields; they contain other
  viewmodels (`DocumentViewModel` -> `SurfaceViewModel` -> `ZoneViewModel`) instead. They are usually manipulated by
  service methods (see services), or especially in the case of data bindings, are directly modified by widget
  interactions. Viewmodels should fire signals on changes, so that the widgets (see views) can adapt accordingly.
  - `app/viewmodels/document_viewmodel.py`: Holds the live application state regarding document contents.
  - `app/viewmodels/settings_viewmodel.py`: Hold the live application state regarding settings.
  - `app/viewmodels/surface_viewmodel.py`: Holds the live application state regarding surface contents.
  - `app/viewmodels/zone_viewmodel.py`: Holds the live application state regarding zone contents.
- Services (`app/services/`) 
  - `app/services/document_service.py`: Document manipulation, such as adding/removal of surfaces/zones, etc. 
  - `app/services/image_service.py`: Image manipulation, such as applying brightness/saturation/contrast.
  - `app/services/mapping_service.py`: Model/viewmodel conversion, only called by services. Mapping functions touch only
    persistable fields. Transient viewmodel fields, such as `selected_zone_index`, are not persisted and are not
    modified by mapping.
  - `app/services/settings_service.py`: Settings manipulation, e.g., loading default settings, creating temporary
    settings viewmodel objects, loading from temporary settings viewmodels, etc.
  - `app/services/xml_export_service.py`: For exporting TEI/MEI XML data.
  - `app/services/xml_id_service.py`: Generates surface and zone xml:ids.
- Views (`app/ui/`) are the layer that is closest to the user of the software. They consist of windows, dialogs and
  widgets that are used to display the application state (see viewmodels) to the user or allow its modification by the
  user. Complex validation checks or application state modifications are meant to be contained in the services, but 
  simple changes and data bindings may directly access the viewmodel layer.
  - `app/ui/dialog_change_settings.py`: The dialog for editing application settings.
  - `app/ui/facsimile_canvas.py`: The canvas widget for displaying and interacting with the image, drawing zones, etc.
  - `app/ui/main_window.py`: The application's main window.
  - `app/ui/widgets.py`: Contains custom widgets, such as a widget for picking and displaying colors.

### Signal Scope

Signals fire at the narrowest scope that changed:

- Updating one zone rectangle emits only that `ZoneViewModel.rect_changed`.
- Adding, removing, or reordering zones emits only the owning `SurfaceViewModel.zones_changed`.
- Adding, removing, reordering pages, or opening a new document emits `DocumentViewModel.surfaces_changed`.

This keeps the UI from rebuilding unrelated page and zone objects when only one nested item changed.

### Persistence

Repositories are stateless. `DocumentRepository` loads and saves explicit paths only, and it does not drive UI state.
Saves are atomic: data is packed with `msgpack`, written to a sibling `.tmp` file, then replaced into place.

### XML IDs

`xml:id` values are never stored in the model, viewmodel, or `.fca` file. They are derived on demand by `XmlIdService`
from current positions, such as `facs_1` and `facs_3_zone_2`. The same service will back future TEI/MEI export logic.
