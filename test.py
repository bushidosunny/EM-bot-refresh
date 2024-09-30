import base64

# Read the image file in binary mode and encode it
with open("video_screenshot.png", "rb") as img_file:
    encoded_string = base64.b64encode(img_file.read()).decode()

# Save the encoded string to a file
with open("video_screenshot_encoded", "w") as text_file:
    text_file.write(encoded_string)

