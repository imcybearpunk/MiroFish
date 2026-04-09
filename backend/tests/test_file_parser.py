"""
Tests for FileParser utility module.

Comprehensive test suite covering:
- Text extraction from supported file formats (.txt, .md, .markdown, .pdf)
- Error handling for missing files and unsupported extensions
- Multiple file extraction with proper formatting
- Character encoding fallback mechanisms
- Chinese and special character handling
"""

import pytest
import sys
import importlib.util
from pathlib import Path

# Import FileParser and _read_text_with_fallback directly
# This avoids importing through app.__init__ which has heavy dependencies
spec = importlib.util.spec_from_file_location(
    "file_parser",
    str(Path(__file__).parent.parent / "app" / "utils" / "file_parser.py")
)
file_parser_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(file_parser_module)

FileParser = file_parser_module.FileParser
_read_text_with_fallback = file_parser_module._read_text_with_fallback


class TestExtractText:
    """Test the extract_text method."""

    def test_extract_txt_utf8(self, tmp_path):
        """Extract UTF-8 encoded .txt file successfully."""
        # Create a UTF-8 .txt file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, this is a test file.\nWith multiple lines."
        test_file.write_text(test_content, encoding='utf-8')

        # Extract and verify
        result = FileParser.extract_text(str(test_file))
        assert result == test_content

    def test_extract_md_file(self, tmp_path):
        """Extract content from .md Markdown file."""
        # Create a .md file
        test_file = tmp_path / "readme.md"
        test_content = "# Title\n\nSome markdown content.\n\n- List item 1\n- List item 2"
        test_file.write_text(test_content, encoding='utf-8')

        # Extract and verify
        result = FileParser.extract_text(str(test_file))
        assert result == test_content

    def test_extract_markdown_extension(self, tmp_path):
        """Extract content from .markdown extension (alternate Markdown extension)."""
        # Create a .markdown file
        test_file = tmp_path / "document.markdown"
        test_content = "## Heading\n\nSome **bold** text here."
        test_file.write_text(test_content, encoding='utf-8')

        # Extract and verify
        result = FileParser.extract_text(str(test_file))
        assert result == test_content

    def test_extract_nonexistent_raises_file_not_found(self, tmp_path):
        """FileNotFoundError is raised when file does not exist."""
        nonexistent_file = str(tmp_path / "does_not_exist.txt")

        # Verify FileNotFoundError is raised
        with pytest.raises(FileNotFoundError):
            FileParser.extract_text(nonexistent_file)

    def test_extract_unsupported_extension_raises_value_error(self, tmp_path):
        """ValueError is raised for unsupported file extensions."""
        # Test various unsupported extensions
        unsupported_files = [
            tmp_path / "file.docx",
            tmp_path / "data.csv",
            tmp_path / "image.jpg",
            tmp_path / "script.py"
        ]

        for unsupported_file in unsupported_files:
            # Create dummy files
            unsupported_file.write_text("dummy")

            # Verify ValueError is raised
            with pytest.raises(ValueError, match="不支持的文件格式"):
                FileParser.extract_text(str(unsupported_file))

    def test_extract_txt_chinese_content(self, tmp_path):
        """Extract UTF-8 encoded Chinese text correctly."""
        # Create a .txt file with Chinese content
        test_file = tmp_path / "chinese.txt"
        test_content = "你好，这是一个测试文件。\n包含中文内容。\n支持多行文本。"
        test_file.write_text(test_content, encoding='utf-8')

        # Extract and verify
        result = FileParser.extract_text(str(test_file))
        assert result == test_content
        assert "你好" in result
        assert "测试文件" in result

    def test_extract_md_chinese_content(self, tmp_path):
        """Extract Chinese content from Markdown files correctly."""
        # Create a .md file with Chinese content
        test_file = tmp_path / "readme_cn.md"
        test_content = "# 标题\n\n这是一个Markdown文档。\n\n## 副标题\n\n包含中文内容。"
        test_file.write_text(test_content, encoding='utf-8')

        # Extract and verify
        result = FileParser.extract_text(str(test_file))
        assert result == test_content
        assert "标题" in result


class TestExtractFromMultiple:
    """Test the extract_from_multiple method."""

    def test_extract_from_multiple_combines_texts(self, tmp_path):
        """Extract from multiple files combines content with proper headers."""
        # Create two test files
        file1 = tmp_path / "file1.txt"
        file1.write_text("Content from file 1", encoding='utf-8')

        file2 = tmp_path / "file2.md"
        file2.write_text("Content from file 2", encoding='utf-8')

        # Extract from multiple
        result = FileParser.extract_from_multiple([str(file1), str(file2)])

        # Verify both files are included with headers
        assert "=== 文档 1: file1.txt ===" in result
        assert "Content from file 1" in result
        assert "=== 文档 2: file2.md ===" in result
        assert "Content from file 2" in result

    def test_extract_from_multiple_handles_error_gracefully(self, tmp_path):
        """Extract from multiple handles missing file gracefully."""
        # Create one valid file
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("Valid content", encoding='utf-8')

        # Reference a nonexistent file
        nonexistent_file = str(tmp_path / "missing.txt")

        # Extract from multiple (with one missing)
        result = FileParser.extract_from_multiple([str(valid_file), nonexistent_file])

        # Verify valid file is included
        assert "=== 文档 1: valid.txt ===" in result
        assert "Valid content" in result

        # Verify error message for missing file
        assert "=== 文档 2:" in result
        assert "提取失败" in result
        assert "missing.txt" in result

    def test_extract_from_multiple_empty_list(self):
        """Empty file list returns empty string."""
        result = FileParser.extract_from_multiple([])
        assert result == ""

    def test_extract_from_multiple_single_file(self, tmp_path):
        """Extract from single file in list works correctly."""
        test_file = tmp_path / "single.txt"
        test_file.write_text("Single file content", encoding='utf-8')

        result = FileParser.extract_from_multiple([str(test_file)])

        assert "=== 文档 1: single.txt ===" in result
        assert "Single file content" in result

    def test_extract_from_multiple_three_files_with_mixed_errors(self, tmp_path):
        """Extract from three files with one error in the middle."""
        file1 = tmp_path / "file1.txt"
        file1.write_text("File 1 content", encoding='utf-8')

        nonexistent = str(tmp_path / "missing.txt")

        file3 = tmp_path / "file3.md"
        file3.write_text("File 3 content", encoding='utf-8')

        result = FileParser.extract_from_multiple([str(file1), nonexistent, str(file3)])

        # Verify all three are referenced
        assert "=== 文档 1:" in result
        assert "=== 文档 2:" in result
        assert "=== 文档 3:" in result

        # Verify content and error
        assert "File 1 content" in result
        assert "File 3 content" in result
        assert "提取失败" in result


class TestReadTextWithFallback:
    """Test the _read_text_with_fallback function."""

    def test_read_text_fallback_utf8_success(self, tmp_path):
        """Successfully read UTF-8 encoded file."""
        test_file = tmp_path / "utf8_file.txt"
        content = "UTF-8 content: Hello world"
        test_file.write_text(content, encoding='utf-8')

        result = _read_text_with_fallback(str(test_file))
        assert result == content

    def test_read_text_fallback_latin1(self, tmp_path):
        """Read Latin-1 encoded file with fallback mechanism."""
        test_file = tmp_path / "latin1_file.txt"
        # Write content with Latin-1 encoding
        content = "Café résumé naïve"
        test_file.write_bytes(content.encode('latin-1'))

        # Should read without crashing (may have replacement chars)
        result = _read_text_with_fallback(str(test_file))
        # The fallback should handle it without raising an exception
        assert isinstance(result, str)
        assert len(result) > 0

    def test_read_text_fallback_mixed_encoding(self, tmp_path):
        """Read file with mixed or unknown encoding without crashing."""
        test_file = tmp_path / "mixed_file.txt"
        # Create a file with unusual bytes that aren't pure UTF-8
        mixed_bytes = b"Hello \xc3\xa9 world"  # "Hello é world" in UTF-8
        test_file.write_bytes(mixed_bytes)

        result = _read_text_with_fallback(str(test_file))
        assert isinstance(result, str)
        assert "Hello" in result

    def test_read_text_fallback_empty_file(self, tmp_path):
        """Read empty file returns empty string."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding='utf-8')

        result = _read_text_with_fallback(str(test_file))
        assert result == ""

    def test_read_text_fallback_multiline_content(self, tmp_path):
        """Read multiline UTF-8 file correctly."""
        test_file = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3\nLine 4"
        test_file.write_text(content, encoding='utf-8')

        result = _read_text_with_fallback(str(test_file))
        assert result == content
        assert result.count('\n') == 3


class TestSupportedExtensions:
    """Test supported file extensions."""

    def test_supported_extensions_defined(self):
        """Check that SUPPORTED_EXTENSIONS is properly defined."""
        expected = {'.pdf', '.md', '.markdown', '.txt'}
        assert FileParser.SUPPORTED_EXTENSIONS == expected

    def test_supported_extensions_are_lowercase(self):
        """Verify all supported extensions are lowercase."""
        for ext in FileParser.SUPPORTED_EXTENSIONS:
            assert ext == ext.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_extract_file_with_special_characters_in_name(self, tmp_path):
        """Extract file with special characters in filename."""
        test_file = tmp_path / "file_with-special.chars_123.txt"
        content = "Content with special filename"
        test_file.write_text(content, encoding='utf-8')

        result = FileParser.extract_text(str(test_file))
        assert result == content

    def test_extract_file_with_unicode_in_name(self, tmp_path):
        """Extract file with Unicode characters in filename."""
        test_file = tmp_path / "文件_test.txt"
        content = "Content with Unicode filename"
        test_file.write_text(content, encoding='utf-8')

        result = FileParser.extract_text(str(test_file))
        assert result == content

    def test_extract_large_text_file(self, tmp_path):
        """Extract large text file (10,000+ characters)."""
        test_file = tmp_path / "large.txt"
        # Create a large file with 20,000 characters
        large_content = "Line content. " * 1500
        test_file.write_text(large_content, encoding='utf-8')

        result = FileParser.extract_text(str(test_file))
        assert len(result) > 10000
        assert result == large_content

    def test_extract_file_with_newlines_and_whitespace(self, tmp_path):
        """Extract file with various whitespace patterns."""
        test_file = tmp_path / "whitespace.txt"
        content = "Line 1\n\nLine 3 with empty above\n  \nLine with indent\n\n\n"
        test_file.write_text(content, encoding='utf-8')

        result = FileParser.extract_text(str(test_file))
        assert result == content

    def test_extract_case_insensitive_extension(self, tmp_path):
        """File extensions are case insensitive (.TXT, .Txt, .txt all work)."""
        # Test with uppercase extension
        test_file_upper = tmp_path / "file.TXT"
        test_file_upper.write_text("Content", encoding='utf-8')
        result_upper = FileParser.extract_text(str(test_file_upper))
        assert result_upper == "Content"

        # Test with mixed case extension
        test_file_mixed = tmp_path / "file.Md"
        test_file_mixed.write_text("# Markdown", encoding='utf-8')
        result_mixed = FileParser.extract_text(str(test_file_mixed))
        assert result_mixed == "# Markdown"

    def test_extract_from_multiple_all_errors(self, tmp_path):
        """Extract from multiple files where all fail."""
        nonexistent1 = str(tmp_path / "missing1.txt")
        nonexistent2 = str(tmp_path / "missing2.txt")

        result = FileParser.extract_from_multiple([nonexistent1, nonexistent2])

        # Should still produce output with error messages
        assert "=== 文档 1:" in result
        assert "=== 文档 2:" in result
        assert "提取失败" in result

    def test_extract_md_and_markdown_extensions_equivalent(self, tmp_path):
        """Both .md and .markdown extensions are treated equivalently."""
        content = "# Same Content"

        md_file = tmp_path / "file.md"
        md_file.write_text(content, encoding='utf-8')

        markdown_file = tmp_path / "file.markdown"
        markdown_file.write_text(content, encoding='utf-8')

        result_md = FileParser.extract_text(str(md_file))
        result_markdown = FileParser.extract_text(str(markdown_file))

        assert result_md == result_markdown == content
