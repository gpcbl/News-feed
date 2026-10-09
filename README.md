# News Feed

Combines several news RSS feeds into one feed, updated automatically every 2 hours by GitHub Actions.

**Output** (in the `docs/` folder):
- `feed.xml`: one combined RSS feed you can add to any reader (Feedly, Inoreader, Reeder)
- `news.json`: the same stories as JSON, for a web app to read

## Setup (about 10 minutes)

1. **Create a repository.** On GitHub, click **New repository**, name it `news-feed`, set it to Public (needed for free GitHub Pages), and create it.
2. **Upload the files.** Click **Add file → Upload files** and drag in everything from this folder, keeping the `.github/workflows/` folder structure. If the web uploader drops the hidden `.github` folder, create the file manually: **Add file → Create new file**, type `.github/workflows/update-feed.yml` as the name, and paste the contents.
3. **Allow the workflow to save changes.** Go to **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**, and save.
4. **Run it once.** Go to the **Actions** tab, pick **Update news feed**, and click **Run workflow**. After about a minute, `docs/feed.xml` and `docs/news.json` appear in the repo.
5. **Publish it.** Go to **Settings → Pages**, set Source to **Deploy from a branch**, branch `main`, folder `/docs`, and save. Your feed will be live at:
   `https://YOUR-USERNAME.github.io/news-feed/feed.xml`
6. Update the `link` in `feeds.json` to that address.

## Adding or removing sources

Edit `feeds.json`. Each source needs a name, a category, and the feed URL:

```json
{"name": "CBC Canada", "category": "Canadian Economy", "url": "https://www.cbc.ca/webfeed/rss/rss-canada"}
```

To find a site's feed, look for an RSS icon or try adding `/feed` or `/rss` to its address. For sites without a feed, tools like RSS.app can generate one.

## Notes

- If a source fails, the run continues and the log under the **Actions** tab lists which feeds were skipped. Some news sites block automated requests; remove or replace those.
- The Bank of Canada feed was confirmed working on October 6, 2026. The others are each publisher's published feed address, but publishers change these from time to time, so check the first run's log.
- To change how often it runs, edit the `cron` line in `.github/workflows/update-feed.yml`. `0 */2 * * *` means every 2 hours; `0 12 * * *` means daily at 12:00 UTC (5 a.m. in Vancouver during daylight time).
- Scheduled workflows pause after 60 days without repository activity. The feed commits keep it active, but if it stops, re-enable it from the Actions tab.
- Feeds contain headlines, short summaries and links back to the original articles. Don't modify the script to copy full articles into a public feed.

## Run it locally

```bash
pip install -r requirements.txt
python fetch_feeds.py
```
