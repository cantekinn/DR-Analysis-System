"""Lezyon segmentasyonu icin U-Net modelleri."""
import segmentation_models_pytorch as smp
import torch
import torch.nn as nn


def create_segmenter(encoder_name: str = 'efficientnet-b0',
                     in_channels: int = 3,
                     n_classes: int = 4,
                     pretrained: bool = True):
    """
    U-Net + EfficientNet encoder (ImageNet pretrained).
    n_classes = 4: [MA, HE, EX, SE] multi-label segmentasyon.
    """
    model = smp.Unet(
        encoder_name=encoder_name,
        encoder_weights='imagenet' if pretrained else None,
        in_channels=in_channels,
        classes=n_classes,
        activation=None,  # logit, sigmoid loss icinde olacak
    )
    return model


class BCEDiceLoss(nn.Module):
    """
    BCE + Dice kombinasyonu. Multi-label segmentasyon icin standart.
    Her kanal (lezyon tipi) icin bagimsiz hesaplanir.
    """
    def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5,
                 smooth: float = 1.0):
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss()
        self.bce_w = bce_weight
        self.dice_w = dice_weight
        self.smooth = smooth

    def dice_loss(self, logits, targets):
        probs = torch.sigmoid(logits)
        # her kanal icin ayri dice
        dims = (0, 2, 3)
        intersection = (probs * targets).sum(dims)
        union = probs.sum(dims) + targets.sum(dims)
        dice = (2.0 * intersection + self.smooth) / (union + self.smooth)
        return 1.0 - dice.mean()

    def forward(self, logits, targets):
        bce = self.bce(logits, targets)
        dice = self.dice_loss(logits, targets)
        return self.bce_w * bce + self.dice_w * dice
