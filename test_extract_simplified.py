#!/usr/bin/env python3
"""
Comprehensive test script for the simplified extract_element_text method
"""
import asyncio
import os
from playwright_automation import PlaywrightAutomation

async def test_text_extraction_comprehensive():
    """Test the simplified text extraction functionality comprehensively"""
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
        
        print("Testing simplified text extraction functionality...\n")
        
        test_cases = [
            # (selector, expected_contains, description)
            ("h1#main-title", "Text Extraction Test Page", "CSS: Main title"),
            ("//h1[@id='main-title']", "Text Extraction Test Page", "XPath: Main title"),
            ("xpath=//h1[@id='main-title']", "Text Extraction Test Page", "XPath with prefix: Main title"),
            ("p.description", "This page is designed", "CSS: Description paragraph"),
            ("//p[@class='description']", "This page is designed", "XPath: Description paragraph"),
            ("#text-input", "This is a test value", "CSS: Text input"),
            ("//input[@id='text-input']", "This is a test value", "XPath: Text input"),
            ("#textarea-input", "This is a multiline test value", "CSS: Textarea"),
            ("//textarea[@id='textarea-input']", "This is a multiline test value", "XPath: Textarea"),
            ("h2.section-title", "Regular Text Elements", "CSS: First section title"),
            ("//h2[@class='section-title'][1]", "Regular Text Elements", "XPath: First section title"),
        ]
        
        passed = 0
        failed = 0
        
        for selector, expected_contains, description in test_cases:
            print(f"Testing: {description}")
            print(f"  Selector: {selector}")
            
            try:
                result = await automation.extract_element_text(selector)
                print(f"  Result: '{result}'")
                
                if expected_contains in result:
                    print(f"  ✅ PASSED\n")
                    passed += 1
                else:
                    print(f"  ❌ FAILED - Expected to contain: '{expected_contains}'\n")
                    failed += 1
            except Exception as e:
                print(f"  ❌ ERROR: {e}\n")
                failed += 1
        
        # Test with non-existent element
        print("Testing: Non-existent element")
        print(f"  Selector: #non-existent-element")
        result = await automation.extract_element_text("#non-existent-element")
        print(f"  Result: '{result}'")
        if result == "":
            print(f"  ✅ PASSED - Returned empty string for non-existent element\n")
            passed += 1
        else:
            print(f"  ❌ FAILED - Expected empty string\n")
            failed += 1
        
        print(f"Test Summary:")
        print(f"  Total: {len(test_cases) + 1}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        
        if failed == 0:
            print(f"\n✅ All tests passed successfully!")
        else:
            print(f"\n❌ {failed} tests failed!")
        
    except Exception as e:
        print(f"Test framework failed with error: {e}")
    finally:
        # Close the browser
        if automation.browser:
            await automation.browser.close()

if __name__ == "__main__":
    asyncio.run(test_text_extraction_comprehensive())