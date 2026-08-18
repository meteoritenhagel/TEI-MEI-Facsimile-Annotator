"""
Constants module. Contains constants that are accessible for the whole application.

Constants:
    ORGANIZATION_NAME: Name of the organization responsible for creating the app.
    APPLICATION_NAME: Name of the current application.
    DOMAIN_NAME: Domain name associated with the application.

    DOCUMENT_FILE_EXTENSION: File extension associated with saving/loading the document to/from the file system.

    IMAGE_DIRECTORY: Default image directory for image paths in exported TEI/MEI.

    DEBOUNCE_INTERVAL_MS: Debounce timer interval for image settings.
"""
ORGANIZATION_NAME: str = "Tristan Repolusk"
APPLICATION_NAME: str = "TEI/MEI Facsimile Annotator"
DOMAIN_NAME: str = "https://github.com/meteoritenhagel/TEI-MEI-Facsimile-Annotator"

DOCUMENT_FILE_EXTENSION: str = "fca"

IMAGE_DIRECTORY: str = "../images/"

DEBOUNCE_INTERVAL_MS: int = 100