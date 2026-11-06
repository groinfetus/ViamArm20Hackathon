import io
from collections import deque
import numpy as np
import cv2
from PIL import Image
import config

_NEI = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def viam_to_bgr(img):
    """Convert whatever cam.get_image() returned into an OpenCV BGR array."""
    try:
        from viam.media.utils.pil import viam_to_pil_image
        pil = viam_to_pil_image(img)
    except Exception:
        pil = Image.open(io.BytesIO(img.data)) if hasattr(img, "data") else img
    return cv2.cvtColor(np.array(pil.convert("RGB")), cv2.COLOR_RGB2BGR)


def pix_to_arm(u, v, H):
    p = H @ np.array([u, v, 1.0])
    return float(p[0] / p[2]), float(p[1] / p[2])


# ---------------------------------------------------------------- tape color
def sample_tape_color(frame, pts, r=4):
    """Median LAB color of small patches around the clicked points (all on the tape)."""
    blur = cv2.GaussianBlur(frame, (5, 5), 0)
    lab = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB).astype(np.float32)
    patches = []
    for x, y in pts:
        x, y = int(x), int(y)
        patches.append(lab[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1].reshape(-1, 3))
    return np.median(np.vstack(patches), axis=0).tolist()


def tape_mask(frame, ref_lab):
    """Binary mask of pixels that match the taught tape color (within TAPE_TOL)."""
    blur = cv2.GaussianBlur(frame, (5, 5), 0)
    lab = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB).astype(np.float32)
    diff = lab - np.array(ref_lab, np.float32)
    diff[..., 0] *= config.LIGHTNESS_WEIGHT           # <1: tolerate shadows / uneven light
    dist = np.linalg.norm(diff, axis=2)
    mask = (dist < config.TAPE_TOL).astype(np.uint8) * 255

    m = config.MARGIN_PX                              # ignore image borders
    mask[:m, :] = 0; mask[-m:, :] = 0; mask[:, :m] = 0; mask[:, -m:] = 0

    k = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    keep = np.zeros_like(mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= config.MIN_AREA_PX:
            keep[labels == i] = 255
    return keep


# ------------------------------------------------------------ centerline path
def _main_path(points):
    """Longest path through a skeleton blob (ignores tiny spurs). points: set of (x,y)."""
    def bfs(start):
        dist, prev, q, last = {start: 0}, {}, deque([start]), start
        while q:
            p = q.popleft(); last = p
            for dx, dy in _NEI:
                n = (p[0] + dx, p[1] + dy)
                if n in points and n not in dist:
                    dist[n] = dist[p] + 1; prev[n] = p; q.append(n)
        return last, prev

    a, _ = bfs(next(iter(points)))
    b, prev = bfs(a)
    path = [b]
    while path[-1] != a:
        path.append(prev[path[-1]])
    return path[::-1]


def _extend_end(p_end, p_ref, amount):
    d = np.array(p_end, float) - np.array(p_ref, float)
    n = np.linalg.norm(d)
    if n < 1e-6 or amount <= 0:
        return tuple(map(float, p_end))
    return tuple(np.array(p_end, float) + d / n * amount)


def detect_tape_paths(frame, ref_lab):
    """Returns (paths, mask). paths = list of polylines [(x,y), ...] in pixels.
    Only keeps color-matching pieces that are long and narrow (tape-shaped)."""
    from skimage.morphology import skeletonize

    mask = tape_mask(frame, ref_lab)
    if mask.max() == 0:
        return [], mask

    skel = skeletonize(mask > 0).astype(np.uint8)
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    n, labels = cv2.connectedComponents(skel, connectivity=8)

    paths = []
    for i in range(1, n):
        ys, xs = np.nonzero(labels == i)
        if len(xs) < config.MIN_PATH_LEN_PX:
            continue
        pts = set(zip(xs.tolist(), ys.tolist()))
        path = _main_path(pts)
        if len(path) < config.MIN_PATH_LEN_PX:
            continue
        width = 2.0 * float(np.median([dt[y, x] for x, y in path]))
        if len(path) / max(width, 1.0) < config.MIN_ASPECT:
            continue   # blob / square / text, not a strip of tape

        poly = cv2.approxPolyDP(np.array(path, np.int32).reshape(-1, 1, 2),
                                config.SIMPLIFY_EPS_PX, False).reshape(-1, 2)
        poly = [tuple(map(float, p)) for p in poly]
        if len(poly) < 2:
            continue

        if config.EXTEND_ENDS:
            # skeleton ends sit ~half a tape-width short of the real tape end
            half = float(np.median([dt[y, x] for x, y in path]))
            poly[0] = _extend_end(poly[0], poly[1], half)
            poly[-1] = _extend_end(poly[-1], poly[-2], half)
        paths.append(poly)
    return paths, mask


# -------------------------------------------------------------- path utilities
def order_paths(paths, start):
    """Nearest-neighbor ordering; reverses a path if its far end is closer."""
    remaining, ordered, cur = list(paths), [], np.array(start, float)
    while remaining:
        best = None
        for i, p in enumerate(remaining):
            for cand in (p, p[::-1]):
                d = np.linalg.norm(cur - np.array(cand[0]))
                if best is None or d < best[0]:
                    best = (d, i, cand)
        _, i, cand = best
        remaining.pop(i)
        ordered.append(cand)
        cur = np.array(cand[-1], float)
    return ordered


def draw_overlay(frame, paths_px, mask=None):
    out = frame.copy()
    if mask is not None:
        tint = out.copy(); tint[mask > 0] = (0, 200, 255)
        out = cv2.addWeighted(out, 0.6, tint, 0.4, 0)
    for i, path in enumerate(paths_px):
        pts = np.array(path, np.int32).reshape(-1, 1, 2)
        cv2.polylines(out, [pts], False, (0, 255, 0), 2)
        for p in path[1:-1]:
            cv2.circle(out, (int(p[0]), int(p[1])), 3, (0, 255, 0), -1)
        a, b = path[0], path[-1]
        cv2.circle(out, (int(a[0]), int(a[1])), 7, (0, 0, 255), -1)   # start = red
        cv2.circle(out, (int(b[0]), int(b[1])), 7, (255, 0, 0), -1)   # end = blue
        cv2.putText(out, str(i + 1), (int(a[0]) + 8, int(a[1]) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return out
