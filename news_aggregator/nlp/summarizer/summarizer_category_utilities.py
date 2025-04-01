# path: fast_news/news_aggregator/nlp/summarizer/summarizer_category_utilities.py
import os
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def ensure_category_images_folder(output_folder):
    """
    Ensure the specified folder exists; if not, create it.
    
    Args:
        output_folder (str): The path to the output folder.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logger.debug(f"Created folder: {output_folder}")

def crop_and_resize_image(input_image_path, output_image_path, target_width=400, target_height=300):

    """
    Open an image from input_image_path, crop it from the center to match the target aspect ratio,
    resize it to target_width x target_height, and save it to output_image_path.
    
    Args:
        input_image_path (str): Full path to the source image.
        output_image_path (str): Full path where the processed image will be saved.
        target_width (int): The desired width in pixels (default: 300).
        target_height (int): The desired height in pixels (default: 200).
        
    Returns:
        bool: True if the image was processed and saved successfully, False otherwise.
    """
    try:
        with Image.open(input_image_path) as img:
            width, height = img.size
            logger.debug(f"Original image size: {width}x{height}")
            
            # Calculate the target and current aspect ratios.
            target_ratio = target_width / target_height
            current_ratio = width / height

            if current_ratio > target_ratio:
                # Image is wider than target: crop the sides.
                new_width = int(height * target_ratio)
                new_height = height
                left = (width - new_width) // 2
                top = 0
            else:
                # Image is taller than target: crop the top and bottom.
                new_width = width
                new_height = int(width / target_ratio)
                left = 0
                top = (height - new_height) // 2
            
            right = left + new_width
            bottom = top + new_height

            # Crop the image from the center.
            img_cropped = img.crop((left, top, right, bottom))
            logger.debug(f"Cropped image size: {img_cropped.size[0]}x{img_cropped.size[1]}")

            # Resize the cropped image to the target dimensions.
            img_resized = img_cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Append the dimensions to the output file name
            base, ext = os.path.splitext(output_image_path)
            new_output_image_path = f"{base}_{target_width}x{target_height}{ext}"

            img_resized.save(new_output_image_path)
            logger.debug(f"Saved processed image to: {new_output_image_path}")
            return True

    except Exception as e:
        logger.error(f"Error processing image {input_image_path}: {e}", exc_info=True)
        return False
