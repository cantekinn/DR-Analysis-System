"""
Fundus goruntu on-isleme modulu.
Diyabetik Retinopati Analizi - EEM0458 Bahar 2026
Yazar: Can Tekin
"""
import cv2
import numpy as np
from PIL import Image


def crop_fundus(img: np.ndarray, tol: int = 7) -> np.ndarray:
    """
    Fundus goruntusunun siyah arka planini keser, sadece goz dairesini birakir.
    Ben Graham'in (Kaggle 2015 DR yarismasi kazanani) yaklasimi.

    Args:
        img: BGR veya RGB goruntu, np.uint8.
        tol: Siyah piksel esigi. Bu degerden buyuk pikseller "fundus" sayilir.

    Returns:
        Kirpilmis goruntu.
    """
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img

    mask = gray > tol
    if mask.sum() == 0:
        return img  # tamamen siyah ise dokunma

    coords = np.argwhere(mask)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1
    return img[y0:y1, x0:x1]


def apply_clahe(img: np.ndarray, clip_limit: float = 2.0,
                tile_grid_size: tuple = (8, 8)) -> np.ndarray:
    """
    LAB renk uzayinda L kanalina CLAHE uygulayarak kontrasti arttirir.
    Fundus goruntulerinde lezyonlari belirginlestirir.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l_eq = clahe.apply(l)
    lab_eq = cv2.merge([l_eq, a, b])
    return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2RGB)


def resize_square(img: np.ndarray, size: int = 384) -> np.ndarray:
    """
    Goruntuyu kare olacak sekilde sifir-padding ile yeniden boyutlandirir.
    Cember fundus'un en/boy oranini korur.
    """
    h, w = img.shape[:2]
    s = max(h, w)
    pad_top = (s - h) // 2
    pad_bot = s - h - pad_top
    pad_lef = (s - w) // 2
    pad_rig = s - w - pad_lef
    padded = cv2.copyMakeBorder(img, pad_top, pad_bot, pad_lef, pad_rig,
                                cv2.BORDER_CONSTANT, value=[0, 0, 0])
    return cv2.resize(padded, (size, size), interpolation=cv2.INTER_AREA)


def preprocess_pipeline(img_path: str, size: int = 384,
                        apply_clahe_flag: bool = True) -> np.ndarray:
    """
    Tum on-isleme adimlarini sirayla uygular:
    1. Goruntuyu yukle (RGB)
    2. Fundus crop (siyah arka plani kes)
    3. CLAHE (kontrast artirma)
    4. Square padding + resize (size x size)

    Args:
        img_path: Goruntu yolu.
        size: Cikti boyutu.
        apply_clahe_flag: CLAHE uygulansin mi?

    Returns:
        RGB np.uint8 goruntu, sekil (size, size, 3).
    """
    img = np.array(Image.open(img_path).convert('RGB'))
    img = crop_fundus(img, tol=7)
    if apply_clahe_flag:
        img = apply_clahe(img)
    img = resize_square(img, size=size)
    return img


def get_normalization_stats():
    """ImageNet mean/std (transfer learning icin standart)."""
    return {
        'mean': [0.485, 0.456, 0.406],
        'std':  [0.229, 0.224, 0.225],
    }
