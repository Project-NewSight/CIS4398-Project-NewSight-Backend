# app/services/google_vision_service.py

from google.cloud import vision
import io

def detect_colors(image_path):
    client = vision.ImageAnnotatorClient()

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.image_properties(image=image)
    props = response.image_properties_annotation

    colors = []
    for color_info in props.dominant_colors.colors:
        color = color_info.color
        colors.append({
            "r": color.red,
            "g": color.green,
            "b": color.blue,
            "score": color_info.score,
            "pixel_fraction": color_info.pixel_fraction
        })
    
    return colors


def is_multicolor(colors, threshold=0.15):
    strong_colors = [
        c for c in colors if c["pixel_fraction"] >= threshold
    ]
    if len(strong_colors) >= 3:
        return True
    
    rgb_values = [(c["r"], c["g"], c["b"]) for c in strong_colors]
    variance = sum((max(v) - min(v)) for v in zip(*rgb_values))
    
    return variance > 80


def pattern_likelihood(colors):
    fractions = [c["pixel_fraction"] for c in colors]
    small = len([f for f in fractions if f < 0.1])
    return small >= 4

def rgb_to_simple_color(r, g, b):
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    if h < 0.05 or h > 0.95:
        return "red"
    elif h < 0.10:
        return "orange"
    elif h < 0.18:
        return "yellow"
    elif h < 0.28:
        return "green"
    elif h < 0.40:
        return "cyan"
    elif h < 0.55:
        return "blue"
    elif h < 0.75:
        return "purple"
    return "pink"
