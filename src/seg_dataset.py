"""Lezyon segmentasyon dataseti (IDRiD)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import cv2
from PIL import Image
import torch
from torch.utils.data import Dataset
import albumentations as A
from albumentations.pytorch import ToTensorV2

sys.path.insert(0, str(Path(__file__).parent))
from preprocessing import crop_fundus, apply_clahe, get_normalization_stats

LESION_KEYS = ['MA', 'HE', 'EX', 'SE']
LESION_NAMES = ['Mikroanevrizma', 'Kanama', 'Sert Eksuda', 'Yumusak Eksuda']
LESION_COLORS_RGB = [(255, 0, 0), (255, 140, 0), (255, 255, 0), (0, 200, 255)]


def get_seg_train_transforms(size: int = 512):
    """Multi-task: ayni transform hem image hem mask uygulanir."""
    stats = get_normalization_stats()
    return A.Compose([
        A.Resize(size, size, interpolation=cv2.INTER_AREA),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.3),
        A.Rotate(limit=180, border_mode=0, value=0, mask_value=0, p=0.6),
        A.RandomBrightnessContrast(brightness_limit=0.15, contrast_limit=0.15, p=0.4),
        A.GaussianBlur(blur_limit=(3, 5), p=0.2),
        A.Normalize(mean=stats['mean'], std=stats['std']),
        ToTensorV2(),
    ])


def get_seg_val_transforms(size: int = 512):
    stats = get_normalization_stats()
    return A.Compose([
        A.Resize(size, size, interpolation=cv2.INTER_AREA),
        A.Normalize(mean=stats['mean'], std=stats['std']),
        ToTensorV2(),
    ])


class IDRiDSegDataset(Dataset):
    """
    Cikti:
        image: tensor (3, H, W)
        mask:  tensor (4, H, W)  [MA, HE, EX, SE], her piksel 0/1
    """
    def __init__(self, csv_path, transform=None, apply_preprocess: bool = True):
        self.df = pd.read_csv(csv_path).reset_index(drop=True)
        self.transform = transform
        self.apply_preprocess = apply_preprocess

    def __len__(self):
        return len(self.df)

    def _load_mask(self, path):
        """Maske yukle, 0/1 binary. Yoksa None doner."""
        if pd.isna(path) or path == '' or path is None:
            return None
        m = np.array(Image.open(path))
        if m.ndim == 3:
            m = m[..., 0]
        m = (m > 0).astype(np.uint8)
        return m

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img = np.array(Image.open(row['image_path']).convert('RGB'))
        
        # 4 lezyon maskelerini stack et
        masks = []
        for key in LESION_KEYS:
            m = self._load_mask(row.get(f'mask_{key}'))
            if m is None:
                m = np.zeros(img.shape[:2], dtype=np.uint8)
            masks.append(m)
        mask = np.stack(masks, axis=-1)  # H x W x 4
        
        # Preprocess (crop + CLAHE) - opsiyonel
        if self.apply_preprocess:
            # crop_fundus: hem image hem mask icin ayni kirpma
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            m_fundus = gray > 7
            if m_fundus.sum() > 0:
                coords = np.argwhere(m_fundus)
                y0, x0 = coords.min(axis=0)
                y1, x1 = coords.max(axis=0) + 1
                img = img[y0:y1, x0:x1]
                mask = mask[y0:y1, x0:x1]
            img = apply_clahe(img)
        
        # Albumentations augmentation
        if self.transform is not None:
            aug = self.transform(image=img, mask=mask)
            img = aug['image']
            mask = aug['mask']  # H x W x 4 tensor
            # Albumentations mask'i (H, W, 4) tensor olarak verir, (4, H, W)'ye permute et
            if mask.ndim == 3 and mask.shape[-1] == 4:
                mask = mask.permute(2, 0, 1)
            mask = mask.float()
        
        return img, mask
