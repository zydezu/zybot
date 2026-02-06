import os
from dotenv import load_dotenv
import getkonataxkagami

# Load environment variables
load_dotenv()

def test_search_danbooru():
    """Test the Danbooru search functionality directly"""
    
    # Test cases
    test_cases = [
        {"query": "izumi_konata hiiragi_kagami", "rating": "s"},
        {"query": "lucky_star", "rating": None},
        {"query": "yaoi", "rating": "s"},
        {"query": "yuri", "rating": "s"},  # Should return no results
    ]
    
    print("Testing Danbooru search functionality...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: query='{test_case['query']}', rating='{test_case['rating']}'")
        
        # Get the image URL
        image_url = getkonataxkagami.get_image_url(
            os.getenv('DANBOORU_LOGIN'), 
            os.getenv('DANBOORU_API_KEY'), 
            test_case['query'], 
            test_case['rating']
        )
        
        if image_url:
            print(f"✓ Success: {image_url}")
        else:
            print("✗ No images found or error occurred")
        print("-" * 50)

if __name__ == "__main__":
    # Check if environment variables are set
    if not os.getenv('DANBOORU_LOGIN') or not os.getenv('DANBOORU_API_KEY'):
        print("Error: DANBOORU_LOGIN and DANBOORU_API_KEY must be set in your .env file")
    else:
        test_search_danbooru()