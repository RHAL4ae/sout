from PIL import Image
import numpy as np
from sklearn.cluster import KMeans


def extract_colors(image_path, n_colors=5):
    img = Image.open(image_path).convert('RGB')
    arr = np.array(img)
    pixels = arr.reshape(-1, 3)
    kmeans = KMeans(n_clusters=n_colors, random_state=0).fit(pixels)
    counts = np.bincount(kmeans.labels_)
    centers = kmeans.cluster_centers_.astype(int)
    # Sort centers by frequency
    idx = np.argsort(counts)[::-1]
    sorted_centers = centers[idx]
    # Convert to HEX
    hex_colors = ['#%02x%02x%02x' % tuple(c) for c in sorted_centers]
    return hex_colors


if __name__ == '__main__':
    import os
    logo_path = os.path.join(os.path.dirname(__file__), 'Logo.jpg')
    colors = extract_colors(logo_path, n_colors=5)
    print('Dominant colors:', ', '.join(colors))
