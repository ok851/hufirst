#!/usr/bin/env python3
"""
Test script for the optimized extract_element_text method with XPath support
"""
import asyncio
import os
from playwright_automation import PlaywrightAutomation

async def test_text_extraction_xpath():
    """Test the optimized text extraction functionality with XPath support"""
    # Create an instance of PlaywrightAutomation
    automation = PlaywrightAutomation()
    
    try:
        # Start the browser
        await automation.start_browser(headless=True)
        
        # Get the path to the local HTML file
        html_file_path = os.path.abspath("test_extraction.html")
        file_url = f"file://{html_file_path}"
        
        # Navigate to the local HTML file
        await automation.page.goto(file_url)
        
        print("Testing text extraction with XPath support...\n")
        
        # Test 1: Extract text from regular elements using CSS selectors
        print("1. Testing regular text extraction with CSS selectors:")
        h1_text_css = await automation.extract_element_text("h1#main-title")
        print(f"   CSS: h1#main-title -> '{h1_text_css}'")
        
        # Test 2: Extract text from regular elements using XPath selectors
        print("\n2. Testing regular text extraction with XPath selectors:")
        h1_text_xpath = await automation.extract_element_text("//h1[@id='main-title']")
        print(f"   XPath: //h1[@id='main-title'] -> '{h1_text_xpath}'")
        assert h1_text_css == h1_text_xpath, f"CSS and XPath should return the same result for h1"
        
        description_text_xpath = await automation.extract_element_text("//p[@class='description']")
        print(f"   XPath: //p[@class='description'] -> '{description_text_xpath}'")
        assert description_text_xpath == "This page is designed to test the optimized text extraction functionality.", f"Description text mismatch"
        
        # Test 3: Extract text from input elements using XPath
        print("\n3. Testing input field extraction with XPath:")
        input_text_xpath = await automation.extract_element_text("//input[@id='text-input']")
        print(f"   XPath: //input[@id='text-input'] -> '{input_text_xpath}'")
        assert input_text_xpath == "This is a test value", f"Input value mismatch"
        
        textarea_value_xpath = await automation.extract_element_text("//textarea[@id='textarea-input']")
        print(f"   XPath: //textarea[@id='textarea-input'] -> '{textarea_value_xpath}'")
        assert "This is a multiline test value" in textarea_value_xpath, f"Textarea value mismatch"
        
        # Test 4: Extract text using XPath with different formats
        print("\n4. Testing different XPath formats:")
        # Test with 'xpath=' prefix
        h2_text_xpath_prefix = await automation.extract_element_text("xpath=//h2[@class='section-title']")
        print(f"   XPath with prefix: xpath=//h2[@class='section-title'] -> '{h2_text_xpath_prefix}'")
        
        print("\n✅ All tests passed successfully!")
        print(f"\n📝 XPath support is working correctly!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    finally:
        # Close the browser
        if automation.browser:
            await automation.browser.close()

if __name__ == "__main__":
    asyncio.run(test_text_extraction_xpath())