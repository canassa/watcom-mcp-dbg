"""
Source code loading and resolution functionality.

Extracted from ui/source_display.py for use in MCP server.
"""

from pathlib import Path
from typing import Optional


class SourceResolver:
    """Handles loading and resolving source files."""

    def __init__(self):
        self.source_cache = {}  # {file_path: list of lines}
        self.source_directories = []  # Additional directories to search for sources

    def add_source_directory(self, directory: str):
        """Add a directory to search for source files.

        Args:
            directory: Directory path
        """
        path = Path(directory)
        if path.exists() and path.is_dir():
            self.source_directories.append(path)

    def load_source_file(self, file_path: str) -> Optional[list[str]]:
        """Load a source file.

        Args:
            file_path: Path to source file

        Returns:
            List of lines if successful, None otherwise
        """
        if file_path in self.source_cache:
            return self.source_cache[file_path]

        # Try to find the file
        paths_to_try = [Path(file_path)]

        # Try source directories with the basename
        basename = Path(file_path).name
        for src_dir in self.source_directories:
            paths_to_try.append(src_dir / basename)

        for path in paths_to_try:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                        self.source_cache[file_path] = lines
                        return lines
                except Exception:
                    pass

        return None

    def get_source_lines(self, file_path: str, line: int, context_lines: int = 5) -> Optional[dict]:
        """Get source lines with context around a specific line.

        Args:
            file_path: Source file path
            line: Line number to center on
            context_lines: Number of context lines before/after

        Returns:
            Dictionary with 'lines' (list of dicts with 'line_number', 'content', 'is_current')
            and 'file' (basename), or None if file not found
        """
        lines = self.load_source_file(file_path)
        if not lines:
            return None

        # Calculate line range
        start_line = max(1, line - context_lines)
        end_line = min(len(lines), line + context_lines)

        # Build line list
        result_lines = []
        for line_num in range(start_line, end_line + 1):
            line_idx = line_num - 1
            if line_idx < len(lines):
                result_lines.append({
                    'line_number': line_num,
                    'content': lines[line_idx].rstrip(),
                    'is_current': line_num == line
                })

        return {
            'file': Path(file_path).name,
            'full_path': file_path,
            'lines': result_lines
        }

    def get_source_range(self, file_path: str, start_line: int, end_line: int) -> Optional[dict]:
        """Get a range of source lines.

        Args:
            file_path: Source file path
            start_line: First line to display
            end_line: Last line to display

        Returns:
            Dictionary with 'lines' (list of dicts with 'line_number', 'content')
            and 'file' (basename), or None if file not found
        """
        lines = self.load_source_file(file_path)
        if not lines:
            return None

        # Clamp to valid range
        start_line = max(1, start_line)
        end_line = min(len(lines), end_line)

        # Build line list
        result_lines = []
        for line_num in range(start_line, end_line + 1):
            line_idx = line_num - 1
            if line_idx < len(lines):
                result_lines.append({
                    'line_number': line_num,
                    'content': lines[line_idx].rstrip()
                })

        return {
            'file': Path(file_path).name,
            'full_path': file_path,
            'lines': result_lines
        }
