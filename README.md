# Google Developers Blog RSS Generator

This project automatically scrapes content from the [Google Developers Search blog](https://developers.googleblog.com/en/search/) and generates an RSS feed using GitHub Actions.

## Features

- ✅ Automatic scraping every 6 hours
- ✅ RSS feed generation in standard format
- ✅ GitHub Pages deployment for easy access
- ✅ Error handling and retry logic
- ✅ Manual trigger support
- ✅ Feed validation

## Quick Setup

### 1. Fork or Create Repository

Create a new repository or fork this one to your GitHub account.

### 2. Enable GitHub Pages

1. Go to your repository settings
2. Navigate to "Pages" section
3. Under "Source", select "GitHub Actions"

### 3. File Structure

Make sure your repository has these files:

```
your-repo/
├── .github/
│   └── workflows/
│       └── rss-generator.yml
├── scraper.py
├── requirements.txt
└── README.md
```

### 4. Update Configuration

Edit the workflow file (`.github/workflows/rss-generator.yml`) and update:

- Line with `https://your-username.github.io/your-repo-name/feed.xml`
- Replace with your actual GitHub username and repository name

### 5. Manual Trigger (Optional)

You can manually trigger the workflow:

1. Go to "Actions" tab in your repository
2. Select "Generate RSS Feed" workflow
3. Click "Run workflow"

## Usage

### RSS Feed URL

Once deployed, your RSS feed will be available at:
```
https://your-username.github.io/your-repo-name/feed.xml
```

### Adding to RSS Readers

Copy the feed URL and add it to your favorite RSS reader:

- **Feedly**: Add → RSS Feed → Paste URL
- **Inoreader**: Add Subscription → RSS → Paste URL  
- **Apple News**: File → Add to Reading List → RSS Feed
- **Firefox**: Bookmarks → Subscribe to This Page
- **Thunderbird**: File → Subscribe → Paste URL

## Customization

### Change Update Frequency

Edit the cron schedule in `.github/workflows/rss-generator.yml`:

```yaml
schedule:
  # Every 6 hours
  - cron: '0 */6 * * *'
  
  # Every hour: '0 * * * *'
  # Every day at 9 AM: '0 9 * * *'
  # Every Monday at 9 AM: '0 9 * * 1'
```

### Modify Scraping Logic

Edit `scraper.py` to:

- Change the number of articles scraped
- Modify article extraction logic
- Add filtering or content processing
- Change RSS feed metadata

### Add More Sources

You can extend the scraper to include multiple sources by modifying the `scrape_articles()` method.

## Monitoring

### Check Workflow Status

1. Go to "Actions" tab in your repository
2. View recent workflow runs
3. Check logs for any errors

### Feed Validation

The workflow automatically validates the generated RSS feed:

- Checks if file exists and is not empty
- Validates XML structure
- Shows feed statistics in logs

## Troubleshooting

### Common Issues

**1. Workflow fails with "No articles found"**
- The website structure may have changed
- Check the scraper selectors in `scraper.py`
- Review the workflow logs for specific errors

**2. RSS feed not updating**
- Check if the workflow is running (Actions tab)
- Verify cron schedule syntax
- Ensure repository has proper permissions

**3. GitHub Pages not working**
- Verify Pages is enabled in repository settings
- Check if the deploy-pages job completed successfully
- Ensure the workflow has proper permissions

**4. Feed shows errors in RSS readers**
- Check XML validation in workflow logs
- Verify RSS feed structure
- Test feed URL directly in browser

### Debug Mode

To get more detailed logs, you can temporarily add debug statements to `scraper.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the workflow
5. Submit a pull request

## License

This project is open source. Feel free to modify and distribute as needed.

## Disclaimer

This scraper is for educational and personal use. Please respect the target website's robots.txt and terms of service. Consider adding delays between requests for large-scale scraping.
Allow: /feed.xml
Allow: /
Disallow: /.git
