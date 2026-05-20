import re
import logging
from urllib.parse import urlparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
import joblib
import os
from typing import Dict, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)

@dataclass
class LinkPrediction:
    url: str
    probability_valid: float
    prediction: str

class LinkValidator:
    def __init__(self):
        self.domain_reliability = {
            'w3schools.com': 0.98,
            'youtube.com': 0.99
        }
        self.suspicious_patterns = [r'temp[-_]', r'old[-_]', r'deprecated']
        self.model_dir = "models" 
        self.model_path = os.path.join(self.model_dir, "link_validator_model.joblib")
        self.vectorizer_path = os.path.join(self.model_dir, "link_vectorizer.joblib")
        self.clf = None
        self.vectorizer = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize or train the model"""
        try:
            os.makedirs(self.model_dir, exist_ok=True)
            
            if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
                self.clf = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                logging.info("Loaded trained model")
            else:
                logging.info("No trained model found - training new one")
                self._train_model()
        except Exception as e:
            logging.error(f"Error initializing model: {e}")
            raise

    def _train_model(self):
        """Train initial model with synthetic data"""
        logging.info("Training new model")
        
        self.training_data = []
        self.training_labels = []
        
        for domain, reliability in self.domain_reliability.items():
            for i in range(10):
                url = f"https://{domain}/valid-path-{i}"
                self.training_data.append(self._extract_features(url))
                self.training_labels.append(1)
                
        broken_domains = ['test.com', 'example.org', 'temp-site.net']
        for domain in broken_domains:
            for i in range(10):
                url = f"http://{domain}/broken-{i}"
                self.training_data.append(self._extract_features(url))
                self.training_labels.append(0)
        
        self.vectorizer = DictVectorizer(sparse=False)               #train model
        X = self.vectorizer.fit_transform(self.training_data)
        self.clf = RandomForestClassifier(n_estimators=50, random_state=42)
        self.clf.fit(X, self.training_labels)
        
        joblib.dump(self.clf, self.model_path)
        joblib.dump(self.vectorizer, self.vectorizer_path)
        logging.info("Model trained and saved")

    def _extract_features(self, url: str) -> Dict[str, Any]:
        """Extract features from URL"""
        features = {
            'domain': '',
            'is_https': 0,
            'url_length': len(url),
            'has_suspicious': 0,
            'domain_reliability': 0.75
        }
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            features['domain'] = domain
            features['is_https'] = int(parsed.scheme == 'https')
            features['domain_reliability'] = self.domain_reliability.get(domain, 0.75)
            
            for pattern in self.suspicious_patterns:
                if re.search(pattern, url):
                    features['has_suspicious'] = 1
                    break
                    
        except Exception as e:
            logging.error(f"Error extracting features: {e}")
            
        return features

    def predict(self, url: str) -> LinkPrediction:
        """Predict URL validity"""
        try:
            if not self.clf or not self.vectorizer:
                raise ValueError("Model not initialized")
                
            features = self._extract_features(url)
            X = self.vectorizer.transform([features])
            proba = self.clf.predict_proba(X)[0][1]
            return LinkPrediction(
                url=url,
                probability_valid=proba,
                prediction="valid" if proba > 0.75 else "broken"
            )
        except Exception as e:
            logging.error(f"Prediction error for {url}: {e}")
            
            domain = urlparse(url).netloc.replace('www.', '')
            reliability = self.domain_reliability.get(domain, 0.75)
            return LinkPrediction(url, reliability, "fallback")

validator = LinkValidator()

def predict_url_validity(url: str) -> LinkPrediction:
    return validator.predict(url)

def should_verify_url(url: str) -> bool:
    prediction = predict_url_validity(url)
    return prediction.probability_valid < 0.85

def record_verification_result(url: str, is_valid: bool):
    pass  

if __name__ == "__main__":
    test_url = "https://docs.python.org/3/tutorial/"
    print(f"Testing URL: {test_url}")
    print(predict_url_validity(test_url))
