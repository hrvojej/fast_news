import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
import os

# Import the functions we want to test from summarizer_image.py
from summarizer_image import download_image, search_and_download_images, is_valid_image_url

class TestImageFunctions(unittest.TestCase):
    @patch('summarizer_image.ensure_images_directory', return_value=True)
    @patch('summarizer_image.requests.get')
    def test_download_image_valid(self, mock_get, mock_ensure):
        """
        Test that download_image returns a valid file path when given a proper image URL.
        """
        # Setup a fake response with image data
        fake_image_data = b"fake image data"
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.raw = BytesIO(fake_image_data)
        mock_get.return_value = fake_response

        url = "https://example.com/image.jpg"
        article_id = "test_article"
        base_name = "Test Article"
        counter = 1
        
        result = download_image(url, article_id, base_name=base_name, counter=counter)
        self.assertIsInstance(result, str)
        self.assertTrue("images" in result)
        # Clean up the file if it was actually written (optional in a real test environment)
        filepath = os.path.join(os.getcwd(), result)
        if os.path.exists(filepath):
            os.remove(filepath)

    @patch('summarizer_image.ensure_images_directory', return_value=True)
    @patch('summarizer_image.requests.get')
    def test_download_image_invalid_url(self, mock_get, mock_ensure):
        """
        Test that download_image returns None when an invalid URL is provided.
        """
        url = "invalid_url"
        article_id = "test_article"
        result = download_image(url, article_id)
        self.assertIsNone(result)
    
    @patch('summarizer_image.download_image')
    @patch('summarizer_image.requests.get')
    def test_search_and_download_images_no_results(self, mock_get, mock_download):
        """
        Test search_and_download_images when Wikimedia Commons returns no image results.
        """
        # Simulate an API response with no 'query' key
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {}
        mock_get.return_value = fake_response
        
        query = "nonexistent query"
        article_id = "test_article"
        base_name = "Test Article"
        num_images = 2
        
        results = search_and_download_images(query, article_id, base_name, num_images)
        self.assertEqual(results, [])
    
    @patch('summarizer_image.download_image')
    @patch('summarizer_image.requests.get')
    def test_search_and_download_images_with_results(self, mock_get, mock_download):
        """
        Test search_and_download_images with a valid Wikimedia Commons API response.
        """
        # Simulate Wikimedia Commons API response with one image page
        fake_api_response = {
            "query": {
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "title": "File:Test_Image.jpg",
                        "imageinfo": [{
                            "url": "https://example.com/test_image.jpg",
                            "extmetadata": {
                                "ObjectName": {"value": "Test Image Caption"}
                            }
                        }]
                    }
                }
            }
        }
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = fake_api_response
        mock_get.return_value = fake_response
        
        # Simulate download_image returning a fake local image path
        mock_download.return_value = "images/Test_Article_1.jpg"
        
        query = "test keywords"
        article_id = "test_article"
        base_name = "Test Article"
        num_images = 1
        
        results = search_and_download_images(query, article_id, base_name, num_images)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], "images/Test_Article_1.jpg")
        self.assertEqual(results[0]['caption'], "Test Image Caption")

if __name__ == '__main__':
    unittest.main()
