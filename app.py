from flask import Flask, request, jsonify
from flask_cors import CORS
import web_scraper
import time
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from typing import Dict, Tuple, Any, List

app = Flask(__name__)
CORS(app)

notes_cache = {}
CACHE_EXPIRATION = 300

class NLPProcessor:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.entity_patterns = {
            'module': r'\b(module|mod|unit)\s*(\d+)\b',
            'difficulty': r'\b(beginner|intermediate|advanced)\b'
        }

    def initialize(self):
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)

    def process(self, text: str) -> Tuple[str, Dict[str, Any]]:
        text = text.lower().strip()
        intent = self._get_intent(text)
        entities = self._extract_entities(text)
        return intent, entities

    def _get_intent(self, text: str) -> str:
        if re.search(r'\b(hi|hello|hey)\b', text):
            return "greeting"
        elif re.search(r'\b(help|assist)\b', text):
            return "help"
        return "search_notes"

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        entities = {
            'subject': self._detect_subject(text),
            'module': self._extract_pattern(text, 'module'),
            'difficulty': self._extract_pattern(text, 'difficulty'),
            'concepts': self._extract_keywords(text)
        }
        return entities

    def _extract_pattern(self, text: str, pattern_type: str) -> str:
        match = re.search(self.entity_patterns[pattern_type], text)
        return match.group(2) if match else ""

    def _extract_keywords(self, text: str) -> List[str]:
        tokens = word_tokenize(text.lower())
        common_words = set(stopwords.words('english')).union(['tutorial', 'learn', 'help'])
        return [t for t in tokens if t not in common_words and len(t) > 3][:3]

    def _detect_subject(self, text: str) -> str:
        subjects = {
            'python': ['python', 'django', 'flask'],
            'javascript': ['javascript', 'js'],
            'html': ['html', 'html5'],
            'css': ['css', 'css3'],
            'java': ['java', 'spring'],
            'php': ['php', 'laravel', 'wordpress'],
            'sql': ['sql', 'mysql', 'postgresql'],
            'kotlin': ['kotlin', 'android dev'],
            'c++': ['c++', 'cpp'],
            'bootstrap': ['bootstrap'],
            'jquery': ['jquery'],
            'react': ['react', 'reactjs'],
            'xml': ['xml'],
            'c': ['c programming', 'c language']
        }
        text = text.lower()
        for subject, keywords in subjects.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in keywords):
                return subject
        return ""

nlp_processor = NLPProcessor()

def process_message(text: str) -> Tuple[str, Dict[str, Any]]:
    return nlp_processor.process(text)

@app.route('/')
def home():
    return jsonify({
        "service": "Programming Resources Assistant Backend",
        "version": "2.1",
        "description": "Intelligent tutorial and notes search service with link validation prediction"
    })

@app.route('/chat', methods=['POST'])
def chat():
    start_time = time.time()
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid content type"}), 415
            
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Message required"}), 400

        message = data['message'].strip()
        if not message:
            return jsonify({"error": "Empty message"}), 400

        if time.time() - start_time > 3:
            return jsonify({
                "reply": "Server processing timeout. Please try again.",
                "links": []
            })
        intent, entities = process_message(message)
        response = build_response(intent, entities)
        
        return jsonify(response)

    except Exception as e:
        print(f"Chat processing error: {e}")
        return jsonify({
            "reply": "Apologies, our service is temporarily unavailable.",
            "links": []
        }), 500

def build_response(intent: str, entities: Dict[str, str]) -> Dict[str, Any]:
    if intent == 'greeting':
        return {
            "reply": "Hello! I'm your Programming Resources Assistant. I can help you find tutorials and learning resources for various programming languages and technologies. What would you like to learn today?",
            "links": []
        }
    
    if intent == 'help':
        return {
            "reply": "I can help you find tutorials for various programming languages like Python, JavaScript, HTML, CSS, Java, and more. Just ask for tutorials or resources in a specific language or technology!",
            "links": []
        }
    
    if intent == 'search_notes':
        subject = entities.get('subject', '').lower()
        module = entities.get('module', '')
        
        cache_key = f"{subject}_{module}"
        if cache_key in notes_cache and time.time() - notes_cache[cache_key]['timestamp'] < CACHE_EXPIRATION:
            notes = notes_cache[cache_key]['data']
        else:
            notes = web_scraper.search_notes(subject, module)
            notes_cache[cache_key] = {
                'data': notes,
                'timestamp': time.time()
            }
        
        formatted_links = [{
            "title": note.title,
            "url": note.url,
            "description": note.description,
            "source": note.source,
            "reliability": note.reliability if hasattr(note, 'reliability') else 1.0
        } for note in notes]
        
        if not notes:
            return {
                "reply": f"Hmm, I couldn't find specific tutorials for {subject}. Would you like to try another language or technology?",
                "links": []
            }
        
        reply = f"Here are learning resources for {subject.capitalize()}"
        if module:
            reply += f" (Module {module})"
        
        if any(link.get('reliability', 1.0) < 0.85 for link in formatted_links):
            reply += ". Note: Some links may have reduced reliability but still provide valuable resources."
        
        return {
            "reply": reply,
            "links": formatted_links
        }
    
    return {
        "reply": "I specialize in finding programming tutorials. Ask me about languages like Python, JavaScript, HTML, CSS, or Java!",
        "links": []
    }

if __name__ == '__main__':
    nlp_processor.initialize()
    app.run(host='0.0.0.0', port=5000, threaded=True)