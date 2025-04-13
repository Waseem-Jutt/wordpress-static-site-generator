# 🌀 WordPress to Static Build Converter

This tool converts an entire WordPress website into a static HTML build. It crawls all internal links from the sitemap, downloads assets (CSS, JS, Images), and rewrites all internal URLs for offline or static web hosting.

## 🚀 Features

- 📄 Extracts WordPress pages, posts, metadata, featured images, authors, categories, tags
- 🔗 Rewrites all internal URLs to your custom host or local setup
- 🎨 Downloads and rewrites paths for all CSS, JS, and image files
- 🧠 Generates structured JSON export of site content
- 📂 Maintains directory structure matching original URLs
- 📊 Logs and stats of all processed pages and assets
- 📁 Optionally fetches custom URLs from `allow-urls.txt`

## 🛠 Requirements

- Python 3.7+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## ⚙️ Setup

### 1. Create a Virtual Environment (Recommended)

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root with the following variables:

```env
TARGET_DOMAIN=example.com
SITEMAP_URL=https://example.com/sitemap_index.xml
LOCAL_HOST=http://localhost:3000
RELATIVE_URL=https://static.example.com
URL_TO_REPLACE=https://static.example.com
```

- `TARGET_DOMAIN`: Your WordPress domain (no protocol)
- `SITEMAP_URL`: Sitemap index or main sitemap URL
- `LOCAL_HOST`: URL for local development testing
- `RELATIVE_URL`: Production URL for assets and links
- `URL_TO_REPLACE`: Used to rewrite all internal URLs (use LOCAL_HOST for development or RELATIVE_URL for production)

## ▶️ Usage

### Running the Main Script

```bash
python export_website.py
```

All exported files will be saved in a folder named like `exported_site_20250413_171530`.

### Running Specific Functions

If you want to run just the `download_allow_urls()` function:

```bash
python -c "from export_website import download_allow_urls; download_allow_urls()"
```

### Using allow-urls.txt

Create a file named `allow-urls.txt` in the project root with one URL per line:

```
https://example.com/api/data.json
https://example.com/tools/info
```

The script will download these URLs during the export process.

## 📂 Exported Files

```
exported_site_YYYYMMDD_HHMMSS/
│
├── all_internal_links.txt        # List of all internal links
├── all_internal_links.json       # Same as above in JSON
├── wordpress_export.json         # Structured data of all content
├── export_statistics.json        # Export metrics
├── downloaded_urls_*.txt         # Optional additional downloaded URLs
└── [HTML & Assets]               # Static site structure with assets
```

## 🧠 How It Works

1. Crawls the sitemap to get all internal pages
2. Extracts content: titles, excerpts, post content, images, meta info
3. Downloads referenced CSS, JS, and image files
4. Rewrites all internal links to your provided domain
5. Saves everything as local HTML files

## 🔍 Troubleshooting

- **Missing .env file**: The script will use default values if the .env file is missing
- **Connection errors**: Check your internet connection and the TARGET_DOMAIN value
- **Permission errors**: Ensure you have write permissions in the current directory
- **Missing allow-urls.txt**: The script will continue without this file

## 📄 License

MIT License. Feel free to use, improve, and contribute.

## 🤝 Contribute

Pull requests are welcome! Improve functionality, performance, or add new features.

## 🙋‍♂️ Author

Made with ❤️ by Waseem-Jutt

GitHub: https://github.com/Waseem-Jutt
