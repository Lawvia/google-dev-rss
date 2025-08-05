#!/usr/bin/env python3
"""
RSS Feed Generator for Google Developers Search Blog
Scrapes content from https://developers.googleblog.com/en/search/ and generates RSS feed
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import re
import os
import sys
from urllib.parse import urljoin, urlparse
import time

class GoogleDevBlogScraper:
    def __init__(self):
        self.base_url = "https://developers.googleblog.com"
        self.search_url = "https://developers.googleblog.com/en/search/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_page(self, url, max_retries=3):
        """Fetch a web page with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def parse_date(self, date_str):
        """Parse various date formats to ISO format"""
        try:
            # Clean the date string - remove tags and extra content
            if '/' in date_str and any(word in date_str.upper() for word in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']):
                # Extract date part before the first '/' (e.g., "AUG. 1, 2025 / TAGS" -> "AUG. 1, 2025")
                date_str = date_str.split('/')[0].strip()
            
            # Common formats found on Google blogs
            formats = [
                "%B %d, %Y",    # January 15, 2024
                "%b %d, %Y",    # Jan 15, 2024
                "%B. %d, %Y",   # January. 15, 2024
                "%b. %d, %Y",   # Jan. 15, 2024
                "%Y-%m-%d",     # 2024-01-15
                "%m/%d/%Y",     # 01/15/2024
            ]
            
            # Clean up abbreviations with periods
            date_str = date_str.replace('JAN.', 'JAN').replace('FEB.', 'FEB').replace('MAR.', 'MAR')
            date_str = date_str.replace('APR.', 'APR').replace('MAY.', 'MAY').replace('JUN.', 'JUN')
            date_str = date_str.replace('JUL.', 'JUL').replace('AUG.', 'AUG').replace('SEP.', 'SEP')
            date_str = date_str.replace('OCT.', 'OCT').replace('NOV.', 'NOV').replace('DEC.', 'DEC')
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    continue
            
            # If no format matches, return current time
            return datetime.now(timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()
    
    def clean_text(self, text):
        """Clean and normalize text content"""
        if not text:
            return ""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def scrape_articles(self, max_pages=3):
        """Scrape articles from the search page"""
        articles = []
        
        try:
            # Start with the main search page
            response = self.fetch_page(self.search_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for article links and content
            # Google's blog structure may vary, so we'll try multiple selectors
            article_selectors = [
                'article',
                '.post',
                '.blog-post',
                '[class*="post"]',
                '.entry',
                '.article'
            ]
            
            found_articles = []
            for selector in article_selectors:
                found_articles = soup.select(selector)
                if found_articles:
                    break
            
            # If no articles found with above selectors, try finding links
            if not found_articles:
                # Look for links that might be article titles
                link_selectors = [
                    'a[href*="/en/"]',
                    'a[href*="blog"]',
                    'h2 a, h3 a, h4 a',
                    '.title a'
                ]
                
                for selector in link_selectors:
                    links = soup.select(selector)
                    if links:
                        # Process first few links as potential articles
                        for link in links[:10]:
                            href = link.get('href')
                            if href and self.is_valid_article_url(href):
                                article_url = urljoin(self.base_url, href)
                                article = self.scrape_individual_article(article_url, link.get_text())
                                if article:
                                    articles.append(article)
                        break
            else:
                # Process found articles
                for article_elem in found_articles[:10]:  # Limit to prevent overload
                    article = self.extract_article_info(article_elem)
                    if article:
                        articles.append(article)
            
            # If still no articles, create a fallback entry
            if not articles:
                articles.append({
                    'title': 'Google Developers Search Blog',
                    'link': self.search_url,
                    'description': 'Latest updates from Google Developers Search team',
                    'pub_date': datetime.now(timezone.utc).isoformat(),
                    'guid': self.search_url
                })
                
        except Exception as e:
            print(f"Error scraping articles: {e}")
            # Return a fallback article
            articles.append({
                'title': 'Google Developers Search Blog - Error',
                'link': self.search_url,
                'description': f'Error occurred while scraping: {str(e)}',
                'pub_date': datetime.now(timezone.utc).isoformat(),
                'guid': f"{self.search_url}#error-{int(time.time())}"
            })
        
        return articles
    
    def is_valid_article_url(self, url):
        """Check if URL looks like a valid article"""
        if not url:
            return False
        
        # Skip certain URLs
        skip_patterns = [
            'javascript:',
            'mailto:',
            '#',
            '/search',
            '/tag',
            '/category',
            'google.com/search'
        ]
        
        for pattern in skip_patterns:
            if pattern in url.lower():
                return False
        
        return True
    
    def extract_article_info(self, article_elem):
        """Extract article information from article element"""
        try:
            title_elem = article_elem.find(['h1', 'h2', 'h3', 'h4']) or article_elem.find('a')
            title = self.clean_text(title_elem.get_text()) if title_elem else "No Title"
            
            # Find link
            link_elem = article_elem.find('a') or title_elem
            link = urljoin(self.base_url, link_elem.get('href')) if link_elem and link_elem.get('href') else self.search_url
            
            # Find description
            desc_elem = article_elem.find(['p', '.summary', '.excerpt', '.description'])
            description = self.clean_text(desc_elem.get_text()) if desc_elem else title
            
            # Find date - specifically look for search-result__eyebrow class
            date_elem = article_elem.find(class_='search-result__eyebrow') or article_elem.find(['time', '.date', '.published'])
            if date_elem:
                date_str = date_elem.get('datetime') or date_elem.get_text()
                pub_date = self.parse_date(date_str)
            else:
                pub_date = datetime.now(timezone.utc).isoformat()
            
            return {
                'title': title[:200],  # Limit title length
                'link': link,
                'description': description[:500],  # Limit description length
                'pub_date': pub_date,
                'guid': link
            }
            
        except Exception as e:
            print(f"Error extracting article info: {e}")
            return None
    
    def scrape_individual_article(self, url, fallback_title=""):
        """Scrape an individual article page"""
        try:
            response = self.fetch_page(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1') or soup.find('title')
            title = self.clean_text(title_elem.get_text()) if title_elem else fallback_title
            
            # Extract description/content
            content_selectors = ['.content', '.post-content', '.entry-content', 'article p']
            description = ""
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Get first paragraph or first 500 characters
                    paragraphs = content_elem.find_all('p')
                    if paragraphs:
                        description = self.clean_text(paragraphs[0].get_text())
                    else:
                        description = self.clean_text(content_elem.get_text())[:500]
                    break
            
            if not description:
                description = title
            
            # Extract date - specifically look for search-result__eyebrow class
            date_elem = soup.find(class_='search-result__eyebrow') or soup.find(['time', '.date', '.published']) or soup.find(attrs={'datetime': True})
            if date_elem:
                date_str = date_elem.get('datetime') or date_elem.get_text()
                pub_date = self.parse_date(date_str)
            else:
                pub_date = datetime.now(timezone.utc).isoformat()
            
            return {
                'title': title[:200],
                'link': url,
                'description': description[:500],
                'pub_date': pub_date,
                'guid': url
            }
            
        except Exception as e:
            print(f"Error scraping individual article {url}: {e}")
            return None
    
    def generate_rss(self, articles, output_file="feed.xml"):
        """Generate RSS feed from articles"""
        try:
            # Create RSS structure
            rss = ET.Element("rss", version="2.0")
            rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
            
            channel = ET.SubElement(rss, "channel")
            
            # Channel metadata
            ET.SubElement(channel, "title").text = "Google Developers Search Blog"
            ET.SubElement(channel, "link").text = self.search_url
            ET.SubElement(channel, "description").text = "Latest updates from Google Developers Search team"
            ET.SubElement(channel, "language").text = "en-us"
            ET.SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
            
            # Self-referencing atom link
            atom_link = ET.SubElement(channel, "atom:link")
            atom_link.set("href", "https://your-username.github.io/your-repo-name/feed.xml")
            atom_link.set("rel", "self")
            atom_link.set("type", "application/rss+xml")
            
            # Add articles as items
            for article in articles:
                item = ET.SubElement(channel, "item")
                ET.SubElement(item, "title").text = article['title']
                ET.SubElement(item, "link").text = article['link']
                ET.SubElement(item, "description").text = article['description']
                ET.SubElement(item, "pubDate").text = datetime.fromisoformat(article['pub_date'].replace('Z', '+00:00')).strftime("%a, %d %b %Y %H:%M:%S %z")
                ET.SubElement(item, "guid").text = article['guid']
            
            # Create tree and write to file
            tree = ET.ElementTree(rss)
            ET.indent(tree, space="  ", level=0)  # Pretty print
            
            # Write to file
            with open(output_file, 'wb') as f:
                tree.write(f, encoding='utf-8', xml_declaration=True)
            
            print(f"RSS feed generated successfully: {output_file}")
            print(f"Total articles: {len(articles)}")
            
        except Exception as e:
            print(f"Error generating RSS feed: {e}")
            raise

def main():
    """Main function"""
    try:
        scraper = GoogleDevBlogScraper()
        
        print("Starting to scrape Google Developers Search blog...")
        articles = scraper.scrape_articles()
        
        if not articles:
            print("No articles found!")
            sys.exit(1)
        
        print(f"Found {len(articles)} articles")
        
        # Generate RSS feed
        output_file = os.environ.get('RSS_OUTPUT_FILE', 'feed.xml')
        scraper.generate_rss(articles, output_file)
        
        print("RSS feed generation completed successfully!")
        
    except Exception as e:
        print(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
