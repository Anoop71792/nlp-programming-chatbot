import requests
from bs4 import BeautifulSoup
import logging
from dataclasses import dataclass
from typing import List, Dict
import link_validator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

@dataclass
class Note:
    title: str
    url: str
    description: str
    source: str = "W3Schools"
    reliability: float = 1.0

def create_note(title: str, url: str, desc: str, source: str) -> Note:
    prediction = link_validator.predict_url_validity(url)
    return Note(title=title, url=url, description=desc, source=source, reliability=prediction.probability_valid)

def verify_url(url: str) -> bool:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        if response.status_code >= 400:
            response = requests.get(url, headers=headers, timeout=5, stream=True)
            response.close()
        return response.status_code < 400
    except requests.RequestException:
        return False

def search_youtube_resources(subject: str, module: str = "") -> List[Note]:
    try:
        notes = []
        search_query = f"{subject} programming tutorial"
        if module:
            search_query += f" module {module}"
            
        url = f"https://www.youtube.com/results?search_query={'+'.join(search_query.split())}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            import re
            video_ids = re.findall(r"videoId\":\"([^\"]+)\"", response.text)
            
            unique_video_ids = []
            for vid in video_ids:
                if vid not in unique_video_ids:
                    unique_video_ids.append(vid)

            video_ids = unique_video_ids[:5]
            
            video_data = re.findall(r"videoRenderer\":{\"videoId\":\"([^\"]+)\",\"thumbnail\".*?\"title\":{\"runs\":\[{\"text\":\"([^\"]+)\"", response.text)
            
            video_title_map = {vid: title for vid, title in video_data}
            
            for i, video_id in enumerate(video_ids):
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                if video_id in video_title_map:
                    title = video_title_map[video_id]
                else:
                    title = f"{subject.capitalize()} Programming Tutorial"
                
                notes.append(create_note(
                    f"YouTube: {title}",
                    video_url,
                    f"Video tutorial about {title}",
                    "YouTube"
                ))
                
                if len(notes) >= 5:
                    break
                    
        if not notes:
            logging.warning("Couldn't extract YouTube videos, adding fallback results")
            notes.append(create_note(
                f"YouTube: {subject.capitalize()} Programming Tutorials",
                f"https://www.youtube.com/results?search_query={subject}+programming+tutorial",
                f"Search results for {subject} programming tutorials on YouTube",
                "YouTube"
            ))                   
        return notes
    except Exception as e:
        logging.error(f"Error fetching YouTube resources: {e}")
        return [create_note(
            f"YouTube: {subject.capitalize()} Programming Tutorials",
            f"https://www.youtube.com/results?search_query={subject}+programming+tutorial",
            f"Search results for {subject} programming tutorials on YouTube",
            "YouTube"
        )]

def search_notes(subject: str = "", module: str = "") -> List[Note]:
    try:
        notes = []
        if subject.lower() in ['python', 'javascript', 'html', 'css', 'java', 
                             'php', 'sql', 'kotlin', 'c++', 'bootstrap', 
                             'jquery', 'react', 'xml', 'c']:
            url = f"https://www.w3schools.com/{subject.lower()}/"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', class_=['w3-bar-item', 'w3-button'], href=True):
                    href = link['href']
                    if href.startswith(f'/{subject.lower()}/'):
                        full_url = f"https://www.w3schools.com{href}"
                        notes.append(create_note(
                            f"W3Schools: {link.get_text(strip=True)}",
                            full_url,
                            f"Tutorial for {link.get_text(strip=True)}",
                            "W3Schools"
                        ))
        
        notes += search_youtube_resources(subject, module)
        
        notes.sort(key=lambda x: x.reliability, reverse=True)
        return notes[:5]
    
    except Exception as e:
        logging.error(f"Error: {e}")
        return []