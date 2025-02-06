from sentence_transformers import SentenceTransformer
import nltk

# Download required files once
model = SentenceTransformer('all-MiniLM-L6-v2')
nltk.download('stopwords')