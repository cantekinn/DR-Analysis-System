"""
DR siniflandirma icin PyTorch Dataset modulu.
Cache-aware: onceden islenmis PNG'leri direkt okur.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from preprocessing import preprocess_pipeline, get_normalization_stats

import albumentations as A
from albumentations.pytorch import ToTensorV2


CLASS_NAMES = ['No DR', 'Mild', 'Moderate', 'Severe', 'PDR']


def get_train_transforms(size: int = 384):
    stats = get_normalization_stats()
    return A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.3),
        A.Rotate(limit=180, border_mode=0, value=0, p=0.7),
        A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.1, rotate_limit=0,
                           border_mode=0, value=0, p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.15,
                                   contrast_limit=0.15, p=0.5),
        A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=15,
                             val_shift_limit=10, p=0.4),
        A.GaussianBlur(blur_limit=(3, 5), p=0.2),
        A.Normalize(mean=stats['mean'], std=stats['std']),
        ToTensorV2(),
    ])


def get_val_transforms(size: int = 384):
    stats = get_normalization_stats()
    return A.Compose([
        A.Normalize(mean=stats['mean'], std=stats['std']),
        ToTensorV2(),
    ])


class DRClassificationDataset(Dataset):
    """
    Cache-aware fundus dataset.
    use_cache=True ise: PNG direkt okunur (cache'li yol bekler).
    use_cache=False ise: tam pipeline (preprocess_pipeline cagrilir).
    """
    def __init__(self, csv_path, transform=None, size: int = 384,
                 use_cache: bool = True, apply_clahe: bool = True):
        self.df = pd.read_csv(csv_path).reset_index(drop=True)
        self.transform = transform
        self.size = size
        self.use_cache = use_cache
        self.apply_clahe = apply_clahe

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        if self.use_cache:
            img = np.array(Image.open(row['image_path']).convert('RGB'))
        else:
            img = preprocess_pipeline(row['image_path'], size=self.size,
                                      apply_clahe_flag=self.apply_clahe)
        if self.transform:
            img = self.transform(image=img)['image']
        label = int(row['label'])
        return img, label


def compute_class_weights(csv_path: str, num_classes: int = 5):
    df = pd.read_csv(csv_path)
    counts = df['label'].value_counts().sort_index().values
    N = counts.sum()
    K = num_classes
    weights = N / (K * counts)
    return torch.tensor(weights, dtype=torch.float32)


def get_weighted_sampler(csv_path: str):
    df = pd.read_csv(csv_path)
    labels = df['label'].values
    counts = np.bincount(labels)
    sample_weights = 1.0 / counts[labels]
    return WeightedRandomSampler(
        weights=torch.as_tensor(sample_weights, dtype=torch.double),
        num_samples=len(sample_weights),
        replacement=True,
    )
