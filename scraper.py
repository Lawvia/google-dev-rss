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
            
            print(f"Scraping {self.search_url}")
            
            # Look for Google blog specific selectors first - target the wrapper elements
            google_selectors = [
                '.search-result__wrapper',   # Main Google search result wrapper
                '.search-result',           # Google's search result items
                '.search-result-item',      # Alternative Google selector
                '[class*="search-result"]', # Any element with search-result in class
                '.post-preview',            # Google blog post previews
                '.blog-post-preview'        # Alternative blog preview
            ]
            
            found_articles = []
            for selector in google_selectors:
                found_articles = soup.select(selector)
                if found_articles:
                    print(f"Found {len(found_articles)} articles using selector: {selector}")
                    break
            
            # If no specific Google selectors work, try general ones
            if not found_articles:
                print("No Google-specific selectors found, trying general selectors...")
                general_selectors = [
                    'article',
                    '.post',
                    '.blog-post',
                    '[class*="post"]',
                    '.entry',
                    '.article'
                ]
                
                for selector in general_selectors:
                    found_articles = soup.select(selector)
                    if found_articles:
                        print(f"Found {len(found_articles)} articles using general selector: {selector}")
                        break
            
            # Process found articles - increased limit to get more articles
            if found_articles:
                max_articles = min(len(found_articles), 20)  # Process up to 20 articles instead of 10
                for i, article_elem in enumerate(found_articles[:max_articles]):
                    print(f"Processing article {i+1}/{max_articles}...")
                    article = self.extract_article_info(article_elem)
                    if article:
                        print(f"  Title: {article['title'][:50]}...")
                        print(f"  Date: {article['pub_date']}")
                        articles.append(article)
                    else:
                        print(f"  Skipped article {i+1} - could not extract info")
            else:
                print("No articles found with any selector, trying to find individual links...")
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
                        print(f"Found {len(links)} links using selector: {selector}")
                        # Process more links as potential articles
                        max_links = min(len(links), 20)  # Process up to 20 links
                        for i, link in enumerate(links[:max_links]):
                            href = link.get('href')
                            if href and self.is_valid_article_url(href):
                                article_url = urljoin(self.base_url, href)
                                print(f"  Processing link {i+1}/{max_links}: {article_url}")
                                article = self.scrape_individual_article(article_url, link.get_text())
                                if article:
                                    print(f"    Title: {article['title'][:50]}...")
                                    print(f"    Date: {article['pub_date']}")
                                    articles.append(article)
                        break
            
            # If still no articles, create a fallback entry
            if not articles:
                print("No articles found, creating fallback entry")
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
        
        print(f"Total articles extracted: {len(articles)}")
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
            # Find title - look for h3.search-result__title first, then fallbacks
            title_elem = (article_elem.find('h3', class_='search-result__title') or
                         article_elem.find(['h1', 'h2', 'h3', 'h4']) or 
                         article_elem.find('a') or 
                         article_elem.find(class_='title'))
            title = self.clean_text(title_elem.get_text()) if title_elem else "No Title"
            
            # Find link - look for the link inside the title
            link_elem = None
            if title_elem:
                link_elem = title_elem.find('a')  # Link inside title
            if not link_elem:
                link_elem = article_elem.find('a')  # Any link in the article
                
            link = urljoin(self.base_url, link_elem.get('href')) if link_elem and link_elem.get('href') else self.search_url
            
            # Find description - specifically look for p.search-result__summary
            description = title  # fallback
            summary_elem = article_elem.find('p', class_='search-result__summary')
            if summary_elem:
                description = self.clean_text(summary_elem.get_text())
                print(f"    Found summary: '{description[:50]}...'")
            else:
                # Try other description selectors as fallback
                desc_selectors = [
                    ('class', 'summary'),
                    ('class', 'excerpt'), 
                    ('class', 'description'), 
                    ('class', 'snippet'),
                    ('tag', 'p')
                ]
                for selector_type, selector_value in desc_selectors:
                    if selector_type == 'class':
                        desc_elem = article_elem.find(class_=selector_value)
                    else:
                        desc_elem = article_elem.find(selector_value)
                        
                    if desc_elem:
                        desc_text = self.clean_text(desc_elem.get_text())
                        if desc_text and len(desc_text) > 10:  # Make sure it's meaningful
                            description = desc_text
                            print(f"    Found description with {selector_type}='{selector_value}': '{desc_text[:50]}...'")
                            break
            
            # Find featured image
            featured_img = None
            img_elem = article_elem.find('img', class_='search-result__featured-img')
            if img_elem:
                img_src = img_elem.get('src')
                img_alt = img_elem.get('alt', '')
                if img_src:
                    featured_img = {
                        'src': img_src,
                        'alt': img_alt
                    }
                    print(f"    Found featured image: {img_src}")
            
            # Find date - specifically look for the p.search-result__eyebrow element
            pub_date = None
            eyebrow_elem = article_elem.find('p', class_='search-result__eyebrow')
            if eyebrow_elem:
                date_str = eyebrow_elem.get_text()
                print(f"    Found eyebrow date: '{date_str}'")
                pub_date = self.parse_date(date_str)
            else:
                # Try other date selectors as fallback
                date_selectors = [
                    ('class', 'search-result__eyebrow'),
                    ('class', 'search-result-eyebrow'), 
                    ('class', 'eyebrow'),
                    ('tag', 'time'),
                    ('class', 'date'),
                    ('class', 'published'),
                    ('class', 'post-date')
                ]
                
                for selector_type, selector_value in date_selectors:
                    if selector_type == 'class':
                        date_elem = article_elem.find(class_=selector_value)
                    else:
                        date_elem = article_elem.find(selector_value)
                        
                    if date_elem:
                        date_str = date_elem.get('datetime') or date_elem.get_text()
                        print(f"    Found date with {selector_type}='{selector_value}': '{date_str[:50]}...'")
                        pub_date = self.parse_date(date_str)
                        break
            
            if not pub_date:
                print("    No date found, using current time")
                pub_date = datetime.now(timezone.utc).isoformat()
            
            # Create enhanced description with image if available
            enhanced_description = description
            if featured_img:
                # Add image to description for RSS readers that support it
                enhanced_description = f'<img src="{featured_img["src"]}" alt="{featured_img["alt"]}" style="max-width: 100%; height: auto;"><br><br>{description}'
            
            # Debug output
            print(f"    Extracted:")
            print(f"      Title: {title[:50]}...")
            print(f"      Link: {link}")
            print(f"      Description: {description[:50]}...")
            print(f"      Image: {featured_img['src'] if featured_img else 'None'}")
            print(f"      Date: {pub_date}")
            
            return {
                'title': title[:200],  # Limit title length
                'link': link,
                'description': enhanced_description[:1000],  # Increased limit for image + text
                'pub_date': pub_date,
                'guid': link,
                'image': featured_img
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
            
            # Extract date - specifically look for search-result__eyebrow class and other variants
            pub_date = None
            
            date_selectors = [
                '.search-result__eyebrow',
                '.search-result-eyebrow', 
                '[class*="eyebrow"]',
                'time',
                '.date',
                '.published',
                '.post-date',
                '.article-date',
                '[datetime]'
            ]
            
            for selector in date_selectors:
                if selector.startswith('.') and not selector.startswith('['):
                    date_elem = soup.find(class_=selector.replace('.', ''))
                elif selector.startswith('[') and selector.endswith(']'):
                    date_elem = soup.find(attrs={selector[1:-1]: True})
                else:
                    date_elem = soup.find(selector)
                    
                if date_elem:
                    date_str = date_elem.get('datetime') or date_elem.get_text()
                    print(f"      Found date in individual article with selector '{selector}': '{date_str[:50]}...'")
                    pub_date = self.parse_date(date_str)
                    break
            
            if not pub_date:
                print(f"      No date found in individual article {url}, using current time")
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
                
                # Use CDATA for description to allow HTML content (for images)
                description_elem = ET.SubElement(item, "description")
                description_elem.text = f"<![CDATA[{article['description']}]]>"
                
                ET.SubElement(item, "pubDate").text = datetime.fromisoformat(article['pub_date'].replace('Z', '+00:00')).strftime("%a, %d %b %Y %H:%M:%S %z")
                ET.SubElement(item, "guid").text = article['guid']
                
                # Add image as enclosure if available
                if article.get('image'):
                    enclosure = ET.SubElement(item, "enclosure")
                    enclosure.set("url", article['image']['src'])
                    enclosure.set("type", "image/png")  # Default, could be improved by checking actual type
            
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