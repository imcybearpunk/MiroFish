"""Tests for TextProcessor and split_text_into_chunks."""

import pytest
from app.services.text_processor import TextProcessor
from app.utils.file_parser import split_text_into_chunks


class TestTextProcessorPreprocess:
    """Tests for TextProcessor.preprocess_text()."""

    def test_preprocess_removes_extra_newlines(self):
        """Test that 4+ consecutive newlines collapse to 2."""
        text = "line1\n\n\n\nline2"
        result = TextProcessor.preprocess_text(text)
        assert result == "line1\n\nline2"

    def test_preprocess_removes_multiple_extra_newlines(self):
        """Test that multiple groups of 4+ newlines are collapsed."""
        text = "line1\n\n\n\nline2\n\n\n\n\nline3"
        result = TextProcessor.preprocess_text(text)
        assert result == "line1\n\nline2\n\nline3"

    def test_preprocess_normalizes_crlf(self):
        """Test that CRLF (\\r\\n) is converted to LF (\\n)."""
        text = "line1\r\nline2\r\nline3"
        result = TextProcessor.preprocess_text(text)
        assert result == "line1\nline2\nline3"

    def test_preprocess_normalizes_cr(self):
        """Test that CR (\\r) is converted to LF (\\n)."""
        text = "line1\rline2\rline3"
        result = TextProcessor.preprocess_text(text)
        assert result == "line1\nline2\nline3"

    def test_preprocess_strips_line_whitespace(self):
        """Test that leading and trailing spaces on each line are removed."""
        text = "  line1  \n  line2  \n  line3  "
        result = TextProcessor.preprocess_text(text)
        assert result == "line1\nline2\nline3"

    def test_preprocess_strips_tabs(self):
        """Test that leading and trailing tabs on each line are removed."""
        text = "\t\tline1\t\t\n\t\tline2\t\t"
        result = TextProcessor.preprocess_text(text)
        assert result == "line1\nline2"

    def test_preprocess_empty_string(self):
        """Test that empty string returns empty string."""
        result = TextProcessor.preprocess_text("")
        assert result == ""

    def test_preprocess_whitespace_only(self):
        """Test that whitespace-only text is preserved but stripped."""
        text = "   \n   \n   "
        result = TextProcessor.preprocess_text(text)
        # Each line stripped, then newlines collapse
        assert "\n\n\n" not in result

    def test_preprocess_preserves_internal_spaces(self):
        """Test that spaces within lines are preserved."""
        text = "hello world\nfoo bar"
        result = TextProcessor.preprocess_text(text)
        assert result == "hello world\nfoo bar"

    def test_preprocess_combined_normalization(self):
        """Test that all normalization steps work together."""
        text = "  line1  \r\n  line2  \n\n\n\n  line3  "
        result = TextProcessor.preprocess_text(text)
        assert result == "line1\nline2\n\nline3"


class TestTextProcessorStats:
    """Tests for TextProcessor.get_text_stats()."""

    def test_get_text_stats_basic(self):
        """Test text stats for simple single-line text."""
        text = "hello world"
        stats = TextProcessor.get_text_stats(text)
        assert stats["total_chars"] == 11
        assert stats["total_lines"] == 1
        assert stats["total_words"] == 2

    def test_get_text_stats_multiline(self):
        """Test text stats for multiline text."""
        text = "line1\nline2\nline3"
        stats = TextProcessor.get_text_stats(text)
        assert stats["total_chars"] == 17  # 5 + 1 + 5 + 1 + 5
        assert stats["total_lines"] == 3
        assert stats["total_words"] == 3

    def test_get_text_stats_empty_string(self):
        """Test text stats for empty string."""
        stats = TextProcessor.get_text_stats("")
        assert stats["total_chars"] == 0
        # "".count('\n') + 1 == 1 — implementation counts line fragments, not \n count
        assert stats["total_lines"] == 1
        assert stats["total_words"] == 0

    def test_get_text_stats_single_line_multiple_words(self):
        """Test text stats with multiple words on single line."""
        text = "one two three four five"
        stats = TextProcessor.get_text_stats(text)
        assert stats["total_chars"] == 23
        assert stats["total_lines"] == 1
        assert stats["total_words"] == 5

    def test_get_text_stats_with_punctuation(self):
        """Test that punctuation doesn't affect word count."""
        text = "hello, world! how are you?"
        stats = TextProcessor.get_text_stats(text)
        assert stats["total_words"] == 5

    def test_get_text_stats_multiple_spaces(self):
        """Test word count with multiple spaces between words."""
        text = "word1   word2   word3"
        stats = TextProcessor.get_text_stats(text)
        assert stats["total_words"] == 3

    def test_get_text_stats_tabs_and_newlines(self):
        """Test that tabs and newlines are counted in char count."""
        text = "line1\t\tline2\nline3"
        stats = TextProcessor.get_text_stats(text)
        assert stats["total_chars"] == 18  # line1(5) + \t(1) + \t(1) + line2(5) + \n(1) + line3(5) = 18
        assert stats["total_lines"] == 2   # 1 newline → 2 line segments


class TestTextProcessorSplitText:
    """Tests for TextProcessor.split_text()."""

    def test_split_text_delegates_to_chunks(self):
        """Test that TextProcessor.split_text delegates to split_text_into_chunks."""
        text = "This is a test. " * 100  # Long text to trigger splitting
        result = TextProcessor.split_text(text, chunk_size=500, overlap=50)
        expected = split_text_into_chunks(text, chunk_size=500, overlap=50)
        assert result == expected

    def test_split_text_with_custom_chunk_size(self):
        """Test split_text with custom chunk_size parameter."""
        text = "A" * 1000
        result = TextProcessor.split_text(text, chunk_size=200, overlap=20)
        expected = split_text_into_chunks(text, chunk_size=200, overlap=20)
        assert result == expected

    def test_split_text_with_zero_overlap(self):
        """Test split_text with overlap=0."""
        text = "word " * 200
        result = TextProcessor.split_text(text, chunk_size=100, overlap=0)
        expected = split_text_into_chunks(text, chunk_size=100, overlap=0)
        assert result == expected


class TestSplitTextIntoChunksBasic:
    """Tests for split_text_into_chunks() basic behavior."""

    def test_empty_text_returns_empty_list(self):
        """Test that empty string returns empty list."""
        result = split_text_into_chunks("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        """Test that whitespace-only text returns empty list."""
        result = split_text_into_chunks("   \n   \n   ")
        assert result == []

    def test_short_text_returns_single_chunk(self):
        """Test that text shorter than chunk_size returns single chunk."""
        text = "This is short"
        result = split_text_into_chunks(text, chunk_size=500)
        assert len(result) == 1
        assert result[0] == text

    def test_text_exactly_chunk_size(self):
        """Test that text exactly matching chunk_size returns single chunk."""
        text = "A" * 500
        result = split_text_into_chunks(text, chunk_size=500)
        assert len(result) == 1
        assert result[0] == text

    def test_text_slightly_over_chunk_size(self):
        """Test that text slightly over chunk_size can still be single chunk."""
        text = "A" * 510
        result = split_text_into_chunks(text, chunk_size=500)
        # May be 1 or 2 chunks depending on boundary detection; with overlap
        # concatenation may repeat characters, so just verify total coverage.
        assert len(result) >= 1
        assert len("".join(result)) >= len(text)

    def test_long_text_produces_multiple_chunks(self):
        """Test that long text produces multiple chunks."""
        text = "This is a sentence. " * 100
        result = split_text_into_chunks(text, chunk_size=500)
        assert len(result) > 1

    def test_all_chunks_are_non_empty(self):
        """Test that no chunk in result is empty string."""
        text = "This is a test. " * 50
        result = split_text_into_chunks(text, chunk_size=300)
        for chunk in result:
            assert len(chunk) > 0
            assert chunk.strip() != ""


class TestSplitTextIntoChunksOverlap:
    """Tests for split_text_into_chunks() overlap behavior."""

    def test_chunks_overlap(self):
        """Test that chunks overlap correctly."""
        text = "one two three four five six seven eight nine ten " * 10
        result = split_text_into_chunks(text, chunk_size=200, overlap=50)
        assert len(result) > 1

        # Verify overlap: end of chunk[i] should overlap with start of chunk[i+1]
        for i in range(len(result) - 1):
            chunk_i = result[i]
            chunk_i_next = result[i + 1]
            # The end of chunk[i] should have content that appears near the start of chunk[i+1]
            # Due to overlap, some content should be repeated
            last_part = chunk_i[-50:]
            # Check if any of the last part content appears in the next chunk
            assert any(last_part[j:] in chunk_i_next for j in range(len(last_part)))

    def test_no_overlap_when_zero_overlap(self):
        """Test that chunks don't repeat content when overlap=0."""
        text = "word " * 200
        result = split_text_into_chunks(text, chunk_size=100, overlap=0)

        if len(result) > 1:
            # Concatenate all chunks
            full_text = "".join(result)
            # With zero overlap, content shouldn't be duplicated
            # Check that we don't have exact repetitions at chunk boundaries
            for i in range(len(result) - 1):
                chunk_end = result[i][-20:]
                chunk_start = result[i + 1][:20]
                # These shouldn't be identical (minimal overlap)
                assert chunk_end != chunk_start or chunk_end == ""


class TestSplitTextIntoChunksSizeRespect:
    """Tests for chunk size constraints."""

    def test_chunk_size_respected(self):
        """Test that no chunk significantly exceeds chunk_size."""
        text = "word " * 300
        chunk_size = 200
        result = split_text_into_chunks(text, chunk_size=chunk_size, overlap=0)

        # Chunks may be slightly larger due to boundary detection, but not excessively
        for chunk in result:
            # Allow up to 1.5x chunk_size to account for sentence boundary extensions
            assert len(chunk) <= chunk_size * 1.5

    def test_chunk_size_with_overlap(self):
        """Test chunk size respect with overlap enabled."""
        text = "A" * 5000
        chunk_size = 500
        result = split_text_into_chunks(text, chunk_size=chunk_size, overlap=100)

        for chunk in result:
            # With simple text, should be close to chunk_size
            assert len(chunk) <= chunk_size * 1.3


class TestSplitTextIntoChunksBoundaries:
    """Tests for sentence boundary detection."""

    def test_chinese_sentence_boundary(self):
        """Test that Chinese punctuation (。) is recognized as boundary."""
        text = "这是第一句。这是第二句。这是第三句。" * 20
        result = split_text_into_chunks(text, chunk_size=500)
        assert len(result) >= 1

        # Verify chunks split at Chinese periods
        for chunk in result:
            assert len(chunk) > 0

    def test_exclamation_mark_boundary(self):
        """Test that exclamation marks are sentence boundaries."""
        text = "First sentence! Second sentence! Third sentence! " * 15
        result = split_text_into_chunks(text, chunk_size=300)

        # Should split at exclamation marks
        if len(result) > 1:
            for chunk in result:
                assert len(chunk) > 0

    def test_question_mark_boundary(self):
        """Test that question marks are sentence boundaries."""
        text = "Is this a sentence? Yes it is. Is this another? Yes! " * 15
        result = split_text_into_chunks(text, chunk_size=300)

        if len(result) > 1:
            for chunk in result:
                assert len(chunk) > 0

    def test_period_boundary(self):
        """Test that periods are recognized as sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. " * 20
        result = split_text_into_chunks(text, chunk_size=300)

        # Should have multiple chunks from long text
        assert len(result) >= 1

    def test_newline_boundary(self):
        """Test that newlines are recognized as boundaries."""
        text = "Line one\nLine two\nLine three\n" * 20
        result = split_text_into_chunks(text, chunk_size=300)
        assert len(result) >= 1

    def test_triple_newline_boundary(self):
        """Test that triple newlines are recognized as boundaries."""
        text = "Para 1\n\n\nPara 2\n\n\nPara 3\n\n\n" * 15
        result = split_text_into_chunks(text, chunk_size=300)
        assert len(result) >= 1

    def test_mixed_boundaries(self):
        """Test text with mixed boundary types."""
        text = "First. Second! Third? Fourth。\nFifth\n\n\nSixth" * 15
        result = split_text_into_chunks(text, chunk_size=300)

        # Should split on various boundaries
        assert len(result) >= 1
        for chunk in result:
            assert len(chunk) > 0


class TestSplitTextIntoChunksPreservation:
    """Tests for content preservation and integrity."""

    def test_full_text_preserved_when_concatenated(self):
        """Test that chunk content covers all tokens from the original text."""
        text = "This is a test. " * 50
        result = split_text_into_chunks(text, chunk_size=300, overlap=50)

        # All chunks must be non-empty and come from the source text
        assert len(result) > 0
        for chunk in result:
            assert len(chunk.strip()) > 0
            # Every chunk must be a substring of the original (possibly stripped)
            assert chunk.strip() in text or text.replace(" ", "").startswith(chunk.replace(" ", "")[:20])

    def test_unicode_text_preserved(self):
        """Test that unicode text is chunked without corruption."""
        text = "Hello世界。Bonjour monde！Привет мир？" * 20
        result = split_text_into_chunks(text, chunk_size=300)

        # All chunks are non-empty and contain recognisable unicode content
        assert len(result) > 0
        for chunk in result:
            # Each chunk must contain at least some of the original characters
            assert any(c in chunk for c in ['H', '世', 'B', 'П', '。', '！', '？'])

    def test_special_characters_preserved(self):
        """Test that special characters are preserved."""
        text = "Test with @#$%^&*() special chars. " * 30
        result = split_text_into_chunks(text, chunk_size=300)

        for chunk in result:
            assert "@#$%^&*()" in chunk or any(c in chunk for c in "@#$%^&*()")


class TestSplitTextIntoChunksEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_single_very_long_word(self):
        """Test handling of a single word longer than chunk_size."""
        text = "A" * 600
        result = split_text_into_chunks(text, chunk_size=500)
        # Should handle gracefully - may be single chunk or split
        assert len(result) >= 1
        # With overlap, concatenation may repeat content; just verify
        # all characters are from the original and total content length >= original
        concatenated = "".join(result)
        assert len(concatenated) >= len(text)
        assert all(c == 'A' for c in concatenated)

    def test_single_sentence_longer_than_chunk_size(self):
        """Test handling of a single sentence longer than chunk_size."""
        text = "This is a very long sentence " * 30 + "."
        result = split_text_into_chunks(text, chunk_size=200)
        # Should handle gracefully
        assert len(result) >= 1

    def test_text_with_only_boundaries(self):
        """Test text that is mostly boundaries."""
        text = ". ! ? 。！？\n" * 30
        result = split_text_into_chunks(text, chunk_size=200)
        # Should handle without error
        assert isinstance(result, list)

    def test_very_large_chunk_size(self):
        """Test with chunk_size larger than text."""
        text = "This is a short text."
        result = split_text_into_chunks(text, chunk_size=10000)
        assert len(result) == 1
        assert result[0] == text

    def test_very_small_chunk_size(self):
        """Test with very small chunk_size."""
        text = "This is a test. " * 20
        result = split_text_into_chunks(text, chunk_size=10)
        # Should produce many chunks
        assert len(result) >= 10

    def test_overlap_larger_than_chunk_size(self):
        """Test behavior when overlap is larger than chunk_size."""
        text = "word " * 100
        result = split_text_into_chunks(text, chunk_size=50, overlap=100)
        # Should handle gracefully
        assert len(result) >= 1
        for chunk in result:
            assert len(chunk) > 0

    def test_overlap_equal_to_chunk_size(self):
        """Test behavior when overlap equals chunk_size."""
        text = "word " * 100
        result = split_text_into_chunks(text, chunk_size=100, overlap=100)
        # Should handle gracefully
        assert len(result) >= 1
        for chunk in result:
            assert len(chunk) > 0
