from PIL import Image
import io
from django.core.files.base import ContentFile

OUTPUT_WIDTH, OUTPUT_HEIGHT = 400, 400

def squarify_image(image_file, filename='', out_width=OUTPUT_WIDTH, out_height=OUTPUT_HEIGHT):
    """
    Process uploaded image: make it square and optimize size.
    Returns a ContentFile with the processed image.
    """
    # Open the image
    image = Image.open(image_file)
    
    # Convert to RGB if necessary (handles PNG with transparency)
    if image.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    
    # Get dimensions
    width, height = image.size
    new_size = min(width, height)
    
    # Calculate cropping coordinates
    left = (width - new_size) // 2
    top = (height - new_size) // 2
    right = left + new_size
    bottom = top + new_size    

    # Crop to square
    image = image.crop((left, top, right, bottom))
    
    # Resize to a reasonable size (e.g., 300x300) for profile pictures
    image = image.resize((out_width, out_height), Image.Resampling.LANCZOS)
    
    # Optimize image
    output = io.BytesIO()
    image.save(
        output,
        format='JPEG',
        quality=80,  # Balance between quality and file size
        optimize=True,
        progressive=True
    )
    
    # Create a new ContentFile for Django
    output.seek(0)
    new_name = filename if filename else image_file.name.split('.')[0]
    return ContentFile(output.read(), name=f"{new_name}.jpg")