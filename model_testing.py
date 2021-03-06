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

def imshow(img):
    #img = img / 4 + 0.5     # unnormalize
    img[0, :, :] *= .229
    img[1, :, :] *= .224
    img[2, :, :] *= .225
    img[0, :, :] += .485
    img[1, :, :] += .456
    img[2, :, :] += .406
    npimg = img.numpy()
    plt.imshow(np.transpose(npimg, (1, 2, 0)))

def load_data(path, batch_size = 100, shuffle = True):
    normalize = transforms.Normalize([0.485, 0.456, 0.406],
                     [0.229, 0.224, 0.225])
    data_loader = torch.utils.data.DataLoader(
            torchvision.datasets.ImageFolder(path, transforms.Compose([
                transforms.Scale(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                normalize,
            ])),
            batch_size=batch_size, shuffle=shuffle,
            num_workers=1, pin_memory=True)
    return data_loader

def test(inputs):
    yield inputs

def diff(imgs, old_imgs):
    fig = plt.figure("diff")
    plt.imshow(np.transpose(np.abs(torchvision.utils.make_grid(imgs - old_imgs).numpy()), (1, 2, 0)))

def save_figure(imgs, name):
    fig = plt.figure(name)
    imshow(torchvision.utils.make_grid(imgs))
    fig.savefig("/scratch/jsf239/{}.png".format(name))

def is_done(predicted, target_class, batch_size, iters, min_iters):
    all_right = np.all(predicted.numpy() == [target_class]*batch_size)
    return all_right and iters > min_iters

def create_adversary(batch_size=1, target_class=1, image_reg=100, lr=.1, l_inf=False):
    # Load pretrained network
    resnet = models.resnet18(pretrained=True)
    resnet.eval()
    for parameter in resnet.parameters():
        parameter.requires_grad = False
    # Load in first <batch_size> images for validation
    valdir = "/scratch/datasets/imagenet/val"
    val_loader = load_data(valdir, batch_size, True)
    data = next(iter(val_loader))
    images, labels =  data
    print ("The expected labels are {}".format(labels))
    old_image = images.clone()
    inputs = Variable(images, requires_grad = True)
    new_labels = Variable(torch.LongTensor([target_class]*batch_size))
    # Instantiate Loss Classes
    CrossEntropy = nn.CrossEntropyLoss()
    MSE = nn.MSELoss()
    opt = optim.SGD(test(inputs), lr=lr, momentum=0.9)
    print (images[0,0,:,:].shape, np.min(images[0,:,:].numpy()))
    torch.clamp(images[:, 0,:,:], min=-.485/0.229, max=(1-.485)/0.229, out=old_image[:,0,:,:])
    torch.clamp(old_image[:, 1,:,:], min=-.456/0.224, max=(1-.456)/0.224, out=old_image[:,1,:,:])
    torch.clamp(old_image[:, 2,:,:], min=-.406/0.225, max=(1-.406)/0.225, out=old_image[:,2,:,:])
    save_figure(old_image, "Before_{}_{}".format(image_reg, lr))
    plt.show()
    save_figure(images, "Before_{}_{}".format(image_reg, lr))
    predicted = torch.Tensor([-1]*batch_size)
    iters = 0
    min_iters = 0
    while not is_done(predicted, target_class, batch_size, iters, min_iters):
        print ("Iteration {}".format(iters))
        opt.zero_grad()
        torch.clamp(images[:, 0,:,:], min=-.485/0.229, max=(1-.485)/0.229, out=images[:,0,:,:])
        torch.clamp(images[:, 1,:,:], min=-.456/0.224, max=(1-.456)/0.224, out=images[:,1,:,:])
        torch.clamp(images[:, 2,:,:], min=-.406/0.225, max=(1-.406)/0.225, out=images[:,2,:,:])

        outputs = resnet(inputs)
        model_loss = CrossEntropy(outputs, new_labels)
        if not l_inf:
            image_loss = MSE(inputs, Variable(old_image))
        else:
            image_loss = torch.max(inputs - Variable(old_image))
        loss = model_loss + image_reg*image_loss
        predicted = torch.max(outputs.data, 1)
        print ("Target Class Weights:")
        print (outputs.data[:, target_class])
        print ("Predicted Classes:")
        print (predicted)
        predicted = predicted[1]
        iters += 1
        if is_done(predicted, target_class, batch_size, iters, min_iters):
            print (images.numpy().shape)
            print (old_image.numpy().shape)
            save_figure(inputs.data, "After_{}_{}".format(image_reg, lr))
            diff(images, old_image)
            plt.show()
        else:
            print (image_loss)
            print (model_loss)
            loss.backward()
            opt.step()
    

def load_and_run_pretrained():
    # Loading pretrained network and data 
    resnet = models.resnet101(pretrained=True)
    resnet.eval()
    print (resnet)
    valdir = "/scratch/datasets/imagenet/val"
    val_loader = load_data(valdir, 2)
    print("Done instantiating data loader")
    correct = 0
    total = 0
    # Cycle through all data and determine which were correctly labeled
    for data in val_loader:
        images, labels = data
        output = resnet(Variable(images))
        print ("The output is {}".format(output))
        _, predicted = torch.max(output.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum()
        print("Testing batch. Accuracy is {}".format(float(correct)/total))
    print("Accuracy is {}".format(float(correct)/total))

