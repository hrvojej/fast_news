import os
from summarizer_category_utilities import ensure_category_images_folder, crop_and_resize_image

# Input image path (source image)
input_image_path = r"C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\static\images\Stream_These_6_Movies_and_Show_1.jpg"

# Define output folder (for category images) and output image path
output_folder = r"C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories\images"
output_image_path = os.path.join(output_folder, "Stream_These_6_Movies_and_Show_1.jpg")

# Ensure the output folder exists
ensure_category_images_folder(output_folder)

# Process the image (crop from center and resize to 300x200)
result = crop_and_resize_image(input_image_path, output_image_path)

print("Image processing result:", result)
