#!/usr/bin/env python3
"""
Phase 0 Research: Semantic Similarity Library Evaluation
Tests three approaches with real Bicep error scenarios.
"""

import time
from typing import List, Tuple

# Test dataset: pairs of (entry1, entry2, expected_similarity_high)
# True = should be detected as duplicate (>70% similar)
# False = should NOT be duplicate (<70% similar)
TEST_DATASET = [
    # High similarity pairs (should detect as duplicates)
    (
        "Azure Front Door creation fails when backend pool is empty",
        "Front Door deployment error: backend pool configuration missing",
        True
    ),
    (
        "Key Vault deployment fails with VaultAlreadyExists error",
        "Cannot create Key Vault because vault name already exists",
        True
    ),
    (
        "Cosmos DB container requires throughput property with minimum 400 RU/s",
        "CosmosDB deployment fails: missing options.throughput property, needs at least 400 RU",
        True
    ),
    (
        "Storage account public network access enabled by default",
        "Storage deployment: publicNetworkAccess not disabled, security risk",
        True
    ),
    (
        "Azure SQL Database missing minimalTlsVersion property",
        "SQL Server deployment needs TLS version configuration",
        True
    ),
    
    # Low similarity pairs (should NOT be duplicates)
    (
        "Azure Front Door creation fails when backend pool is empty",
        "Storage account requires encryption with customer-managed keys",
        False
    ),
    (
        "Key Vault deployment fails with VaultAlreadyExists error",
        "Cosmos DB throughput configuration is missing",
        False
    ),
    (
        "Network Security Perimeter not supported in this region",
        "Private Endpoint DNS zone configuration required",
        False
    ),
    (
        "App Service VNet integration requires Premium SKU",
        "Function App needs system-assigned managed identity",
        False
    ),
    
    # Edge cases (moderate similarity - test boundary)
    (
        "Azure Key Vault public access not disabled",
        "Storage Account public network access enabled",
        False  # Different resources, but similar security issue
    ),
    (
        "Missing required property: throughput",
        "Required property throughput is not defined",
        True  # Same issue, different wording
    ),
]

def evaluate_option_1_transformers():
    """Evaluate sentence-transformers approach."""
    print("\n" + "="*60)
    print("OPTION 1: sentence-transformers")
    print("="*60)
    
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        # Measure initialization time
        start = time.time()
        model = SentenceTransformer('all-MiniLM-L6-v2')
        init_time = time.time() - start
        print(f"✓ Initialization time: {init_time:.3f}s")
        
        # Measure comparison time for 250 entries
        test_corpus = [pair[0] for pair in TEST_DATASET] * 25  # Simulate 250 entries
        start = time.time()
        embeddings = model.encode(test_corpus)
        encoding_time = time.time() - start
        print(f"✓ Encoding 250 entries: {encoding_time:.3f}s")
        
        # Test accuracy on dataset
        correct = 0
        total = len(TEST_DATASET)
        comparison_times = []
        
        for entry1, entry2, expected_duplicate in TEST_DATASET:
            start = time.time()
            emb1 = model.encode([entry1])[0]
            emb2 = model.encode([entry2])[0]
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            comparison_time = time.time() - start
            comparison_times.append(comparison_time)
            
            # Convert cosine similarity (0-1) to percentage
            similarity_pct = similarity * 100
            is_duplicate = similarity_pct >= 70
            
            if is_duplicate == expected_duplicate:
                correct += 1
            else:
                print(f"✗ Mismatch: {similarity_pct:.1f}% - '{entry1[:50]}...' vs '{entry2[:50]}...'")
        
        avg_comparison = sum(comparison_times) / len(comparison_times) * 1000
        max_comparison = max(comparison_times) * 1000
        
        accuracy = (correct / total) * 100
        print(f"\n✓ Accuracy: {correct}/{total} ({accuracy:.1f}%)")
        print(f"✓ Avg comparison time: {avg_comparison:.1f}ms")
        print(f"✓ Max comparison time: {max_comparison:.1f}ms")
        print(f"✓ Performance target (<500ms): {'PASS' if max_comparison < 500 else 'FAIL'}")
        
        return {
            'init_time': init_time,
            'encoding_time': encoding_time,
            'avg_comparison': avg_comparison,
            'max_comparison': max_comparison,
            'accuracy': accuracy,
            'available': True
        }
        
    except ImportError:
        print("✗ sentence-transformers not installed")
        print("  Install: pip install sentence-transformers")
        return {'available': False}
    except Exception as e:
        print(f"✗ Error: {e}")
        return {'available': False}


def evaluate_option_2_spacy():
    """Evaluate spaCy approach."""
    print("\n" + "="*60)
    print("OPTION 2: spaCy")
    print("="*60)
    
    try:
        import spacy
        
        # Measure initialization time
        start = time.time()
        try:
            nlp = spacy.load("en_core_web_md")
        except OSError:
            print("✗ Model 'en_core_web_md' not found")
            print("  Install: python -m spacy download en_core_web_md")
            return {'available': False}
        
        init_time = time.time() - start
        print(f"✓ Initialization time: {init_time:.3f}s")
        
        # Measure processing time for 250 entries
        test_corpus = [pair[0] for pair in TEST_DATASET] * 25
        start = time.time()
        docs = list(nlp.pipe(test_corpus))
        processing_time = time.time() - start
        print(f"✓ Processing 250 entries: {processing_time:.3f}s")
        
        # Test accuracy on dataset
        correct = 0
        total = len(TEST_DATASET)
        comparison_times = []
        
        for entry1, entry2, expected_duplicate in TEST_DATASET:
            start = time.time()
            doc1 = nlp(entry1)
            doc2 = nlp(entry2)
            similarity = doc1.similarity(doc2)
            comparison_time = time.time() - start
            comparison_times.append(comparison_time)
            
            # spaCy returns similarity 0-1
            similarity_pct = similarity * 100
            is_duplicate = similarity_pct >= 70
            
            if is_duplicate == expected_duplicate:
                correct += 1
            else:
                print(f"✗ Mismatch: {similarity_pct:.1f}% - '{entry1[:50]}...' vs '{entry2[:50]}...'")
        
        avg_comparison = sum(comparison_times) / len(comparison_times) * 1000
        max_comparison = max(comparison_times) * 1000
        
        accuracy = (correct / total) * 100
        print(f"\n✓ Accuracy: {correct}/{total} ({accuracy:.1f}%)")
        print(f"✓ Avg comparison time: {avg_comparison:.1f}ms")
        print(f"✓ Max comparison time: {max_comparison:.1f}ms")
        print(f"✓ Performance target (<500ms): {'PASS' if max_comparison < 500 else 'FAIL'}")
        
        return {
            'init_time': init_time,
            'processing_time': processing_time,
            'avg_comparison': avg_comparison,
            'max_comparison': max_comparison,
            'accuracy': accuracy,
            'available': True
        }
        
    except ImportError:
        print("✗ spaCy not installed")
        print("  Install: pip install spacy")
        return {'available': False}
    except Exception as e:
        print(f"✗ Error: {e}")
        return {'available': False}


def evaluate_option_3_tfidf():
    """Evaluate TF-IDF + Cosine Similarity approach."""
    print("\n" + "="*60)
    print("OPTION 3: TF-IDF + Cosine Similarity (scikit-learn)")
    print("="*60)
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        # Measure initialization time
        start = time.time()
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        init_time = time.time() - start
        print(f"✓ Initialization time: {init_time:.3f}s")
        
        # Measure vectorization time for 250 entries
        test_corpus = [pair[0] for pair in TEST_DATASET] * 25
        start = time.time()
        vectorizer.fit(test_corpus)
        vectors = vectorizer.transform(test_corpus)
        vectorization_time = time.time() - start
        print(f"✓ Vectorizing 250 entries: {vectorization_time:.3f}s")
        
        # Test accuracy on dataset
        # Re-fit on just the test dataset for comparison
        all_texts = []
        for entry1, entry2, _ in TEST_DATASET:
            all_texts.extend([entry1, entry2])
        vectorizer.fit(all_texts)
        
        correct = 0
        total = len(TEST_DATASET)
        comparison_times = []
        
        for entry1, entry2, expected_duplicate in TEST_DATASET:
            start = time.time()
            vec1 = vectorizer.transform([entry1])
            vec2 = vectorizer.transform([entry2])
            similarity = cosine_similarity(vec1, vec2)[0][0]
            comparison_time = time.time() - start
            comparison_times.append(comparison_time)
            
            # Cosine similarity returns 0-1
            similarity_pct = similarity * 100
            is_duplicate = similarity_pct >= 70
            
            if is_duplicate == expected_duplicate:
                correct += 1
            else:
                print(f"✗ Mismatch: {similarity_pct:.1f}% - '{entry1[:50]}...' vs '{entry2[:50]}...'")
        
        avg_comparison = sum(comparison_times) / len(comparison_times) * 1000
        max_comparison = max(comparison_times) * 1000
        
        accuracy = (correct / total) * 100
        print(f"\n✓ Accuracy: {correct}/{total} ({accuracy:.1f}%)")
        print(f"✓ Avg comparison time: {avg_comparison:.1f}ms")
        print(f"✓ Max comparison time: {max_comparison:.1f}ms")
        print(f"✓ Performance target (<500ms): {'PASS' if max_comparison < 500 else 'FAIL'}")
        
        return {
            'init_time': init_time,
            'vectorization_time': vectorization_time,
            'avg_comparison': avg_comparison,
            'max_comparison': max_comparison,
            'accuracy': accuracy,
            'available': True
        }
        
    except ImportError:
        print("✗ scikit-learn not installed")
        print("  Install: pip install scikit-learn")
        return {'available': False}
    except Exception as e:
        print(f"✗ Error: {e}")
        return {'available': False}


def main():
    """Run all evaluations and produce recommendation."""
    print("="*60)
    print("PHASE 0 RESEARCH: Semantic Similarity Library Evaluation")
    print("="*60)
    print(f"\nTest Dataset: {len(TEST_DATASET)} pairs")
    print(f"Requirements:")
    print(f"  - Accuracy: Detect duplicates at 70% threshold")
    print(f"  - Performance: <500ms per comparison")
    print(f"  - Scale: 250 entries in database")
    print(f"  - Platform: Cross-platform (Windows/Linux/macOS)")
    print(f"  - Dependencies: Minimal, Python 3.11+")
    
    # Run evaluations
    results = {
        'transformers': evaluate_option_1_transformers(),
        'spacy': evaluate_option_2_spacy(),
        'tfidf': evaluate_option_3_tfidf(),
    }
    
    # Summary comparison
    print("\n" + "="*60)
    print("SUMMARY COMPARISON")
    print("="*60)
    
    print(f"\n{'Metric':<25} {'Transformers':<15} {'spaCy':<15} {'TF-IDF':<15}")
    print("-" * 70)
    
    def get_val(results, lib, key, fmt="{:.1f}"):
        if results[lib].get('available'):
            return fmt.format(results[lib].get(key, 0))
        return "N/A"
    
    print(f"{'Init Time (s)':<25} {get_val(results, 'transformers', 'init_time', '{:.3f}'):<15} {get_val(results, 'spacy', 'init_time', '{:.3f}'):<15} {get_val(results, 'tfidf', 'init_time', '{:.3f}'):<15}")
    print(f"{'Avg Comparison (ms)':<25} {get_val(results, 'transformers', 'avg_comparison'):<15} {get_val(results, 'spacy', 'avg_comparison'):<15} {get_val(results, 'tfidf', 'avg_comparison'):<15}")
    print(f"{'Max Comparison (ms)':<25} {get_val(results, 'transformers', 'max_comparison'):<15} {get_val(results, 'spacy', 'max_comparison'):<15} {get_val(results, 'tfidf', 'max_comparison'):<15}")
    print(f"{'Accuracy (%)':<25} {get_val(results, 'transformers', 'accuracy'):<15} {get_val(results, 'spacy', 'accuracy'):<15} {get_val(results, 'tfidf', 'accuracy'):<15}")
    
    print("\n" + "="*60)
    print("RECOMMENDATION")
    print("="*60)
    
    # Determine best option based on available results
    available = [k for k, v in results.items() if v.get('available')]
    
    if not available:
        print("\n✗ No libraries available for evaluation")
        print("  Install at least one option to complete research")
        return
    
    # Score each option (higher is better)
    scores = {}
    for lib in available:
        r = results[lib]
        # Scoring: accuracy (40%), performance (40%), init time (20%)
        acc_score = r['accuracy'] * 0.4
        perf_score = (500 - min(r['max_comparison'], 500)) / 5 * 0.4  # Max 40 points
        init_score = (5 - min(r['init_time'], 5)) * 4 * 0.2  # Max 20 points
        scores[lib] = acc_score + perf_score + init_score
    
    winner = max(scores, key=scores.get)
    
    print(f"\n✓ RECOMMENDED: {winner.upper()}")
    print(f"  Score: {scores[winner]:.1f}/100")
    print(f"\nReason: Best balance of accuracy ({results[winner]['accuracy']:.1f}%), ")
    print(f"        performance ({results[winner]['max_comparison']:.1f}ms max), ")
    print(f"        and initialization ({results[winner]['init_time']:.3f}s)")
    
    if winner == 'tfidf':
        print(f"\nAdditional Benefits:")
        print(f"  - Minimal dependencies (scikit-learn only)")
        print(f"  - Fast initialization and comparison")
        print(f"  - Easy to debug and maintain")
        print(f"  - Small footprint (~20MB)")
        
    elif winner == 'spacy':
        print(f"\nAdditional Benefits:")
        print(f"  - Good semantic understanding")
        print(f"  - Production-ready library")
        print(f"  - Moderate model size (~50MB)")
        
    elif winner == 'transformers':
        print(f"\nAdditional Benefits:")
        print(f"  - Highest semantic accuracy")
        print(f"  - State-of-the-art NLP models")
        print(f"  - Well-maintained by HuggingFace")
        print(f"\nTradeoffs:")
        print(f"  - Large dependencies (~420MB)")
        print(f"  - Slower initialization")


if __name__ == "__main__":
    main()
