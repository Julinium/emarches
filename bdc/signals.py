from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver

from django.conf import settings
from pathlib import Path

from bdc.models import PurchaseOrder

@receiver(post_delete, sender=PurchaseOrder)
def bdc_post_delete(sender, instance, using, **kwargs):
    pdf_items_path = Path(settings.MEDIA_ROOT) / "bdc" / "items" / "pdf" / f"{ bdc.id }"
    delete_flat_dir(pdf_items_path)
    csv_items_path = Path(settings.MEDIA_ROOT) / "bdc" / "items" / "csv" / f"{ bdc.id }"
    delete_flat_dir(csv_items_path)

def delete_flat_dir(path: Path) -> bool:

    if not path.is_dir():
        return False

    # Check for subdirectories (including symlinks to dirs)
    for entry in path.iterdir():
        try:
            if entry.is_dir():
                return False
        except OSError:
            # broken symlink or permission issue → be safe
            return False

    # Remove files first (no recursion)
    for entry in path.iterdir():
        entry.unlink(missing_ok=True)

    path.rmdir()
    return True