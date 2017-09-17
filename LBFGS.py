import abc
import adversaries
import torch
import torchvision
import torchvision.models as models
import torchvision.transforms as transforms
from torch.autograd import Variable
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import torch.nn as nn
import torch.optim as optim

class LBFGS(adversaries.Adverarial_Base):
    
  def adversary_batch(self, data, model, target_class, image_reg, lr):
    """Creates adversarial examples for one batch of data.

    Helper function for create_one_adversary_batch.

    Args:
      data: images, labels tuple of batch to be altered
      model: trained pytorch imagenet model
      target_class: int, class to target for adverserial examples
        If target_class is -1, optimize non targeted attack. Choose next closest class.
      image_reg: Regularization constant for image loss component of loss function
      lr: float, Learning rate

    Returns:
      iters: Number of iterations it took to create adversarial example
      MSE: Means Squared error between original and altered image.

    """
    # Load in first <batch_size> images for validation
    images, original_labels =  data
    if self.cuda:
      images = images.cuda()
      original_labels = original_labels.cuda()
    inputs = Variable(images, requires_grad = True)
    opt = optim.SGD(self.generator_hack(inputs), lr=lr, momentum=0.9)
    self.clamp_images(images)
    old_images = images.clone()
    outputs = model(inputs)
    predicted_classes = torch.max(outputs.data, 1)[1]
    # Set target variables for model loss
    new_labels = self.target_class_tensor(target_class, outputs, original_labels)
    iters = 0
    while not self.all_changed(original_labels, predicted_classes):
      if self.verbose:
        print "Iteration {}".format(iters)
      opt.zero_grad()
      # Clamp loss so that all pixels are in valid range (Between 0 and 1 unnormalized)
      self.clamp_images(images)
      outputs = model(inputs)
      # Compute full loss of adversarial example
      model_loss = self.CrossEntropy(outputs, new_labels)
      image_loss = self.MSE(inputs, Variable(old_images))
      if self.cuda:
        model_loss = model_loss.cuda()
        image_loss = image_loss.cuda()
      loss = model_loss + image_reg*image_loss
      predicted_loss, predicted_classes = torch.max(outputs.data, 1)
      if self.verbose:
        print "Target Class Weights Minus Predicted Weights:"
        print outputs.data[:, new_labels.data][:,0] - predicted_loss
      iters += 1
      if self.all_changed(original_labels, predicted_classes):
        if self.show_images:
          self.save_figure(inputs.data, "After_{}_{}".format(image_reg, lr))
          self.save_figure(old_images, "Before_{}_{}".format(image_reg, lr))
          self.diff(images, old_images)
          plt.show()
      else:
          loss.backward()
          opt.step()
          new_labels = self.target_class_tensor(target_class, outputs, original_labels)
    return iters, self.MSE(images, Variable(old_images)), self.percent_changed(original_labels, predicted_classes)