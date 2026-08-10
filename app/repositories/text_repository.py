from __future__ import annotations

from pathlib import Path


class TextRepository:
    """
    Repository for saving text data to the file system.

    Methods:
        save (Path, str): Saves the text data into a text file on the file system.
    """

    @classmethod
    def save(cls, path: Path, text: str) -> None:
        """
        Saves the text data into a text file on the file system.

        :param path: Path to save to.
        :param text: Text to save.
        """
        tmp_path = path.with_name(f"{path.name}.tmp")
        tmp_path.write_text(text)
        tmp_path.replace(path)
