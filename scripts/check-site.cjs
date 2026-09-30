// Run against the local preview server; no website dependency on Playwright.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const base = process.env.HUNCH_BASE_URL || 'http://localhost:8000';

(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}, colorScheme: 'light', permissions: ['clipboard-read', 'clipboard-write']});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
    await page.goto(base, {waitUntil: 'networkidle'});
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('h1').count(), 1);
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'light');
    assert.equal(await page.locator('.orbit textPath').count(), 6);
    const orbit = page.locator('.orbit-one svg');
    const initialRotation = await orbit.evaluate(el => getComputedStyle(el).transform);
    await page.waitForFunction(initial => getComputedStyle(document.querySelector('.orbit-one svg')).transform !== initial, initialRotation);
    await page.locator('.orbit-toggle').click();
    assert.equal(await page.locator('#pause-orbits').isChecked(), true);
    for (const ring of await page.locator('.orbit svg').all()) {
      assert.equal(await ring.evaluate(el => getComputedStyle(el).animationPlayState), 'paused');
    }
    await page.locator('#pause-orbits').focus();
    await page.keyboard.press('Space');
    assert.equal(await page.locator('#pause-orbits').isChecked(), false);
    assert.equal(await orbit.evaluate(el => getComputedStyle(el).animationPlayState), 'running');
    const metadata = await page.locator('script[type="application/ld+json"]').textContent();
    assert.equal(JSON.parse(metadata)['@graph'].length, 3);
    for (const selector of ['link[rel=canonical]', 'meta[property="og:image"]', 'meta[name="twitter:card"]', 'link[rel=describedby]', 'link[rel=alternate]']) {
      assert.equal(await page.locator(selector).count(), 1, selector);
    }
    for (const [scenario, risk, route] of [['write', 'reversibleWrite', 'Review the diff.'], ['delete', 'destructive', 'Ask a human.'], ['secret', 'sensitive', 'Stop and review.'], ['read', 'readOnly', 'Continue locally.']]) {
      await page.locator(`[data-scenario=${scenario}]`).click();
      assert.equal(await page.locator('#demo-risk').textContent(), risk);
      assert.equal(await page.locator('#demo-route').textContent(), route);
      assert.equal(await page.locator('[data-scenario][aria-pressed=true]').count(), 1);
    }
    await page.locator('#theme-toggle').click(); // system → light
    await page.locator('#theme-toggle').click(); // light → dark
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.reload({waitUntil: 'networkidle'});
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.screenshot({path: '/private/tmp/hunch-site-dark.png', fullPage: true, animations: 'disabled'});
    await page.locator('#theme-toggle').click(); // dark → system
    await page.emulateMedia({colorScheme: 'light'});
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'light');
    await page.screenshot({path: '/private/tmp/hunch-site-light.png', fullPage: true, animations: 'disabled'});
    await page.locator('#copy-command').click();
    assert.match(await page.evaluate(() => navigator.clipboard.readText()), /swift run hunch/);
    await page.locator('details').first().locator('summary').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('details').first().getAttribute('open'), '');
    for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({width, height: 900});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Overflow at ${width}px`);
    }
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: '/private/tmp/hunch-site-mobile.png', fullPage: true, animations: 'disabled'});
    await page.emulateMedia({reducedMotion: 'reduce', colorScheme: 'dark'});
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'dark');
    assert.equal(await page.locator('.terminal-cursor').evaluate(el => getComputedStyle(el).animationName), 'none');
    for (const ring of await page.locator('.orbit svg').all()) {
      assert.equal(await ring.evaluate(el => getComputedStyle(el).animationName), 'none');
    }
    assert.equal(await page.locator('.orbit-toggle').isVisible(), false);
    for (const path of ['index.md', 'llms.txt', 'llms-full.txt', 'sitemap.xml', 'robots.txt', 'assets/hunch-social.png', 'assets/favicon.svg']) {
      assert.equal((await context.request.get(`${base}/${path}`)).status(), 200, path);
    }
    assert.deepEqual(errors, []);
    await context.close();
    const noJs = await browser.newContext({javaScriptEnabled: false, colorScheme: 'dark'});
    const staticPage = await noJs.newPage();
    await staticPage.goto(base);
    assert.equal(await staticPage.locator('h1').count(), 1);
    assert.equal(await staticPage.locator('#theme-toggle').isVisible(), false);
    assert.equal(await staticPage.locator('noscript').isVisible(), true);
    assert.equal(await staticPage.locator('body').evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(19, 29, 24)');
    await staticPage.locator('.orbit-toggle').click();
    assert.equal(await staticPage.locator('.orbit-one svg').evaluate(el => getComputedStyle(el).animationPlayState), 'paused');
    await noJs.close();
    console.log('Passed: orbit animation/pause, desktop/mobile layout, themes, routing, clipboard, keyboard, reduced motion, metadata, assets, and no-JS fallback.');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
