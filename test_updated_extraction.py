#!/usr/bin/env python3
"""
Test script to verify the updated text extraction functionality
"""
import asyncio
import os
from playwright_automation import PlaywrightAutomation

async def test_updated_text_extraction():
    """Test the updated text extraction functionality"""
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
        
        print("Testing updated text extraction functionality...\n")
        
        # Test cases with selector_type parameter
        test_cases = [
            ("h1#main-title", "css", "CSS: Main title"),
            ("//h1[@id='main-title']", "xpath", "XPath: Main title"),
            ("p.description", "css", "CSS: Description paragraph"),
            ("//p[@class='description']", "xpath", "XPath: Description paragraph"),
            ("#text-input", "css", "CSS: Text input"),
            ("//input[@id='text-input']", "xpath", "XPath: Text input"),
        ]
        
        passed = 0
        failed = 0
        
        for selector, selector_type, description in test_cases:
            print(f"Testing: {description}")
            print(f"   Selector: {selector}")
            print(f"   Selector Type: {selector_type}")
            
            try:
                result = await automation.extract_element_text(selector, selector_type)
                print(f"   Result: '{result}'")
                
                if result != "":
                    print(f"   ✅ PASSED\n")
                    passed += 1
                else:
                    print(f"   ❌ FAILED - Empty result\n")
                    failed += 1
            except Exception as e:
                print(f"   ❌ ERROR: {e}\n")
                failed += 1
        
        print(f"Test Summary:")
        print(f"  Total: {len(test_cases)}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        
        if failed == 0:
            print(f"\n✅ All tests passed! The updated text extraction functionality is working correctly.")
        else:
            print(f"\n❌ {failed} tests failed! Please check the implementation.")
        
    except Exception as e:
        print(f"Test framework failed with error: {e}")
    finally:
        # Close the browser
        if automation.browser:
            await automation.close_browser()

if __name__ == "__main__":
    asyncio.run(test_updated_text_extraction())