
from pathlib import Path
import cv2
import numpy as np

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)

def create_label(path, address):
    image = np.full((500, 800, 3), 255, dtype=np.uint8)

    cv2.putText(
        image, "DEVICE X100", (40, 70),
        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3
    )

    cv2.putText(
        image, "Manufacturer:", (40, 150),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2
    )

    cv2.putText(
        image, address, (40, 205),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2
    )

    cv2.putText(
        image, "DEMO LABEL - NOT FOR CLINICAL USE", (40, 400),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2
    )

    cv2.imwrite(str(path), image)


create_label(DATA / "old_label.png", "Old Demo Address")
create_label(DATA / "new_label.png", "Updated Demo Address")

old = cv2.imread(str(DATA / "old_label.png"))
new = cv2.imread(str(DATA / "new_label.png"))

gray_old = cv2.cvtColor(old, cv2.COLOR_BGR2GRAY)
gray_new = cv2.cvtColor(new, cv2.COLOR_BGR2GRAY)

difference = cv2.absdiff(gray_old, gray_new)
_, mask = cv2.threshold(difference, 40, 255, cv2.THRESH_BINARY)


# Find changed regions and combine nearby differences
highlighted = new.copy()

# Focus on the manufacturer address area
roi_old = gray_old[170:240, :]
roi_new = gray_new[170:240, :]

difference = cv2.absdiff(roi_old, roi_new)
_, mask = cv2.threshold(difference, 40, 255, cv2.THRESH_BINARY)

# Combine nearby changed pixels into one region
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 15))
merged = cv2.dilate(mask, kernel, iterations=2)

contours, _ = cv2.findContours(
    merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
)

for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)

    if w > 10 and h > 5:
        cv2.rectangle(
            highlighted,
            (x, y + 170),
            (x + w, y + h + 170),
            (0, 0, 255),
            2
        )

cv2.imwrite(str(DATA / "difference_mask.png"), mask)
cv2.imwrite(str(DATA / "highlighted_changes.png"), highlighted)

print("ARTWORK VALIDATION COMPLETE")
print("Combined change regions saved.")


print("ARTWORK VALIDATION COMPLETE")
print("Old and new label images regenerated.")
print("Highlighted differences saved.")

