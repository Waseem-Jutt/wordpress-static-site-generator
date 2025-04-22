import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import logging
from datetime import datetime
import json
import re
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wordpress_export.log'),
        logging.StreamHandler()
    ]
)

# Domain configuration from .env file
TARGET_DOMAIN = os.getenv("TARGET_DOMAIN")

# Target sitemap URL
sitemap_url = os.getenv("SITEMAP_URL", f"https://{TARGET_DOMAIN}/sitemap_index.xml")

# Local Virtual Host URL (for development)
local_host = os.getenv("LOCAL_HOST")

# URL For Assets, CSS, JS and Links (for production)
RELATIVE_URL = os.getenv("RELATIVE_URL")

# URL to use for replacing domain URLs (switch between local_host and RELATIVE_URL)
# For local testing: url_to_replace = local_host
# For production: url_to_replace = RELATIVE_URL
url_to_replace = os.getenv("URL_TO_REPLACE")  # Change this to local_host for local testing

# Create export folder with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
export_folder = f"exported_site_{timestamp}"
os.makedirs(export_folder, exist_ok=True)

# Create WordPress export structure
wordpress_data = {
    "site_info": {
        "name": "",
        "description": "",
        "url": "",
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    "content": {
        "pages": [],
        "posts": [],
        "categories": [],
        "tags": [],
        "media": [],
        "menus": []
    }
}

# Statistics
stats = {
    "pages_processed": 0,
    "assets_downloaded": 0,
    "errors": 0,
    "posts_found": 0,
    "categories_found": 0,
    "tags_found": 0
}

def extract_wordpress_data(soup, url):
    """Extract WordPress-specific data from the page"""
    data = {
        "url": url,
        "title": "",
        "content": "",
        "excerpt": "",
        "categories": [],
        "tags": [],
        "author": "",
        "date": "",
        "modified_date": "",
        "featured_image": "",
        "meta": {}
    }

    # Extract title
    if soup.title:
        data["title"] = soup.title.string.strip()

    # Extract meta description
    meta_desc = soup.find("meta", {"name": "description"})
    if meta_desc:
        data["meta"]["description"] = meta_desc.get("content", "")

    # Extract author
    author = soup.find("meta", {"name": "author"})
    if author:
        data["author"] = author.get("content", "")

    # Extract date
    date = soup.find("meta", {"property": "article:published_time"})
    if date:
        data["date"] = date.get("content", "")

    # Extract modified date
    modified = soup.find("meta", {"property": "article:modified_time"})
    if modified:
        data["modified_date"] = modified.get("content", "")

    # Extract categories and tags
    for term in soup.find_all("a", {"rel": "category tag"}):
        if "category" in term.get("rel", []):
            data["categories"].append(term.text.strip())
            wordpress_data["content"]["categories"].add(term.text.strip())
        if "tag" in term.get("rel", []):
            data["tags"].append(term.text.strip())
            wordpress_data["content"]["tags"].add(term.text.strip())

    # Extract featured image
    featured_img = soup.find("meta", {"property": "og:image"})
    if featured_img:
        data["featured_image"] = featured_img.get("content", "")

    # Extract main content
    content_div = soup.find("div", {"class": "entry-content"}) or soup.find("article")
    if content_div:
        data["content"] = content_div.get_text(strip=True)
        # Try to get excerpt
        excerpt = content_div.find("div", {"class": "entry-summary"})
        if excerpt:
            data["excerpt"] = excerpt.get_text(strip=True)

    return data

def download_file(file_url, save_path, file_type="asset"):
    try:
        # Skip external CDNs and non-target domain URLs
        parsed_url = urlparse(file_url)
        if TARGET_DOMAIN not in parsed_url.netloc:
            logging.info(f"Skipping external URL: {file_url}")
            return False
            
        # Check if file already exists
        if os.path.exists(save_path):
            logging.info(f"File already exists, skipping download: {file_url}")
            return True
            
        # time.sleep(0.5)
        response = requests.get(file_url, stream=True, timeout=30)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            stats["assets_downloaded"] += 1
            
            # Track media files
            if file_type == "media":
                wordpress_data["content"]["media"].append({
                    "url": file_url,
                    "local_path": save_path,
                    "type": os.path.splitext(save_path)[1][1:].lower()
                })
            
            logging.info(f"Downloaded: {file_url}")
            return True
        else:
            logging.warning(f"Failed to download {file_url}: Status code {response.status_code}")
    except Exception as e:
        logging.error(f"Error downloading {file_url}: {e}")
        stats["errors"] += 1
    return False

def replace_domain_urls(soup, page_url):
    """Replace all URLs containing TARGET_DOMAIN with url_to_replace in one shot"""
    logging.info(f"Replacing domain URLs with {url_to_replace} for {page_url}")
    
    # Convert the entire HTML to string
    html_str = str(soup)
    
    # Replace all instances of the domain with protocol variations
    replacements = [
        (f"https://{TARGET_DOMAIN}", url_to_replace.rstrip('/')),
        (f"http://{TARGET_DOMAIN}", url_to_replace.rstrip('/')),
        (f"//{TARGET_DOMAIN}", url_to_replace.rstrip('/').replace('http:', '').replace('https:', '')),
        (TARGET_DOMAIN, url_to_replace.rstrip('/').replace('http://', '').replace('https://', ''))
    ]
    
    for old, new in replacements:
        html_str = html_str.replace(old, new)
    
    # Parse the modified HTML back to BeautifulSoup
    return BeautifulSoup(html_str, 'html.parser')

def get_all_internal_links(soup, base_url):
    """Extract all internal links from a page"""
    internal_links = set()
    
    # Find all links on the page
    for link in soup.find_all("a", href=True):
        href = link["href"]
        
        # Skip empty links, anchors, and external links
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
            
        # Make the URL absolute if it's relative
        absolute_url = urljoin(base_url, href)
        
        # Only include links from the same domain
        if TARGET_DOMAIN in absolute_url:
            internal_links.add(absolute_url)
            logging.info(f"Found internal link: {absolute_url}")
    
    return internal_links

def collect_all_internal_links():
    """Collect all internal links from the sitemap and return them as a unique list"""
    all_internal_links = set()
    
    # Get links from the sitemap
    sitemap_links = get_sitemap_links(sitemap_url)
    all_internal_links.update(sitemap_links)
    logging.info(f"Found {len(sitemap_links)} links in sitemap")
    
    # Process each sitemap link to find additional internal links
    processed_urls = set()
    urls_to_process = set(sitemap_links)
    
    while urls_to_process:
        current_url = urls_to_process.pop()
        if current_url in processed_urls:
            continue
            
        processed_urls.add(current_url)
        
        try:
            logging.info(f"Fetching links from: {current_url}")
            response = requests.get(current_url, timeout=30)
            if response.status_code != 200:
                logging.error(f"Failed to fetch {current_url}: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, "html.parser")
            internal_links = get_all_internal_links(soup, current_url)
            
            # Add new links to the processing queue
            new_links = internal_links - processed_urls
            urls_to_process.update(new_links)
            all_internal_links.update(internal_links)
            
            logging.info(f"Found {len(internal_links)} internal links on {current_url}")
            logging.info(f"Added {len(new_links)} new links to process")
            logging.info(f"Total unique links found so far: {len(all_internal_links)}")
            
        except Exception as e:
            logging.error(f"Error processing {current_url}: {e}")
    
    logging.info(f"Total unique links found across the site: {len(all_internal_links)}")
    return list(all_internal_links)

def process_srcset_images(soup, page_url):
    """Process all images with srcset attributes and download them"""
    for img in soup.find_all("img", srcset=True):
        srcset = img["srcset"]
        new_srcset = []
        
        # Split the srcset into individual sources
        sources = [s.strip() for s in srcset.split(",")]
        
        for source in sources:
            # Split into URL and size descriptor
            parts = source.strip().split(" ")
            if len(parts) >= 1:
                img_url = parts[0]
                size_descriptor = " ".join(parts[1:]) if len(parts) > 1 else ""
                
                # Make the URL absolute if it's relative
                img_url = urljoin(page_url, img_url)
                
                # Get the path after the domain
                img_path = urlparse(img_url).path.lstrip("/")
                
                # Create the full path in export folder maintaining original structure
                img_file_path = os.path.join(export_folder, img_path)
                
                if download_file(img_url, img_file_path, "media"):
                    # Update src to point to the root level path
                    new_url = f"{url_to_replace}{img_path}"
                    new_srcset.append(f"{new_url} {size_descriptor}".strip())
        
        # Update the srcset attribute with the new URLs
        if new_srcset:
            img["srcset"] = ", ".join(new_srcset)

def process_page(page_url):
    """Process a single page and save it to the export folder"""
    try:
        # Skip if not from target domain
        if TARGET_DOMAIN not in urlparse(page_url).netloc:
            logging.info(f"Skipping external page: {page_url}")
            return

        # Get the path from the URL and create the folder structure
        path = urlparse(page_url).path.strip("/")
        if not path:  # Homepage
            page_folder = export_folder
        else:
            # Create the full path maintaining the original structure
            page_folder = os.path.join(export_folder, path)
        
        # Check if the page has already been processed
        if os.path.exists(os.path.join(page_folder, "index.html")):
            logging.info(f"Page already processed, skipping: {page_url}")
            return

        logging.info(f"Processing page: {page_url}")
        response = requests.get(page_url, timeout=30)
        if response.status_code != 200:
            logging.error(f"Failed to fetch {page_url}: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        
        os.makedirs(page_folder, exist_ok=True)

        # Extract WordPress data
        page_data = extract_wordpress_data(soup, page_url)
        
        # Determine if it's a post or page
        is_post = bool(soup.find("article", {"class": "post"}))
        content_type = "posts" if is_post else "pages"
        wordpress_data["content"][content_type].append(page_data)
        
        if is_post:
            stats["posts_found"] += 1
        stats["categories_found"] = len(wordpress_data["content"]["categories"])
        stats["tags_found"] = len(wordpress_data["content"]["tags"])

        # Process CSS
        for link in soup.find_all("link", rel="stylesheet"):
            if "href" in link.attrs:
                css_url = urljoin(page_url, link["href"])
                # Get the path after the domain
                css_path = urlparse(css_url).path.lstrip("/")
                # Create the full path in export folder maintaining original structure
                css_file_path = os.path.join(export_folder, css_path)
                if download_file(css_url, css_file_path):
                    # Update href to point to the root level path
                    link["href"] = f"{url_to_replace}{css_path}"

        # Process JS
        for script in soup.find_all("script", src=True):
            if "src" in script.attrs:
                js_url = urljoin(page_url, script["src"])
                # Get the path after the domain
                js_path = urlparse(js_url).path.lstrip("/")
                # Create the full path in export folder maintaining original structure
                js_file_path = os.path.join(export_folder, js_path)
                if download_file(js_url, js_file_path):
                    # Update src to point to the root level path
                    script["src"] = f"{url_to_replace}{js_path}"

        # Process Images
        for img in soup.find_all("img", src=True):
            if "src" in img.attrs:
                img_url = urljoin(page_url, img["src"])
                # Get the path after the domain
                img_path = urlparse(img_url).path.lstrip("/")
                # Create the full path in export folder maintaining original structure
                img_file_path = os.path.join(export_folder, img_path)
                if download_file(img_url, img_file_path, "media"):
                    # Update src to point to the root level path
                    img["src"] = f"{url_to_replace}{img_path}"
        
        # Process srcset images
        process_srcset_images(soup, page_url)

        # Replace all domain URLs with url_to_replace in one shot
        soup = replace_domain_urls(soup, page_url)

        # Save Modified HTML
        html_path = os.path.join(page_folder, "index.html")
        with open(html_path, "w", encoding="utf-8") as file:
            file.write(soup.prettify())

        stats["pages_processed"] += 1
        logging.info(f"Page exported: {html_path}")

    except Exception as e:
        logging.error(f"Error processing page {page_url}: {e}")
        stats["errors"] += 1

def get_sitemap_links(sitemap_url):
    try:
        # Skip if not from target domain
        if TARGET_DOMAIN not in urlparse(sitemap_url).netloc:
            logging.info(f"Skipping external sitemap: {sitemap_url}")
            return []

        sitemap_response = requests.get(sitemap_url, timeout=30)
        if sitemap_response.status_code != 200:
            logging.error(f"Failed to fetch sitemap: {sitemap_url}")
            return []

        # Parse XML properly
        root = ET.fromstring(sitemap_response.content)
        urls = []
        
        # Handle both sitemap index and regular sitemaps
        for elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            url = elem.text.strip()
            if url.endswith(".xml"):
                urls.extend(get_sitemap_links(url))
            else:
                urls.append(url)

        return urls
    except Exception as e:
        logging.error(f"Error processing sitemap {sitemap_url}: {e}")
        return []

def save_wordpress_export():
    """Save the complete WordPress export data"""
    # Convert sets to lists for JSON serialization
    wordpress_data["content"]["categories"] = list(wordpress_data["content"]["categories"])
    wordpress_data["content"]["tags"] = list(wordpress_data["content"]["tags"])
    
    # Save the complete WordPress export
    export_path = os.path.join(export_folder, "wordpress_export.json")
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(wordpress_data, f, indent=4)
    
    # Save statistics
    stats_path = os.path.join(export_folder, "export_statistics.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)

def download_allow_urls():
    """Read URLs from the local allow-urls.txt file and download their content"""
    try:
        # Check if the file exists
        if not os.path.exists("allow-urls.txt"):
            logging.error("allow-urls.txt file not found in the current directory")
            return False
        
        # Read the file
        with open("allow-urls.txt", "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
        
        logging.info(f"Read {len(urls)} URLs from allow-urls.txt")
        
        # Download each URL
        success_count = 0
        for i, url in enumerate(urls, 1):
            try:
                logging.info(f"Downloading URL {i}/{len(urls)}: {url}")
                
                # Get the filename from the URL
                filename = url.split("/")[-1]
                if not filename:
                    filename = f"url_{i}.txt"
                
                # Download the content
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    # Save the file
                    file_path = os.path.join(export_folder, filename)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    
                    logging.info(f"Successfully downloaded to {file_path}")
                    success_count += 1
                else:
                    logging.error(f"Failed to download {url}: Status code {response.status_code}")
                    
            except Exception as e:
                logging.error(f"Error downloading {url}: {e}")
        
        # Save all URLs to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        urls_file = f"downloaded_urls_{timestamp}.txt"
        urls_path = os.path.join(export_folder, urls_file)
        with open(urls_path, "w", encoding="utf-8") as f:
            for url in urls:
                f.write(f"{url}\n")
        
        logging.info(f"Saved {len(urls)} URLs to {urls_path}")
        logging.info(f"Successfully downloaded {success_count}/{len(urls)} URLs")
        
        return success_count > 0
            
    except Exception as e:
        logging.error(f"Error processing allow-urls.txt: {e}")
        return False

# Main execution
if __name__ == "__main__":
    logging.info("Starting WordPress site export...")
    
    # First, collect all internal links from the site
    all_internal_links = collect_all_internal_links()
    
    # Save unique links to a file
    links_file_path = os.path.join(export_folder, "all_internal_links.txt")
    with open(links_file_path, "w", encoding="utf-8") as f:
        for link in sorted(all_internal_links):
            f.write(f"{link}\n")
    logging.info(f"Saved {len(all_internal_links)} unique links to {links_file_path}")
    
    # Also save links as JSON for easier programmatic access
    links_json_path = os.path.join(export_folder, "all_internal_links.json")
    with open(links_json_path, "w", encoding="utf-8") as f:
        json.dump(all_internal_links, f, indent=4)
    logging.info(f"Saved links to JSON file: {links_json_path}")
    
    logging.info(f"Found {len(all_internal_links)} total links to process")
    
    # Process each page
    for page_url in all_internal_links:
        process_page(page_url)
        logging.info(f"Progress: {stats['pages_processed']}/{len(all_internal_links)} pages processed")
    
    # Save the complete WordPress export
    save_wordpress_export()

    # Download allow-urls.txt file
    download_allow_urls()

    # Print final statistics
    logging.info("\nExport Statistics:")
    logging.info(f"Pages Processed: {stats['pages_processed']}")
    logging.info(f"Posts Found: {stats['posts_found']}")
    logging.info(f"Categories Found: {stats['categories_found']}")
    logging.info(f"Tags Found: {stats['tags_found']}")
    logging.info(f"Assets Downloaded: {stats['assets_downloaded']}")
    logging.info(f"Errors Encountered: {stats['errors']}")
    logging.info(f"Export completed! Files saved in: {export_folder}")
