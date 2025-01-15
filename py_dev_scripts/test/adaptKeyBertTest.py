import yake
import re
from typing import List, Set, Dict, Optional
from collections import Counter
import logging
from dataclasses import dataclass
import string
import sys
print(sys.executable)


@dataclass
class DomainStats:
    """Track domain-specific statistics for term importance."""
    frequency: Counter  # Term frequency in corpus
    position: Counter  # Term positions in titles
    collocations: Counter  # Words that appear together
    importance: Dict[str, float]  # Learned term importance

class AdaptKeywordExtractor:
    """Adaptive keyword extractor with domain learning capabilities."""
    
    def __init__(self):
        # Core extractor with optimized parameters
        self.kw_extractor = yake.KeywordExtractor(
            lan="en",
            n=3,  # Up to trigrams
            dedupLim=0.1,  # Strict deduplication
            windowsSize=1,
            top=20
        )
        
        # Domain knowledge initialization
        self.domain_stats = DomainStats(
            frequency=Counter(),
            position=Counter(),
            collocations=Counter(),
            importance={}
        )
        
        # Regex patterns
        self.patterns = {
            'compound': re.compile(r'\w+(?:[-]\w+)+|\w+(?:\s\w+){1,2}'),
            'quotes': re.compile(r"'([^']*)'|\"([^\"]*)\""),
            'numbers': re.compile(r'\b\d+\b')
        }
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def adapt_to_domain(self, titles: List[str], min_frequency: int = 2):
        """
        Learn domain-specific patterns from a corpus of titles.
        
        Args:
            titles: List of news titles to learn from
            min_frequency: Minimum frequency for term consideration
        """
        self.logger.info(f"Adapting to domain using {len(titles)} titles")
        
        # Reset stats for new adaptation
        self.domain_stats = DomainStats(
            frequency=Counter(),
            position=Counter(),
            collocations=Counter(),
            importance={}
        )
        
        # Process each title
        for title in titles:
            if not title:
                continue
                
            # Clean and tokenize
            clean_title = self._clean_text(title)
            words = clean_title.split()
            
            # Update term frequencies
            self.domain_stats.frequency.update(words)
            
            # Track term positions (start/middle/end)
            for i, word in enumerate(words):
                position_weight = 1.0
                if i == 0:  # Start of title
                    position_weight = 1.5
                elif i == len(words) - 1:  # End of title
                    position_weight = 1.2
                self.domain_stats.position[word] += position_weight
            
            # Track collocations (words that appear together)
            for i in range(len(words) - 1):
                collocation = f"{words[i]} {words[i+1]}"
                self.domain_stats.collocations[collocation] += 1
        
        # Calculate term importance
        total_titles = len(titles)
        for term, freq in self.domain_stats.frequency.items():
            if freq >= min_frequency:
                position_score = self.domain_stats.position[term] / freq
                frequency_score = freq / total_titles
                importance = (position_score + frequency_score) / 2
                self.domain_stats.importance[term] = importance
        
        self.logger.info(f"Learned {len(self.domain_stats.importance)} domain terms")

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text while preserving important patterns."""
        # Standardize quotes and hyphens
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        text = re.sub(r'[‐‑‒–—―]', '-', text)
        
        # Remove punctuation except in patterns we want to keep
        punctuation_to_remove = string.punctuation.replace('-', '').replace("'", '')
        translation_table = str.maketrans('', '', punctuation_to_remove)
        text = text.translate(translation_table)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.lower()

    def _extract_special_patterns(self, title: str) -> Set[str]:
        """Extract special patterns like quotes and compound terms."""
        patterns = set()
        
        # Extract quoted phrases
        for match in self.patterns['quotes'].finditer(title):
            quote = match.group(1) or match.group(2)
            if quote and len(quote.split()) <= 3:
                patterns.add(quote.strip())
        
        # Extract compound terms
        compounds = self.patterns['compound'].findall(title)
        patterns.update(compound.strip() for compound in compounds)
        
        return patterns

    def _score_keyword(self, keyword: str, position: int, title_length: int) -> float:
        """Score a keyword based on learned domain knowledge and position."""
        base_score = 1.0
        keyword_lower = keyword.lower()
        
        # Domain importance boost
        if keyword_lower in self.domain_stats.importance:
            base_score *= (1 + self.domain_stats.importance[keyword_lower])
        
        # Position boost
        position_score = 1.0 - (position / title_length)
        base_score *= (1 + position_score)
        
        # Length penalty for very short terms
        if len(keyword_lower) < 3:
            base_score *= 0.5
        
        return base_score

    def extract_keywords(self, title: str, max_keywords: int = 5) -> List[str]:
        """
        Extract keywords from a news title using adapted domain knowledge.
        
        Args:
            title: News title to extract keywords from
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of extracted keywords
        """
        if not title:
            return []
        
        keywords = []
        seen = set()
        
        # 1. Extract special patterns first
        special_patterns = self._extract_special_patterns(title)
        for pattern in special_patterns:
            if pattern.lower() not in seen:
                keywords.append((pattern, 1.5))  # High base score for special patterns
                seen.add(pattern.lower())
        
        # 2. Extract keywords using YAKE
        yake_keywords = self.kw_extractor.extract_keywords(title)
        for kw, score in yake_keywords:
            if kw.lower() not in seen:
                # Convert YAKE score (lower is better) to our scale
                converted_score = 1 / (1 + score)
                keywords.append((kw, converted_score))
                seen.add(kw.lower())
        
        # 3. Score and sort all keywords
        scored_keywords = []
        words = title.split()
        for kw, base_score in keywords:
            positions = [i for i, w in enumerate(words) if kw.lower() in w.lower()]
            if positions:
                final_score = base_score * self._score_keyword(kw, positions[0], len(words))
                scored_keywords.append((kw, final_score))
        
        # Sort by score and remove duplicates/substrings
        scored_keywords.sort(key=lambda x: x[1], reverse=True)
        final_keywords = []
        seen = set()
        
        for kw, _ in scored_keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen and not any(kw_lower in existing for existing in seen):
                final_keywords.append(kw)
                seen.add(kw_lower)
                if len(final_keywords) == max_keywords:
                    break
        
        return final_keywords

def test_extractor():
    """Test the adaptive keyword extractor."""
    # Create sample training corpus
    training_corpus = [
        "Covid-19 cases surge in major cities",
        "New vaccine shows promising results against virus",
        "Global climate conference reaches historic agreement",
        "Tech company announces breakthrough in AI research",
        "Sports team wins championship after dramatic final",
        "Economic recovery continues despite challenges",
        "Scientists discover new species in Amazon rainforest",
    ]
    
    # Initialize and adapt extractor
    extractor = AdaptKeywordExtractor()
    extractor.adapt_to_domain(training_corpus)
    
    # Test cases
    test_cases = [
        "Feeling 'so destroyed' by Covid-19",
        "The Sikh volunteers feeding thousands in lockdown",
        "Girl dies with Covid on day she was due vaccine",
        "'I'm double-vaccinated but can't show the proof'",
        "Study reveals long-term Covid-19 effects on brain",
        "New variant emerges as cases rise globally"
    ]
    
    print("\nTesting adaptive keyword extraction:")
    print("=" * 50)
    
    for title in test_cases:
        keywords = extractor.extract_keywords(title)
        print(f"\nTitle: {title}")
        print(f"Keywords: {keywords}")

if __name__ == "__main__":
    test_extractor()