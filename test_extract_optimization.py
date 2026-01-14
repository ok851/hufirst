#!/usr/bin/env python3
"""
Test script for the optimized extract_element_text method
"""
import asyncio
from playwright_automation import PlaywrightAutomation

async def test_text_extraction():
    """Test the optimized text extraction functionality"""
    # Create an instance of PlaywrightAutomation
    automation = PlaywrightAutomation()
    
    try:
        # Start the browser
        await automation.start_browser(headless=False)
        
        # Test 1: Basic text extraction from a simple webpage
        print("Test 1: Basic text extraction from a simple webpage")
        await automation.page.goto("https://example.com")
        
        # Extract text from the h1 element
        h1_text = await automation.extract_element_text("h1")
        print(f"h1 text: {h1_text}")
        assert "Example Domain" in h1_text, f"Expected 'Example Domain' in h1 text, got '{h1_text}'"
        
        # Extract text from the paragraph
        p_text = await automation.extract_element_text("p")
        print(f"p text: {p_text}")
        assert len(p_text) > 0, "Expected non-empty paragraph text"
        
        # Test 2: Input field extraction
        print("\nTest 2: Input field extraction")
        await automation.page.goto("https://www.w3schools.com/html/html_forms.asp")
        
        # Extract value from an input field (first name)
        input_text = await automation.extract_element_text("input[name='firstname']")
        print(f"Input field value: '{input_text}'")
        
        # Test 3: Test with iframe
        print("\nTest 3: Iframe text extraction")
        await automation.page.goto("https://www.w3schools.com/html/html_iframe.asp")
        
        # Try to extract text from inside an iframe
        iframe_text = await automation.extract_element_text("h1")
        print(f"Iframe text: '{iframe_text}'")
        
        print("\nAll tests passed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
    finally:
        # Close the browser
        if automation.browser:
            await automation.browser.close()

if __name__ == "__main__":
    asyncio.run(test_text_extraction())