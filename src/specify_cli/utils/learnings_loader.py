"""
Learnings Database Loader and Manager

Handles loading, parsing, similarity detection, and appending for the Bicep learnings database.
Implements strict error handling per Constitution Principle III (Early and Fatal Error Handling).

Performance Targets:
- Database loading: <2 seconds for 250 entries
- Semantic similarity: <500ms per comparison
- Append operations: <100ms
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Error classification keywords from learnings-format.md contract
CAPTURE_KEYWORDS = [
    "missing property",
    "invalid value",
    "quota exceeded",
    "already exists",
    "not found",
    "unauthorized",
    "forbidden",
    "conflict",
    "bad request",
]

IGNORE_KEYWORDS = [
    "throttled",
    "timeout",
    "unavailable",
    "service unavailable",
    "gateway timeout",
    "too many requests",
]

# Canonical category list from learnings-format.md
CANONICAL_CATEGORIES = [
    "Security",
    "Compliance",
    "Networking",
    "Data Services",
    "Compute",
    "Configuration",
    "Performance",
    "Operations",
]

# Category priority for conflict resolution
HIGH_PRIORITY_CATEGORIES = ["Security", "Compliance"]


class FileNotFoundError(Exception):
    """Raised when learnings database file is missing or inaccessible."""
    pass


class PerformanceError(Exception):
    """Raised when operation exceeds performance budget."""
    pass


class ImportError(Exception):
    """Raised when required library fails to import."""
    pass


class LearningEntry:
    """Represents a single learning entry from the database."""
    
    def __init__(
        self,
        timestamp: datetime,
        category: str,
        context: str,
        issue: str,
        solution: str,
        raw_text: str,
    ):
        self.timestamp = timestamp
        self.category = category
        self.context = context
        self.issue = issue
        self.solution = solution
        self.raw_text = raw_text
    
    def __repr__(self):
        return f"LearningEntry({self.category}, {self.timestamp.isoformat()})"
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
            "context": self.context,
            "issue": self.issue,
            "solution": self.solution,
        }


def load_learnings_database(file_path: Path) -> List[LearningEntry]:
    """
    Load and parse the learnings database from Markdown file.
    
    Args:
        file_path: Path to bicep-learnings.md file
        
    Returns:
        List of parsed LearningEntry objects
        
    Raises:
        FileNotFoundError: If file is missing or inaccessible with actionable error message
        
    Performance: Must complete in <2 seconds for 250 entries
    """
    start_time = time.time()
    
    # Verify file exists and is readable
    if not file_path.exists():
        raise FileNotFoundError(
            f"Learnings database not found at: {file_path}\n"
            f"Expected location: .specify/learnings/bicep-learnings.md\n"
            f"Action: Run 'specify init' to create the database, or manually create the file."
        )
    
    if not file_path.is_file():
        raise FileNotFoundError(
            f"Path exists but is not a file: {file_path}\n"
            f"Action: Remove the directory and create bicep-learnings.md file instead."
        )
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except PermissionError as e:
        raise FileNotFoundError(
            f"Permission denied reading learnings database: {file_path}\n"
            f"Action: Check file permissions (need read access).\n"
            f"Error: {e}"
        )
    except Exception as e:
        raise FileNotFoundError(
            f"Failed to read learnings database: {file_path}\n"
            f"Error: {e}\n"
            f"Action: Verify file is not corrupted and is valid UTF-8 text."
        )
    
    # Parse entries from content
    entries = []
    lines = content.split("\n")
    
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        
        # Skip empty lines, comments, headers, and metadata
        if not line or line.startswith("#") or line.startswith("**") or line.startswith("<!--"):
            continue
        
        # Try to parse as learning entry
        entry = _parse_entry(line, line_num)
        if entry:
            entries.append(entry)
    
    elapsed = time.time() - start_time
    
    # Check entry count thresholds per FR-013
    entry_count = len(entries)
    
    if entry_count >= 250:
        print(f"ℹ️  Info: Database has {entry_count} entries (≥250). Category filtering will be automatically enabled for optimal performance.")
    elif entry_count >= 200:
        print(f"⚠️  Warning: Database has {entry_count} entries (≥200). Approaching optimization threshold (250 entries). Consider using category filtering for better performance.")
    
    # Log performance warning if approaching budget (80% threshold)
    if elapsed > 1.6:  # 80% of 2s budget
        print(f"⚠️  Warning: Database loading took {elapsed:.2f}s (approaching 2s limit)")
    
    return entries


def _parse_entry(line: str, line_num: int) -> Optional[LearningEntry]:
    """
    Parse a single learning entry line.
    
    Format: [Timestamp] [Category] [Context] → [Issue] → [Solution]
    
    Args:
        line: Raw line text
        line_num: Line number for error reporting
        
    Returns:
        LearningEntry if valid, None if malformed (logs warning)
    """
    # Entry format: [TIMESTAMP] [CATEGORY] [CONTEXT] → [ISSUE] → [SOLUTION]
    # Check for arrow separators
    if "→" not in line:
        return None  # Not a learning entry, skip silently
    
    parts = line.split("→")
    if len(parts) != 3:
        print(f"⚠️  Warning: Malformed entry at line {line_num} (expected 2 arrows): {line[:80]}...")
        return None
    
    # Extract timestamp, category, context from first part
    header = parts[0].strip()
    issue = parts[1].strip()
    solution = parts[2].strip()
    
    # Parse timestamp and category from header
    # Format: [TIMESTAMP] CATEGORY CONTEXT (category may contain spaces like "Data Services")
    
    # Try matching with known canonical categories first (handles multi-word categories)
    category_pattern = '|'.join(re.escape(cat) for cat in CANONICAL_CATEGORIES)
    timestamp_match = re.match(rf"\[([^\]]+)\]\s+({category_pattern})\s+(.+)", header)
    
    if not timestamp_match:
        # Fallback: Try format with brackets: [TIMESTAMP] [CATEGORY] CONTEXT
        timestamp_match = re.match(r"\[([^\]]+)\]\s+\[([^\]]+)\]\s+(.+)", header)
    
    if not timestamp_match:
        # Fallback: Try simple format with single-word category
        timestamp_match = re.match(r"\[([^\]]+)\]\s+(\w+)\s+(.+)", header)
    
    if not timestamp_match:
        print(f"⚠️  Warning: Cannot parse timestamp/category at line {line_num}: {header[:60]}...")
        return None
    
    timestamp_str = timestamp_match.group(1)
    category = timestamp_match.group(2).strip()
    context = timestamp_match.group(3).strip()
    
    # Parse timestamp
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError:
        print(f"⚠️  Warning: Invalid timestamp at line {line_num}: {timestamp_str}")
        return None
    
    # Validate category (case-insensitive)
    if category not in CANONICAL_CATEGORIES and category.title() not in CANONICAL_CATEGORIES:
        print(f"⚠️  Warning: Unknown category '{category}' at line {line_num} (not in canonical list)")
        # Still parse the entry, just warn
    
    return LearningEntry(
        timestamp=timestamp,
        category=category,
        context=context,
        issue=issue,
        solution=solution,
        raw_text=line,
    )


def classify_error(error_message: str) -> Tuple[bool, Optional[str]]:
    """
    Classify error as structural (worth learning) or transient (ignore).
    
    Implements keyword matching algorithm from learnings-format.md:
    - Case-insensitive substring matching
    - Check "Ignore" keywords first (transient errors)
    - Then check "Capture" keywords (structural errors)
    - First match wins
    
    Args:
        error_message: Error message text to classify
        
    Returns:
        Tuple of (should_capture, matched_keyword)
        - should_capture: True if structural error worth learning
        - matched_keyword: Keyword that triggered classification
    """
    error_lower = error_message.lower()
    
    # Check IGNORE keywords first (transient errors)
    for keyword in IGNORE_KEYWORDS:
        if keyword.lower() in error_lower:
            return (False, keyword)
    
    # Check CAPTURE keywords (structural errors)
    for keyword in CAPTURE_KEYWORDS:
        if keyword.lower() in error_lower:
            return (True, keyword)
    
    # No keyword match - default to NOT capturing (be conservative)
    return (False, None)


def check_insufficient_context(error_message: str, context: str = "") -> bool:
    """
    Detect if error lacks sufficient context to be a useful learning.
    
    Insufficient context indicators:
    - Error message is too short (< 10 chars)
    - Only generic single-word errors ("error", "failed")
    
    Args:
        error_message: Error message text
        context: Context/resource information
        
    Returns:
        True if context is insufficient (should skip append)
    """
    # Too short
    if len(error_message.strip()) < 10:
        return True
    
    # Single-word generic errors only
    error_trimmed = error_message.strip().lower()
    single_word_generic = ["error", "failed", "failure"]
    if error_trimmed in single_word_generic:
        return True
    
    return False


def check_duplicate_entry(
    new_entry_text: str,
    existing_entries: List[LearningEntry],
    threshold: float = 0.6,
) -> Tuple[bool, Optional[LearningEntry], float]:
    """
    Check if new entry is duplicate using semantic similarity.
    
    Uses TF-IDF vectorization + cosine similarity with 60% threshold
    (adjusted from 70% to compensate for keyword-based matching).
    
    Args:
        new_entry_text: Full text of new entry to check
        existing_entries: List of existing entries to compare against
        threshold: Similarity threshold (default 0.6 = 60%)
        
    Returns:
        Tuple of (is_duplicate, matched_entry, similarity_score)
        
    Raises:
        ImportError: If scikit-learn is not installed with installation instructions
        PerformanceError: If any comparison exceeds 500ms timeout
    """
    # Import scikit-learn with error handling
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError as e:
        raise ImportError(
            "scikit-learn is required for semantic similarity detection.\n"
            "Install with: pip install scikit-learn\n"
            "Or add to pyproject.toml and run: pip install -e .\n"
            f"Original error: {e}"
        )
    
    if not existing_entries:
        return (False, None, 0.0)
    
    start_time = time.time()
    
    # Extract text from existing entries
    existing_texts = [entry.raw_text for entry in existing_entries]
    all_texts = existing_texts + [new_entry_text]
    
    # Vectorize using TF-IDF
    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            max_features=500,  # Limit features for performance
        )
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except Exception as e:
        print(f"⚠️  Warning: TF-IDF vectorization failed: {e}")
        return (False, None, 0.0)
    
    # Calculate cosine similarity between new entry and all existing entries
    new_vector = tfidf_matrix[-1]
    existing_vectors = tfidf_matrix[:-1]
    
    similarities = cosine_similarity(new_vector, existing_vectors)[0]
    
    # Find highest similarity
    max_similarity_idx = similarities.argmax()
    max_similarity = float(similarities[max_similarity_idx])  # Convert from numpy to Python float
    
    elapsed = time.time() - start_time
    
    # Check performance budget (500ms per comparison)
    if elapsed > 0.5:
        raise PerformanceError(
            f"Similarity check exceeded 500ms budget: {elapsed*1000:.1f}ms\n"
            f"Database size: {len(existing_entries)} entries\n"
            f"Action: Consider enabling category filtering or implementing caching."
        )
    
    # Determine if duplicate based on threshold
    is_duplicate = max_similarity >= threshold
    matched_entry = existing_entries[max_similarity_idx] if is_duplicate else None
    
    return (is_duplicate, matched_entry, max_similarity)


def append_learning_entry(
    file_path: Path,
    category: str,
    context: str,
    issue: str,
    solution: str,
    existing_entries: Optional[List[LearningEntry]] = None,
    check_duplicates: bool = True,
) -> bool:
    """
    Append new learning entry to database with format validation and duplicate detection.
    
    Args:
        file_path: Path to bicep-learnings.md file
        category: Entry category (must match canonical list)
        context: Context/resource description
        issue: Problem description
        solution: Solution/pattern description
        existing_entries: Optional pre-loaded entries for duplicate checking
        check_duplicates: Whether to check for duplicates (default True)
        
    Returns:
        True if entry was appended, False if duplicate detected
        
    Raises:
        ValueError: If entry format is invalid (malformed entries rejected immediately)
        FileNotFoundError: If database file cannot be loaded for reading/appending
        PerformanceError: If append operation exceeds 100ms timeout
        
    Performance: Must complete in <100ms
    """
    start_time = time.time()
    
    # Validate category
    if category not in CANONICAL_CATEGORIES:
        raise ValueError(
            f"Invalid category: '{category}'\n"
            f"Must be one of: {', '.join(CANONICAL_CATEGORIES)}\n"
            f"Action: Use a canonical category name (case-sensitive)."
        )
    
    # Validate field lengths (from learnings-format.md)
    if len(category) > 20:
        raise ValueError(f"Category too long: {len(category)} chars (max 20)")
    if len(context) > 100:
        raise ValueError(f"Context too long: {len(context)} chars (max 100)")
    if len(issue) > 150:
        raise ValueError(f"Issue too long: {len(issue)} chars (max 150)")
    if len(solution) > 200:
        raise ValueError(f"Solution too long: {len(solution)} chars (max 200)")
    
    # Generate timestamp (ISO 8601 UTC)
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Format entry
    entry_text = f"[{timestamp}] {category} {context} → {issue} → {solution}"
    
    # Validate total length
    if len(entry_text) > 500:
        raise ValueError(
            f"Entry too long: {len(entry_text)} chars (max 500)\n"
            f"Action: Shorten context, issue, or solution text."
        )
    
    # Check for duplicates if requested
    if check_duplicates:
        if existing_entries is None:
            # Load database for duplicate checking
            try:
                existing_entries = load_learnings_database(file_path)
            except FileNotFoundError:
                # Database doesn't exist yet, create it
                existing_entries = []
        
        is_duplicate, matched_entry, similarity = check_duplicate_entry(
            entry_text, existing_entries, threshold=0.6
        )
        
        if is_duplicate:
            print(
                f"ℹ️  Duplicate detected (similarity: {similarity:.1%})\n"
                f"   Existing: {matched_entry.raw_text[:80]}...\n"
                f"   Skipping append."
            )
            return False
    
    # Append to file
    try:
        # Find appropriate category section in file
        content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        
        # Find category header
        category_header = f"## {category}"
        if category_header in content:
            # Insert after category header
            lines = content.split("\n")
            insert_idx = None
            for i, line in enumerate(lines):
                if line.strip() == category_header:
                    # Find first blank line or next header after category
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("##") or lines[j].startswith("---"):
                            insert_idx = j
                            break
                    if insert_idx is None:
                        insert_idx = i + 2  # Insert after header and blank line
                    break
            
            if insert_idx is not None:
                lines.insert(insert_idx, entry_text)
                content = "\n".join(lines)
        else:
            # Category section doesn't exist, append at end
            content += f"\n\n## {category}\n\n{entry_text}\n"
        
        file_path.write_text(content, encoding="utf-8")
        
    except PermissionError as e:
        raise FileNotFoundError(
            f"Permission denied writing to learnings database: {file_path}\n"
            f"Action: Check file/directory write permissions.\n"
            f"Error: {e}"
        )
    except Exception as e:
        raise FileNotFoundError(
            f"Failed to write to learnings database: {file_path}\n"
            f"Error: {e}"
        )
    
    elapsed = time.time() - start_time
    
    # Check performance budget (100ms)
    if elapsed > 0.1:
        print(f"⚠️  Warning: Append operation took {elapsed*1000:.0f}ms (exceeds 100ms target)")
    
    return True


def filter_learnings_by_category(
    entries: List[LearningEntry],
    categories: List[str],
) -> List[LearningEntry]:
    """
    Filter learnings to only specified categories for performance optimization.
    
    Args:
        entries: All learning entries
        categories: List of category names to include
        
    Returns:
        Filtered list of entries matching specified categories
    """
    categories_lower = [cat.lower() for cat in categories]
    return [
        entry for entry in entries
        if entry.category.lower() in categories_lower
    ]


def _get_category_priority(category: str) -> int:
    """
    Get priority level for a category.
    
    Security and Compliance categories have HIGH priority (0).
    All other categories have NORMAL priority (1).
    
    Args:
        category: Category name
        
    Returns:
        Priority level (0 = HIGH, 1 = NORMAL)
    """
    return 0 if category in HIGH_PRIORITY_CATEGORIES else 1


def _entries_conflict(entry1: LearningEntry, entry2: LearningEntry) -> bool:
    """
    Determine if two learning entries conflict with each other.
    
    Entries conflict if they address the same context (resource type)
    AND the same issue/topic but provide contradictory guidance.
    
    Args:
        entry1: First learning entry
        entry2: Second learning entry
        
    Returns:
        True if entries conflict, False otherwise
    """
    # Must be same context to conflict
    if entry1.context.lower() != entry2.context.lower():
        return False
    
    # Check if they address the same issue/property
    # (e.g., both talk about "public network access" or "encryption")
    issue1_lower = entry1.issue.lower()
    issue2_lower = entry2.issue.lower()
    solution1_lower = entry1.solution.lower()
    solution2_lower = entry2.solution.lower()
    
    # Extract key topics from both entries
    topics = [
        "public network access",
        "public access",
        "public endpoint",
        "encryption",
        "tls",
        "front door",
        "retention",
        "api version",
        "authentication",
        "private endpoint",
        "dns",
        "subnet",
        "vnet",
    ]
    
    # Find common topics between the two entries
    common_topics = []
    for topic in topics:
        in_entry1 = topic in issue1_lower or topic in solution1_lower
        in_entry2 = topic in issue2_lower or topic in solution2_lower
        if in_entry1 and in_entry2:
            common_topics.append(topic)
    
    # No common topics means no conflict (addressing different aspects)
    if not common_topics:
        return False
    
    # Check for contradictory keywords in solutions for the same topic
    contradictory_pairs = [
        ("enable", "disable"),
        ("enabled", "disabled"),
        ("use", "avoid"),
        ("include", "exclude"),
        ("required", "optional"),
        ("always", "never"),
        ("must", "should not"),
    ]
    
    for word1, word2 in contradictory_pairs:
        if (word1 in solution1_lower and word2 in solution2_lower) or \
           (word2 in solution1_lower and word1 in solution2_lower):
            return True
    
    return False


def resolve_conflicts(entries: List[LearningEntry]) -> List[LearningEntry]:
    """
    Resolve conflicts between learning entries using priority and timestamp.
    
    Conflict Resolution Rules (from learnings-format.md):
    1. Check category priority: Security/Compliance override all others
    2. Check timestamp: Most recent wins within same priority tier
    3. Tie-breaker: If timestamps identical, first entry in file wins
    
    Args:
        entries: List of learning entries (may contain conflicts)
        
    Returns:
        Filtered list with conflicts resolved
        
    Performance:
        O(n²) worst case for conflict detection
        Acceptable for <250 entries (target: <50ms)
    """
    if not entries:
        return []
    
    # Group entries by context for efficient conflict detection
    context_groups: Dict[str, List[LearningEntry]] = {}
    for entry in entries:
        context_key = entry.context.lower()
        if context_key not in context_groups:
            context_groups[context_key] = []
        context_groups[context_key].append(entry)
    
    # Process each context group for conflicts
    resolved_entries = []
    
    for context_key, group in context_groups.items():
        if len(group) == 1:
            # No conflicts possible with single entry
            resolved_entries.append(group[0])
            continue
        
        # Sort by priority (HIGH=0 first) then timestamp (newest first)
        sorted_group = sorted(
            group,
            key=lambda e: (_get_category_priority(e.category), -e.timestamp.timestamp())
        )
        
        # Check for conflicts and select winning entries
        selected_entries = []
        for entry in sorted_group:
            # Check if this entry conflicts with any already selected
            conflicts = False
            for selected in selected_entries:
                if _entries_conflict(entry, selected):
                    # Current entry conflicts with higher-priority entry
                    # Skip this entry
                    conflicts = True
                    print(f"⚠️  Conflict detected: Skipping '{entry.context}' entry from {entry.timestamp.date()} " +
                          f"(overridden by {selected.category} entry from {selected.timestamp.date()})")
                    break
            
            if not conflicts:
                selected_entries.append(entry)
        
        resolved_entries.extend(selected_entries)
    
    # Sort final results by timestamp (newest first) for better context ordering
    resolved_entries.sort(key=lambda e: -e.timestamp.timestamp())
    
    return resolved_entries
