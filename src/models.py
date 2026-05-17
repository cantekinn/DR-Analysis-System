"""DR Siniflandirma Modelleri (timm tabanli)."""
import timm
import torch
import torch.nn as nn


def create_model(name: str = 'efficientnet_b3', num_classes: int = 5,
                 pretrained: bool = True, drop_rate: float = 0.3):
    """
    timm'den pretrained model olustur.
    
    name secenekleri:
      - efficientnet_b0 : 5.3M parametre (sanity check icin)
      - efficientnet_b3 : 12M parametre (asil model)
      - convnext_tiny   : 28M parametre (alternatif)
    """
    model = timm.create_model(
        name, pretrained=pretrained, num_classes=num_classes,
        drop_rate=drop_rate,
    )
    return model


def count_params(model):
    """Egitilebilir parametre sayisi."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
