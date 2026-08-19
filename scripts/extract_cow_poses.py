"""Extract four cow poses from the generated checkerboard preview.

The checkerboard is near-white and connected to the image border. We flood-fill
only that connected background, preserving enclosed white areas on the cow.
"""

from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "cow-rough-poses-source.png"
POSES = (
    ("cow-walk.png", 20, 350),
    ("cow-point.png", 440, 810),
    ("cow-graze.png", 840, 1320),
    ("cow-run.png", 1320, 1774),
)


def is_background(pixel: tuple[int, int, int]) -> bool:
    high = max(pixel)
    low = min(pixel)
    return low >= 225 and high - low <= 12


def keep_largest_component(image: Image.Image) -> Image.Image:
    """Drop pieces of neighboring poses that overlap a crop boundary."""
    width, height = image.size
    alpha = image.getchannel("A")
    alpha_pixels = alpha.load()
    visited = bytearray(width * height)
    largest: list[tuple[int, int]] = []

    for start_y in range(height):
        for start_x in range(width):
            start_index = start_y * width + start_x
            if visited[start_index] or alpha_pixels[start_x, start_y] == 0:
                continue
            component: list[tuple[int, int]] = []
            queue = deque([(start_x, start_y)])
            visited[start_index] = 1
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    index = next_y * width + next_x
                    if visited[index] or alpha_pixels[next_x, next_y] == 0:
                        continue
                    visited[index] = 1
                    queue.append((next_x, next_y))
            if len(component) > len(largest):
                largest = component

    keep = set(largest)
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            if (x, y) not in keep:
                pixels[x, y] = (255, 255, 255, 0)
    return image


def main() -> None:
    image = Image.open(SOURCE).convert("RGBA")
    width, height = image.size
    pixels = image.load()
    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))

    while queue:
        x, y = queue.popleft()
        index = y * width + x
        if visited[index] or not is_background(pixels[x, y][:3]):
            continue
        visited[index] = 1
        pixels[x, y] = (255, 255, 255, 0)
        if x:
            queue.append((x - 1, y))
        if x + 1 < width:
            queue.append((x + 1, y))
        if y:
            queue.append((x, y - 1))
        if y + 1 < height:
            queue.append((x, y + 1))

    for name, left, right in POSES:
        pose = keep_largest_component(image.crop((left, 0, right, height)))
        alpha = pose.getchannel("A")
        bbox = alpha.getbbox()
        if bbox:
            pose = pose.crop(bbox)
        pose.save(ROOT / "assets" / name, optimize=True)


if __name__ == "__main__":
    main()
