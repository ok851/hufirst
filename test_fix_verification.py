#!/usr/bin/env python3
"""
Test script to verify the fix for text extraction with prefixes
"""
import asyncio
import os
from playwright_automation import PlaywrightAutomation

async def test_text_extraction_with_prefix():
    """Test text extraction with different selector prefixes"""
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
        
        print("Testing text extraction with prefixes...\n")
        
        # Test with the same selector in different formats
        selector = "//input[@id='text-input']"
        
        # Test 1: Without prefix
        result1 = await automation.extract_element_text(selector)
        print(f"1. Without prefix: {selector}")
        print(f"   Result: '{result1}'")
        
        # Test 2: With xpath= prefix (like app.py does)
        result2 = await automation.extract_element_text(f"xpath={selector}")
        print(f"2. With xpath= prefix: xpath={selector}")
        print(f"   Result: '{result2}'")
        
        # Test 3: With CSS selector for comparison
        css_selector = "#text-input"
        result3 = await automation.extract_element_text(css_selector)
        print(f"3. With CSS selector: {css_selector}")
        print(f"   Result: '{result3}'")
        
        # Verify all results are the same
        if result1 == result2 == result3 == "This is a test value":
            print("\n✅ All tests passed! Text extraction works correctly with all selector formats.")
        else:
            print("\n❌ Tests failed! Results don't match expected value.")
        
        # Test more cases from app.py
        print("\nTesting more cases from app.py...")
        
        test_cases = [
            ("//h1[@id='main-title']", "xpath=//h1[@id='main-title']", "Title extraction"),
            ("//p[@class='description']", "xpath=//p[@class='description']", "Description extraction"),
            ("//textarea[@id='textarea-input']", "xpath=//textarea[@id='textarea-input']", "Textarea extraction"),
        ]
        
        all_passed = True
        for xpath, prefixed_xpath, description in test_cases:
            result1 = await automation.extract_element_text(xpath)
            result2 = await automation.extract_element_text(prefixed_xpath)
            
            print(f"\n{description}:")
            print(f"   XPath: {xpath}")
            print(f"   Result: '{result1}'")
            print(f"   XPath with prefix: {prefixed_xpath}")
            print(f"   Result: '{result2}'")
            
            if result1 == result2 and result1 != "":
                print(f"   ✅ PASS")
            else:
                print(f"   ❌ FAIL")
                all_passed = False
        
        if all_passed:
            print("\n✅ All tests passed! The fix is working correctly.")
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
    finally:
        # Close the browser
        if automation.browser:
            await automation.close_browser()

if __name__ == "__main__":
    asyncio.run(test_text_extraction_with_prefix())