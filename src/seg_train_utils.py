"""Segmentasyon egitim ve degerlendirme yardimcilari."""
import time
import numpy as np
import torch
from torch.amp import autocast, GradScaler


def dice_per_channel(probs, targets, threshold: float = 0.5,
                     smooth: float = 1.0):
    """
    Her kanal (lezyon) icin Dice skoru hesapla.
    probs: (B, C, H, W) sigmoid sonrasi 0-1
    targets: (B, C, H, W) 0/1
    Donus: (C,) numpy
    """
    preds = (probs > threshold).float()
    dims = (0, 2, 3)
    intersection = (preds * targets).sum(dims)
    union = preds.sum(dims) + targets.sum(dims)
    dice = (2.0 * intersection + smooth) / (union + smooth)
    return dice.cpu().numpy()


def iou_per_channel(probs, targets, threshold: float = 0.5,
                    smooth: float = 1.0):
    """Her kanal icin IoU."""
    preds = (probs > threshold).float()
    dims = (0, 2, 3)
    intersection = (preds * targets).sum(dims)
    union = preds.sum(dims) + targets.sum(dims) - intersection
    iou = (intersection + smooth) / (union + smooth)
    return iou.cpu().numpy()


@torch.no_grad()
def evaluate_seg(model, loader, device, criterion=None):
    """Segmentation modeli degerlendir."""
    model.eval()
    all_probs, all_targets, total_loss = [], [], 0.0
    n_batches = 0
    for imgs, masks in loader:
        imgs = imgs.to(device, non_blocking=True)
        masks = masks.to(device, non_blocking=True)
        with autocast(device_type='cuda', dtype=torch.float16):
            logits = model(imgs)
            if criterion is not None:
                total_loss += criterion(logits.float(), masks).item()
                n_batches += 1
        probs = torch.sigmoid(logits.float())
        all_probs.append(probs.cpu())
        all_targets.append(masks.cpu())
    
    probs = torch.cat(all_probs, dim=0)
    targets = torch.cat(all_targets, dim=0)
    
    dice = dice_per_channel(probs, targets)
    iou  = iou_per_channel(probs, targets)
    return {
        'avg_loss': total_loss / max(1, n_batches),
        'dice_per_class': dice,
        'iou_per_class': iou,
        'dice_mean': float(dice.mean()),
        'iou_mean': float(iou.mean()),
    }


def train_seg_epoch(model, loader, criterion, optimizer, scaler, device,
                    epoch_idx, total_epochs, scheduler=None):
    model.train()
    total_loss, n = 0.0, 0
    t0 = time.time()
    for imgs, masks in loader:
        imgs = imgs.to(device, non_blocking=True)
        masks = masks.to(device, non_blocking=True)
        
        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type='cuda', dtype=torch.float16):
            logits = model(imgs)
            loss = criterion(logits.float(), masks)
        
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        if scheduler is not None:
            scheduler.step()
        
        total_loss += loss.item() * imgs.size(0)
        n += imgs.size(0)
    
    avg_loss = total_loss / n
    elapsed = time.time() - t0
    print(f"  Epoch {epoch_idx+1}/{total_epochs} | train_loss={avg_loss:.4f} | "
          f"{elapsed:.1f}s")
    return avg_loss
