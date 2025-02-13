import nltk
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords

class KeywordExtractor:
    """
    Uses a SentenceTransformer model to extract keywords from text.
    """
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords')
            self.stop_words = set(stopwords.words('english'))
            
    def extract_keywords(self, text, max_keywords=5):
        """
        Extracts up to max_keywords from the input text.
        :param text: Input text.
        :param max_keywords: Maximum number of keywords to extract.
        :return: List of keywords.
        """
        if not text:
            return []
        # Split text into individual words.
        chunks = text.split()
        if not chunks:
            return []
        # Get embeddings for the full text and individual words.
        text_embedding = self.model.encode([text])
        chunk_embeddings = self.model.encode(chunks)
        similarities = cosine_similarity(text_embedding, chunk_embeddings).flatten()
        # Score and sort words by similarity.
        scored_chunks = sorted(
            [(chunks[i], score) for i, score in enumerate(similarities)],
            key=lambda x: x[1],
            reverse=True
        )
        keywords = []
        seen = set()
        for word, _ in scored_chunks:
            word = word.lower()
            if word not in self.stop_words and word not in seen and len(word) > 2:
                keywords.append(word)
                seen.add(word)
            if len(keywords) >= max_keywords:
                break
        return keywords
