import torch
from pytorch_lightning import LightningDataModule
from torch.utils.data import DataLoader

from pl_bolts.utils import _TORCHVISION_AVAILABLE
from pl_bolts.utils.warnings import warn_missing_pkg

if _TORCHVISION_AVAILABLE:
    import torchvision.transforms as T
    from torchvision.datasets import VOCDetection
else:
    warn_missing_pkg('torchvision')  # pragma: no-cover


class Compose(object):
    """
    Like `torchvision.transforms.compose` but works for (image, target)
    """

    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, image, target):
        for t in self.transforms:
            image, target = t(image, target)
        return image, target


def _collate_fn(batch):
    return tuple(zip(*batch))


CLASSES = (
    "__background__ ",
    "aeroplane",
    "bicycle",
    "bird",
    "boat",
    "bottle",
    "bus",
    "car",
    "cat",
    "chair",
    "cow",
    "diningtable",
    "dog",
    "horse",
    "motorbike",
    "person",
    "pottedplant",
    "sheep",
    "sofa",
    "train",
    "tvmonitor",
)


def _prepare_voc_instance(image, target):
    """
    Prepares VOC dataset into appropriate target for fasterrcnn

    https://github.com/pytorch/vision/issues/1097#issuecomment-508917489
    """
    anno = target["annotation"]
    boxes = []
    classes = []
    area = []
    iscrowd = []
    objects = anno["object"]
    if not isinstance(objects, list):
        objects = [objects]
    for obj in objects:
        bbox = obj["bndbox"]
        bbox = [int(bbox[n]) - 1 for n in ["xmin", "ymin", "xmax", "ymax"]]
        boxes.append(bbox)
        classes.append(CLASSES.index(obj["name"]))
        iscrowd.append(int(obj["difficult"]))
        area.append((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))

    boxes = torch.as_tensor(boxes, dtype=torch.float32)
    classes = torch.as_tensor(classes)
    area = torch.as_tensor(area)
    iscrowd = torch.as_tensor(iscrowd)

    image_id = anno["filename"][5:-4]
    image_id = torch.as_tensor([int(image_id)])

    target = {}
    target["boxes"] = boxes
    target["labels"] = classes
    target["image_id"] = image_id

    # for conversion to coco api
    target["area"] = area
    target["iscrowd"] = iscrowd

    return image, target


class VOCDetectionDataModule(LightningDataModule):
    """
    TODO(teddykoker) docstring
    """

    name = "vocdetection"

    def __init__(
        self,
        data_dir: str,
        year: str = "2012",
        num_workers: int = 16,
        normalize: bool = False,
        shuffle: bool = False,
        pin_memory: bool = False,
        drop_last: bool = False,
        *args,
        **kwargs,
    ):
        if not _TORCHVISION_AVAILABLE:
            raise ModuleNotFoundError(  # pragma: no-cover
                'You want to use VOC dataset loaded from `torchvision` which is not installed yet.'
            )

        super().__init__(*args, **kwargs)

        self.year = year
        self.data_dir = data_dir
        self.num_workers = num_workers
        self.normalize = normalize
        self.shuffle = shuffle
        self.pin_memory = pin_memory
        self.drop_last = drop_last

    @property
    def num_classes(self):
        """
        Return:
            21
        """
        return 21

    def prepare_data(self):
        """
        Saves VOCDetection files to data_dir
        """
        VOCDetection(self.data_dir, year=self.year, image_set="train", download=True)
        VOCDetection(self.data_dir, year=self.year, image_set="val", download=True)

    def train_dataloader(self, batch_size=1, transforms=None):
        """
        VOCDetection train set uses the `train` subset

        Args:
            batch_size: size of batch
            transforms: custom transforms
        """
        t = [_prepare_voc_instance]
        transforms = transforms or self.train_transforms or self._default_transforms()
        if transforms is not None:
            t.append(transforms)
        transforms = Compose(t)

        dataset = VOCDetection(
            self.data_dir, year=self.year, image_set="train", transforms=transforms
        )
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=self.shuffle,
            num_workers=self.num_workers,
            drop_last=self.drop_last,
            pin_memory=self.pin_memory,
            collate_fn=_collate_fn,
        )
        return loader

    def val_dataloader(self, batch_size=1, transforms=None):
        """
        VOCDetection val set uses the `val` subset

        Args:
            batch_size: size of batch
            transforms: custom transforms
        """
        t = [_prepare_voc_instance]
        transforms = transforms or self.val_transforms or self._default_transforms()
        if transforms is not None:
            t.append(transforms)
        transforms = Compose(t)
        dataset = VOCDetection(
            self.data_dir, year=self.year, image_set="val", transforms=transforms
        )
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            drop_last=self.drop_last,
            pin_memory=self.pin_memory,
            collate_fn=_collate_fn,
        )
        return loader

    def _default_transforms(self):
        if self.normalize:
            return (
                lambda image, target: (
                    T.Compose(
                        [
                            T.ToTensor(),
                            T.Normalize(
                                mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                            ),
                        ]
                    )(image),
                    target,
                ),
            )
        return lambda image, target: (T.ToTensor()(image), target)
