import re
from pathlib import Path


def test_homepage_images_exist():
    """Validate that all images referenced in the homepage HTML exist on disk."""
    index_path = Path("static/index.html")
    content = index_path.read_text(encoding='utf-8')

    # Find all img src paths under /static/images/
    matches = re.findall(r'src="/static/images/([^"]+)"', content)

    for img in matches:
        img_path = Path("static/images") / img
        assert img_path.exists(), f"Referenced image {img} does not exist"
