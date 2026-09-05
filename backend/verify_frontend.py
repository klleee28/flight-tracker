import asyncio
from playwright.async_api import async_playwright
import os

async def capture_dashboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        
        print("Navigating to http://localhost:3000 ...")
        await page.goto("http://localhost:3000", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Take screenshot of dashboard
        screenshot_path = os.path.join(os.path.dirname(__file__), "dashboard_screenshot.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Dashboard screenshot captured: {screenshot_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_dashboard())
