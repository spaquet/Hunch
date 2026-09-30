# Hunch website

Static HTML, CSS, and JavaScript. No build step or package installation.

## Preview

From the repository root:

```sh
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000`.

## Publish

In GitHub → Settings → Pages, select **Deploy from a branch**, your publishing branch, and **/docs**. Commit the complete `docs` directory, including assets and `.nojekyll`. GitHub serves the HTML directly and keeps `index.md` available as the Markdown alternate.

Canonical and social URLs are configured for **https://spaquet.github.io/Hunch/**. If you add a custom domain, update the absolute URLs in `index.html`, `index.md`, `llms.txt`, `llms-full.txt`, `sitemap.xml`, and `robots.txt`, and add the GitHub Pages `CNAME` file.

The `robots.txt` file is ready for a domain-root deployment. On a GitHub Pages project URL, crawlers consult `https://spaquet.github.io/robots.txt`, which this repository cannot control. The page's robots meta tag, discoverable sitemap, structured data, and relative links work at the project URL. `llms.txt` covers the `/Hunch/` path and is explicitly linked from the page.

Search and agent discovery use semantic HTML, JSON-LD, canonical URLs, Open Graph, Twitter cards, a sitemap, a Markdown alternate, and the proposed llms.txt format. These aids do not guarantee indexing or inclusion in AI answers. GitHub Pages does not support custom HTTP response headers; metadata is provided in the HTML head.

Fonts are self-hosted: DM Sans, Instrument Serif, and IBM Plex Mono. Their licenses are included in `assets/fonts`. Existing Hunch brand assets are copied into `assets`, so the site does not depend on files outside the publishing directory.

## Browser check

With Playwright available, run the browser check against the preview server:

```sh
HUNCH_BASE_URL=http://localhost:8000 node scripts/check-site.cjs
```

The check covers assets, metadata, mobile overflow, theme behavior, routing examples, clipboard, keyboard access, and the JavaScript-free page. Pass `PLAYWRIGHT_MODULE` if Playwright is installed outside this repository.
