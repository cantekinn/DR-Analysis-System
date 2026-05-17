"""Egitim ve validasyon yardimcilari."""
import time
import torch
import torch.nn as nn
from torch.amp import autocast, GradScaler
from sklearn.metrics import (accuracy_score, f1_score, cohen_kappa_score,
                             confusion_matrix, classification_report)
import numpy as np


@torch.no_grad()
def evaluate(model, loader, device, criterion=None):
    """Validation/test seti uzerinde degerlendir."""
    model.eval()
    all_preds, all_labels, total_loss = [], [], 0.0
    n_batches = 0
    for imgs, lbls in loader:
        imgs = imgs.to(device, non_blocking=True)
        lbls = lbls.to(device, non_blocking=True)
        with autocast(device_type='cuda', dtype=torch.float16):
            logits = model(imgs)
            if criterion is not None:
                total_loss += criterion(logits, lbls).item()
                n_batches += 1
        preds = logits.argmax(dim=1)
        all_preds.append(preds.cpu().numpy())
        all_labels.append(lbls.cpu().numpy())
    
    preds = np.concatenate(all_preds)
    labels = np.concatenate(all_labels)
    
    metrics = {
        'accuracy': accuracy_score(labels, preds),
        'f1_macro': f1_score(labels, preds, average='macro', zero_division=0),
        'kappa_quadratic': cohen_kappa_score(labels, preds, weights='quadratic'),
        'avg_loss': total_loss / n_batches if n_batches > 0 else 0.0,
        'preds': preds,
        'labels': labels,
    }
    return metrics


def train_one_epoch(model, loader, criterion, optimizer, scaler, device,
                    epoch_idx: int, total_epochs: int, scheduler=None):
    """Tek bir epoch egitimi (AMP mixed precision)."""
    model.train()
    total_loss, total_correct, total_samples = 0.0, 0, 0
    t0 = time.time()
    
    for i, (imgs, lbls) in enumerate(loader):
        imgs = imgs.to(device, non_blocking=True)
        lbls = lbls.to(device, non_blocking=True)
        
        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type='cuda', dtype=torch.float16):
            logits = model(imgs)
            loss = criterion(logits, lbls)
        
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        
        if scheduler is not None:
            scheduler.step()
        
        preds = logits.argmax(dim=1)
        total_loss += loss.item() * lbls.size(0)
        total_correct += (preds == lbls).sum().item()
        total_samples += lbls.size(0)
    
    avg_loss = total_loss / total_samples
    avg_acc = total_correct / total_samples
    elapsed = time.time() - t0
    
    print(f"  Epoch {epoch_idx+1}/{total_epochs} | "
          f"train_loss={avg_loss:.4f} | train_acc={avg_acc:.4f} | "
          f"{elapsed:.1f}s")
    return avg_loss, avg_acc
