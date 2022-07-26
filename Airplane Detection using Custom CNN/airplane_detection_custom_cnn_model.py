# -*- coding: utf-8 -*-
"""Airplane Detection Custom CNN model.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1chUkX2X8JwBswg0Bq0VCoGjlIWlkyVTo

## Install dependencies and initialization
"""

# install dependencies: 
!pip install pyyaml==5.1 pycocotools>=2.0.1
# !pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu101/torch1.6/index.html
!pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu111/torch1.9/index.html

!pwd # shows current directory
!ls  # shows all files in this directory
!nvidia-smi # shows the specs and the current status of the allocated GPU

# import some common libraries
from google.colab.patches import cv2_imshow
from sklearn.metrics import jaccard_score
from PIL import Image, ImageDraw
from tqdm.notebook import tqdm
import pandas as pd
import numpy as np
import datetime
import random
import json
import cv2
import csv
import os

# import some common pytorch utilities
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
from torch.autograd import Variable
import torch.nn.functional as F
import torch.nn as nn
import torch

# import some common detectron2 utilities
import detectron2
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.structures import BoxMode
from detectron2.engine import DefaultTrainer
from detectron2.engine import DefaultPredictor
from detectron2.utils.logger import setup_logger
from detectron2.utils.visualizer import ColorMode
from detectron2.utils.visualizer import Visualizer
from detectron2.data import build_detection_test_loader
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
setup_logger()

# Make sure that GPU is available for your notebook. 
# Otherwise, you need to update the settungs in Runtime -> Change runtime type -> Hardware accelerator
torch.cuda.is_available()

# You need to mount your google drive in order to load the data:
from google.colab import drive
drive.mount('/content/drive', True)
# Put all the corresponding data files in a data folder and put the data folder in a same directory with this notebook.
# Also create an output directory for your files such as the trained models and the output images.

"""## Part 1: Object Detection

### Data Loader
"""

'''
# This function returns a list of data samples in which each sample is a dictionary. 
# Make sure to select the correct bbox_mode for the data
# For the test data, you only have access to the images, therefore, the annotations should be empty.
# Other values could be obtained from the image files.
'''

def get_detection_data(set_name): 
  test_dirs = '{}/data/test'.format(BASE_DIR)

  if set_name == 'test':

    dataset = []
    for i in os.listdir(test_dirs):
      test = {}
      filename = os.path.join(test_dirs, i)
      width, height = Image.open(filename).size
      test["file_name"] = filename
      test["width"] = width
      test["height"] = height
      test["annotations"] = []
      dataset.append(test)

    return dataset

  else:
    data_dirs = '{}/data'.format(BASE_DIR)
    train_dirs = '{}/data/train'.format(BASE_DIR)
    
    dataset = []
    objects = []
    file = os.path.join(data_dirs, "train.json")
    with open(file) as f:
      imgs_anns = json.load(f)

    dataset_dicts = []
    currfilename = ''
    for idx, v in enumerate(tqdm(imgs_anns)):

      prevfilename = currfilename      
      currfilename = os.path.join(train_dirs, v["file_name"])

      record = {}

      if currfilename != prevfilename:
        objects = []
        img = Image.open(currfilename)
        width, height =  img.size
        record["file_name"] = currfilename
        record["image_id"] = idx
        record["height"] = height
        record["width"] = width   
        dataset.append(record)    


      obj =  {
          "bbox": v["bbox"],
          "bbox_mode": BoxMode.XYWH_ABS,      
          "segmentation": v["segmentation"],
          "category_id": 0,
      }
      objects.append(obj)
      record["annotations"] = objects
      

    
      
        
    return dataset

'''
# Remember to add your dataset to DatasetCatalog and MetadataCatalog
# Consdier "data_detection_train" and "data_detection_test" for registration
# You can also add an optional "data_detection_val" for your validation by spliting the training data
'''
DatasetCatalog.clear()
data_train = get_detection_data('train')
data_test = get_detection_data('test')

DatasetCatalog.register("airplane_train", lambda: data_train)
DatasetCatalog.register("airplane_test", lambda: data_test)

#for d in ["train", "val", "test"]:
for d in ["train", "test"]:
  MetadataCatalog.get("airplane_" + d).set(thing_classes=["plane"])

plane_train_metadata = MetadataCatalog.get("airplane_train")
plane_test_metadata = MetadataCatalog.get("airplane_test")

'''
# Visualize some samples using Visualizer to make sure that the function works correctly
'''

i = 0
for d in random.sample(data_train, 3):
  
    img = cv2.imread(d["file_name"])
    
    visualizer = Visualizer(img[:, :, ::-1], metadata=plane_train_metadata, scale=0.5)
    out = visualizer.draw_dataset_dict(d)
    cv2_imshow(out.get_image()[:, :, ::-1])

"""### Set Configs"""

'''
# Set the configs for the detection part in here.
'''

cfg = get_cfg()
cfg.OUTPUT_DIR = "{}/output/".format(BASE_DIR)

cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_101_FPN_3x.yaml"))
cfg.DATASETS.TRAIN = ("airplane_train")
cfg.DATASETS.TEST = ()

cfg.DATALOADER.NUM_WORKERS = 2
cfg.SOLVER.BASE_LR = 0.00025
cfg.SOLVER.IMS_PER_BATCH = 2
cfg.SOLVER.MAX_ITER = 700
cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 512   
cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1

"""### Training"""

'''
# Create a DefaultTrainer using the above config and train the model
'''
os.makedirs(cfg.OUTPUT_DIR, exist_ok= True)
trainer = DefaultTrainer(cfg)

#trainer.train()

"""### Evaluation and Visualization"""

'''
# After training the model, we need to update cfg.MODEL.WEIGHTS
# Define a DefaultPredictor
'''

cfg.MODEL.WEIGHTS = os.path.join("/content/drive/My Drive/SFU_CMPT_CV_Lab3/output", "model_final.pth")
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.4
predictor = DefaultPredictor(cfg)

'''
# Visualize the output for 3 random test samples
'''

print(data_train[0])
print(data_test[0])

for i in random.sample(data_test, 3):
  image = cv2.imread(i['file_name'])
  output = predictor(image)

  v = Visualizer(image[:, :, ::-1],
                 metadata = plane_test_metadata,
                 scale = 0.5)
  out = v.draw_instance_predictions(output['instances'].to('cpu'))
  cv2_imshow(out.get_image()[:, :, ::-1])

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard
# %tensorboard --logdir output

'''
# Using COCOEvaluator and build_detection_train_loader
# You can save the output predictions using inference_on_dataset
'''

from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.data import build_detection_test_loader

evaluator = COCOEvaluator("airplane_train", cfg, False, output_dir= "./output/")
val_loader = build_detection_test_loader(cfg, "airplane_train")
print(inference_on_dataset(trainer.model, val_loader, evaluator))

"""## Part 2: Semantic Segmentation

### Data Loader
"""

'''
# A function that returns the cropped image and corresponding mask regarding the target bounding box
# idx is the index of the target bbox in the data
# high-resolution image could be passed or could be load from data['file_name']
# You can use the mask attribute of detectron2.utils.visualizer.GenericMask 
#     to convert the segmentation annotations to binary masks
'''


def get_instance_sample(data, idx, image):

  annotations = data['annotations'][idx]
  bbox = annotations['bbox']
  x,y,w,h = bbox
  x = int(x)
  y = int(y)
  w = int(w)
  h = int(h)     
  img = image[y:y+h, x:x+w]
    
  mask = detectron2.utils.visualizer.GenericMask(data['annotations'][idx]['segmentation'], 
                                                    data['height'], data['width']).mask
  mask = mask[y:y+h, x:x+w]
  obj_img = cv2.resize(img, (128,128), interpolation = cv2.INTER_AREA) 
  obj_mask = cv2.resize(mask, (128,128), interpolation = cv2.INTER_AREA)
      
   
  return obj_img, obj_mask

'''
# A data loader for segmentation training
#  __getitem__() 
# Also added data augmentation or normalization in here
'''

class PlaneDataset(Dataset):
  def __init__(self, set_name, data_list):
      self.transforms = transforms.Compose([
          transforms.ToTensor(), # Converting the image to tensor and change the image format (Channels-Last => Channels-First)
      ])
      self.set_name = set_name
      self.data = data_list
      self.instance_map = []
      for i, d in enumerate(tqdm(self.data)):
        image = cv2.imread(d['file_name'])
        for j in range(len(d['annotations'])):
          img, mask = get_instance_sample(d, j, image)
          self.instance_map.append((img, mask)) 

  '''
  # you can change the value of length to a small number like 10 for debugging of your training procedure and overfeating
  # make sure to use the correct length for the final training
  '''
  def __len__(self):
      return len(self.instance_map)

  def numpy_to_tensor(self, img, mask):
    if self.transforms is not None:
        img = self.transforms(img)
    img = torch.tensor(img, dtype=torch.float)
    mask = torch.tensor(mask, dtype=torch.float)
    return img, mask

  '''
  # Complete this part by using get_instance_sample function
  # make sure to resize the img and mask to a fixed size (for example 128*128)
  # you can use "interpolate" function of pytorch or "numpy.resize"
  # TODO: 5 lines
  '''
  def __getitem__(self, idx):
    if torch.is_tensor(idx):
        idx = idx.tolist()        

    return self.instance_map[idx]

def get_plane_dataset(set_name='train', batch_size=2):
    my_data_list = DatasetCatalog.get("airplane_{}".format(set_name))
    dataset = PlaneDataset(set_name, my_data_list)
    loader = DataLoader(dataset, batch_size=batch_size, num_workers=4,
                                              pin_memory=True, shuffle=True)
    return loader, dataset

"""### Network"""

'''
# convolution module layer consists of conv2d layer, batch normalization, and relu activation
'''
class conv(nn.Module):
    def __init__(self, in_ch, out_ch, activation=True):
        super(conv, self).__init__()
        if(activation):
          self.layer = nn.Sequential(
             nn.Conv2d(in_ch, out_ch, 3, padding=1),
             nn.BatchNorm2d(out_ch),
             nn.ReLU(inplace=True)
          )
        else:
          self.layer = nn.Sequential(
             nn.Conv2d(in_ch, out_ch, 3, padding=1)  
             )

    def forward(self, x):
        x = self.layer(x)
        return x

'''
# downsampling module equal to a conv module followed by a max-pool layer
'''
class down(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(down, self).__init__()
        self.layer = nn.Sequential(
            conv(in_ch, out_ch),
            nn.MaxPool2d(2)
            )

    def forward(self, x):
        x = self.layer(x)
        return x

'''
# upsampling module equal to a upsample function followed by a conv module
'''
class up(nn.Module):
    def __init__(self, in_ch, out_ch, bilinear=False):
        super(up, self).__init__()
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        else:
            self.up = nn.ConvTranspose2d(in_ch, in_ch, 2, stride=2)

        self.conv = conv(in_ch, out_ch)

    def forward(self, x):
        y = self.up(x)
        y = self.conv(y)
        return y

'''
# the main model completed by using above modules.
# you can also modify the above modules in order to improve your results.
'''
class MyModel(nn.Module):
    def __init__(self):
        super(MyModel, self).__init__()
          
        # Encoder
        
        self.input_conv = conv(3, 32)
        self.down1 = down(32, 64)
        self.down2 = down(64, 128)
        
        # Decoder
        self.up1 = up(128, 64)
        self.up2 = up(64, 32)
        self.up3 = up(32, 3)
        self.output_conv = conv(3, 1, False) 
        
        self.normal1 = nn.BatchNorm2d(32)
        self.normal2 = nn.BatchNorm2d(64)
        self.normal3 = nn.BatchNorm2d(128)

    def forward(self, input):
      y = self.input_conv(input)
      y = self.down1(y)
      y = self.down2(y)
 
      y = self.up1(y)
      y = self.up2(y)
      y = self.up3(y)
      output = self.output_conv(y)
      return output

from torchsummary import summary

model = MyModel().cuda()
summary(model, (3, 128, 128))

"""### Training"""

'''
# The following is a basic training procedure to train the network
# Updated the code to get the best performance
'''

# Set the hyperparameters
num_epochs = 50
batch_size = 4
learning_rate = 0.001
weight_decay = 1e-5

model = MyModel() # initialize the model
model = model.cuda() # move the model to GPU
loader, _ = get_plane_dataset('train', batch_size) # initialize data_loader
crit = nn.BCEWithLogitsLoss() # Define the loss function
optim = torch.optim.SGD(model.parameters(), lr=learning_rate, weight_decay=weight_decay) # Initialize the optimizer as SGD

# start the training procedure
for epoch in range(num_epochs):
  total_loss = 0
  for (img, mask) in tqdm(loader):
    
    
    cv2_imshow(img[0].cpu().detach().permute((0,1,2)).numpy())
    img = torch.tensor(img, dtype=torch.float, device=torch.device('cuda'), requires_grad = True)
    img = torch.permute(img, (0,3,1,2))
    mask = torch.tensor(mask, dtype=torch.float, device=torch.device('cuda'), requires_grad = True).unsqueeze(1)
    
    cv2_imshow((mask[0]*255).cpu().detach().permute(1,2,0).numpy())
    pred = model(img)
    cv2_imshow((pred[0]*255).cpu().detach().permute(1,2,0).numpy())
    loss = crit(pred, mask)
    optim.zero_grad()
    loss.backward()
    optim.step()
    total_loss += loss.cpu().data
  print("Epoch: {}, Loss: {}".format(epoch, total_loss/len(loader)))
  torch.save(model.state_dict(), '{}/output/{}_segmentation_model.pth'.format(BASE_DIR, epoch))

'''
# Saving the final model
'''
torch.save(model.state_dict(), '{}/output/final_segmentation_model.pth'.format(BASE_DIR))

torch.save(model.state_dict(), '{}/output/final_segmentation_model.pth'.format(BASE_DIR))

"""### Evaluation and Visualization"""

'''
# Before starting the evaluation, we need to set the model mode to eval
# We may load the trained model again, in case if we want to continue our code later
'''
batch_size = 4
model = MyModel().cuda()
model.load_state_dict(torch.load('{}/output/final_segmentation_model.pth'.format(BASE_DIR)))
model = model.eval() # chaning the model to evaluation mode will fix the bachnorm layers
loader, dataset = get_plane_dataset('train', batch_size)

def sigmoid(x):
  return 1/(1 + np.exp(-x))

def iou_coef(y_true, y_pred):
  y_true = np.rint(sigmoid(y_true))
  y_pred = np.rint(sigmoid(y_pred))
  intersection = np.count_nonzero(np.multiply(y_true, y_pred))
  union = np.count_nonzero(y_true+y_pred)
  if union == 0:
      return 0
  return intersection/union


total_iou = 0
count = 0
for (img, mask) in tqdm(loader):
  with torch.no_grad():
    img = img.float()
    img = torch.permute(img, (0,3,1,2))
    img = img.cuda()

    mask = torch.tensor(mask, dtype=torch.float, device=torch.device('cuda'), requires_grad = True)

   # cv2_imshow((mask*255).cpu().detach().permute(1,2,0).numpy())
    pred = model(img).cpu().detach()
   # cv2_imshow((pred[0]*255).cpu().detach().permute(1,2,0).numpy())
    for i in range(img.shape[0]):
        newimg = transforms.ToPILImage()(img[i].cpu())
        predicted = np.array(pred[i])[0]
        #cv2_imshow(np.array(newimg))
        #print(pred[i])
        masked = np.array(mask[i].cpu().detach())
        count+=1
        total_iou+=iou_coef(masked, predicted)
  '''
  ## Obtaining the IoU for each img and print the final Mean IoU
  '''
    

print("\n #images: {}, Mean IoU: {}".format(count, total_iou/count))

"""## Part 3: Instance Segmentation

In this part, you need to obtain the instance segmentation results for the test data by using the trained segmentation model in the previous part and the detection model in Part 1.

### Get Prediction
"""

'''
# Defining a new function to obtain the prediction mask by passing a sample data
# For this part, we need to use all the previous parts (predictor, get_instance_sample, data preprocessings, etc)
# It is better to keep everything (as well as the output of this funcion) on gpu as tensors to speed up the operations.
# pred_mask is the instance segmentation result and should have different values for different airplanes.
'''


def get_prediction_mask(data, bool = False):
  image = cv2.imread(data['file_name'])
  if bool:
    maskdata = np.zeros([data['height'], data['width']])
    for i,j in enumerate(data['annotations']):
      bbox = j['bbox']
      x,y,w,h = bbox
      x = int(x)
      y = int(y)
      w = int(w)
      h = int(h)
      cropmask = image[y:y+h, x:x+w]
      cropmask = torch.tensor(cropmask, dtype=torch.float, device=torch.device('cuda'), requires_grad = True).unsqueeze(1)
      cropmask = torch.permute(cropmask, (1,3,0,2))
      predicted_mask = model(cropmask)
      
      predicted_mask = predicted_mask.squeeze(1)
      #cv2_imshow((predicted_mask*50).cpu().detach().permute(1,2,0).numpy())
      predicted_mask[predicted_mask<0] = 0
      predicted_mask[predicted_mask>0] = 1
      predicted_mask = torch.floor(predicted_mask)
      predicted_mask = predicted_mask.int()
      predicted_mask = predicted_mask[0].cpu().detach().numpy()
      predicted_mask = np.rint((predicted_mask))*(i+1) 
      #cv2_imshow(predicted_mask*30)
      predicted_mask = cv2.resize(predicted_mask, (w,h))
      maskdata[y:y+h, x:x+w] = predicted_mask  

  else:
    
    predictionImg = predictor(image)['instances'].pred_boxes
    maskdata = np.zeros([data['height'], data['width']])

    for i in range(len(predictionImg)):
      bbox = np.floor(predictionImg.tensor.cpu().numpy())
      print(bbox)
      x = int(bbox[i][0])
      y = int(bbox[i][1])
      w = int(bbox[i][2])
      h = int(bbox[i][3])
      cropmask = image[y:h, x:w]
      cv2_imshow(cropmask)
      cropmask = torch.tensor(cropmask, dtype=torch.float, device=torch.device('cuda'), requires_grad = True).unsqueeze(1)
      cropmask = torch.permute(cropmask, (1,3,0,2))
      predicted_mask = model(cropmask)
      predicted_mask = predicted_mask.squeeze(1)
      predicted_mask[predicted_mask<0] = 0
      predicted_mask[predicted_mask>0] = 1
      predicted_mask = torch.floor(predicted_mask)
      predicted_mask = predicted_mask.int()
      #cv2_imshow((predicted_mask*255).cpu().detach().permute(1,2,0).numpy())
      predicted_mask = predicted_mask[0].cpu().detach().numpy()
      predicted_mask = np.rint((predicted_mask))*(i+1) 
      predicted_mask = cv2.resize(predicted_mask, (w-x,h-y))
      maskdata[y:h, x:w] = predicted_mask
    gt_mask = np.zeros([data['height'], data['width']])

    
  for i, j in enumerate(data['annotations']):
    bbox = j['bbox']
    x,y,w,h = [int(j) for j in bbox]
    h = h+y
    w = w+x
    local_gt_mask = detectron2.utils.visualizer.GenericMask(j['segmentation'], data['height'], data['width']).mask
    overlapping = np.maximum(gt_mask[y:h, x:w],local_gt_mask[y:h, x:w]*(i+1))
    gt_mask[y:h, x:w] = overlapping

    

  image = torch.tensor(image, dtype=torch.float, device=torch.device('cuda'), requires_grad = True)
  gt_mask = torch.tensor(gt_mask, dtype=torch.float, device=torch.device('cuda'), requires_grad = True)
  maskdata = torch.tensor(maskdata, dtype=torch.float, device=torch.device('cuda'), requires_grad = True)

  return image, gt_mask, maskdata # gt_mask could be all zero when the ground truth is not given.

d = get_detection_data("train")
for i in tqdm(d):
  get_prediction_mask(i, False)

"""### Visualization and Submission"""

'''
# Visualise the output prediction as well as the GT Mask and Input image for a sample input
'''
dataset = get_detection_data('train.json')
for i in np.random.randint(0,50,5):
  img, true_mask, pred_mask = get_prediction_mask(dataset[i])

  pred_mask = pred_mask.cpu().detach().numpy()
  true_mask = true_mask.cpu().detach().numpy()
  max_val = pred_mask.max()
  fact = 255./max_val
  pred_mask*= fact
  max_val = true_mask.max()
  fact = 255./max_val
  true_mask*= fact
  cv2_imshow(cv2.resize(img, (img.shape[1]//3, img.shape[0]//3), interpolation = cv2.INTER_AREA))
  cv2_imshow(cv2.resize(true_mask, (true_mask.shape[1]//3, true_mask.shape[0]//3), interpolation = cv2.INTER_AREA))
  print("\n")
  cv2_imshow(cv2.resize(pred_mask, (pred_mask.shape[1]//3, pred_mask.shape[0]//3), interpolation = cv2.INTER_AREA))

img, true_mask, pred_mask = get_prediction_mask(dataset[0])
pred_file = open("{}/pred-test.csv".format(BASE_DIR), 'w')
pd.DataFrame(pred_mask).to_csv(pred_file, index=False)
pred_file.close()

'''
# ref: https://www.kaggle.com/rakhlin/fast-run-length-encoding-python
# https://www.kaggle.com/c/airbus-ship-detection/overview/evaluation
'''
def rle_encoding(x):
    '''
    x: pytorch tensor on gpu, 1 - mask, 0 - background
    Returns run length as list
    '''
    dots = torch.where(torch.flatten(x.long())==1)[0]
    if(len(dots)==0):
      return []
    inds = torch.where(dots[1:]!=dots[:-1]+1)[0]+1
    inds = torch.cat((torch.tensor([0], device=torch.device('cuda'), dtype=torch.long), inds))
    tmpdots = dots[inds]
    inds = torch.cat((inds, torch.tensor([len(dots)], device=torch.device('cuda'))))
    inds = inds[1:] - inds[:-1]
    runs = torch.cat((tmpdots, inds)).reshape((2,-1))
    runs = torch.flatten(torch.transpose(runs, 0, 1)).cpu().data.numpy()
    return ' '.join([str(i) for i in runs])

'''
#
# The speed of your code in the previous parts highly affects the running time of this part
'''

preddic = {"ImageId": [], "EncodedPixels": []}

'''
# Writing the predictions of the training set
'''

my_data_list = DatasetCatalog.get("airplane_{}".format('train'))
for i in tqdm(range(len(my_data_list)), position=0, leave=True):
  print(i)
  sample = my_data_list[i]
  sample['image_id'] = sample['file_name'].split("/")[-1][:-4]
  img, true_mask, pred_mask = get_prediction_mask(sample)
  
  pred_file = open("{}/pred_mask.csv".format(BASE_DIR), 'w')
  pd.DataFrame(preddic).to_csv(pred_file, index=False)
  pred_file.close()
  inds = torch.unique(pred_mask)
  if(len(inds)==1):
    preddic['ImageId'].append(sample['image_id'])
    preddic['EncodedPixels'].append([])
  else:
    for index in inds:
      if(index == 0):
        continue
      
      tmp_mask = (pred_mask==index)
      encPix = rle_encoding(tmp_mask)
      preddic['ImageId'].append(sample['image_id'])
      preddic['EncodedPixels'].append(encPix)

'''
# Writing the predictions of the test set
'''

my_data_list = DatasetCatalog.get("airplane_{}".format('test'))
for i in tqdm(range(len(my_data_list)), position=0, leave=True):
  sample = my_data_list[i]
  sample['image_id'] = sample['file_name'].split("/")[-1][:-4]
  img, true_mask, pred_mask = get_prediction_mask(sample)
  inds = torch.unique(pred_mask)
  if(len(inds)==1):
    preddic['ImageId'].append(sample['image_id'])
    preddic['EncodedPixels'].append([])
  else:
    for j, index in enumerate(inds):
      if(index == 0):
        continue
      tmp_mask = (pred_mask==index).double()
      encPix = rle_encoding(tmp_mask)
      preddic['ImageId'].append(sample['image_id'])
      preddic['EncodedPixels'].append(encPix)

pred_file = open("{}/pred.csv".format(BASE_DIR), 'w')
pd.DataFrame(preddic).to_csv(pred_file, index=False)
pred_file.close()

"""## Part 4: Mask R-CNN

For this part you need to follow a same procedure to part 2 with the configs of Mask R-CNN, other parts are generally the same as part 2.

### Data Loader
"""

data = get_detection_data("train")

"""### Network"""

cfg = get_cfg()
cfg.OUTPUT_DIR = "{}/output/".format(BASE_DIR)

cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
cfg.DATASETS.TRAIN = ("airplane_train")
cfg.DATASETS.TEST = ()

cfg.DATALOADER.NUM_WORKERS = 2
cfg.SOLVER.BASE_LR = 0.00025
cfg.SOLVER.IMS_PER_BATCH = 2
cfg.SOLVER.MAX_ITER = 1000
cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 512   
cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1

"""### Training"""

trainer = DefaultTrainer(cfg) 
#trainer.resume_or_load(resume=False) 
#trainer.train()
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.4
predictor = DefaultPredictor(cfg)

"""### Evaluation and Visualization"""

for i in random.sample(data_test, 3):
  image = cv2.imread(i['file_name'])
  output = predictor(image)

  v = Visualizer(image[:, :, ::-1],
                 metadata = plane_test_metadata,
                 scale = 0.5)
  out = v.draw_instance_predictions(output['instances'].to('cpu'))
  cv2_imshow(out.get_image()[:, :, ::-1])

'''
# Use COCOEvaluator and build_detection_train_loader
# You can save the output predictions using inference_on_dataset
# TODO: approx 5 lines
'''
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.data import build_detection_test_loader

evaluator = COCOEvaluator("airplane_train", cfg, False, output_dir= "./output/")
val_loader = build_detection_test_loader(cfg, "airplane_train")
print(inference_on_dataset(trainer.model, val_loader, evaluator))