
import cv2
import numpy as np
import tensorflow as tf
import collections
tf.logging.set_verbosity(tf.logging.ERROR)
from skimage import transform as tr
from multiprocessing import Process, Queue, Manager, Value, Lock
# In[2]:


def Exposure(eval_data,e,y,q,no_of_processes,size):
    m = 1
    x = 1024
    n = 3
    dim = np.int(np.sqrt(x))
    p = (int)(size/no_of_processes)
    eval_data = eval_data[(y-1)*p:y*p]
    labels = eval_data[:,-1]
    eval_data = eval_data[:,0:x*n]
    temp = np.ndarray.astype(np.copy(eval_data.reshape(-1,dim,dim,n)),dtype=np.uint8)
    for i in range(0,eval_data.shape[0]):
        invGamma = 1.0 / e
        table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        temp[i] = cv2.LUT(temp[i], table)
    temp = np.clip(temp,0,255)
    temp = temp.reshape(-1,x*n)
    labels = labels.reshape(temp.shape[0],1)
    temp = np.hstack((temp,labels))
    q.put(temp)

# In[4]:

def Transform(name,eval_data,param):
    sync = Value('i', 1)
    if name is "rotation" or name is "Rotation":
        name = Rotation
    elif name is "scaling" or name is "Scaling":
        name = Scaling
    elif name is "exposure" or name is "Exposure":
        name = Exposure
    elif name is "Shear" or name is "shear":
        name = Shear
    elif name is "Perspective" or name is "perspective":
        name = Perspective
    elif name is "Exposure" or name is "exposure":
        name = Exposure
    elif name is "Translation" or name is "translations":
        name = Translation
    temp = np.copy(eval_data)
    nprocs = 10
    out_q = Queue()
    procs = []
    for i in range(nprocs):
        p = Process(
                target=name,
                args=(temp,param,i+1,out_q,nprocs,temp.shape[0]))
        procs.append(p)
        p.start()
    resultdict = []
    for i in range(nprocs):
        resultdict.append(out_q.get())
    for p in procs:
        p.join()
    temp = np.array(resultdict).reshape(-1,3073)
    return temp



def Translation(eval_data,l,y,q,no_of_processes,size):
    m = 1
    x = 1024
    n = 3
    p = (int)(size/no_of_processes)
    dim = np.int(np.sqrt(x))
    eval_data = eval_data[(y-1)*p:y*p]
    labels = eval_data[:,-1]
    eval_data = eval_data[:,0:x*n]
    temp = np.ndarray.astype(np.copy(eval_data.reshape(-1,dim,dim,n)),dtype=np.uint8)
    M = np.float32([[1,0,l],[0,1,0]])
    for i in range(0,eval_data.shape[0]):
        temp[i] = cv2.warpAffine(temp[i],M,(32,32))
    temp = temp.reshape(-1,x*n)
    labels = labels.reshape(temp.shape[0],1)
    temp = np.hstack((temp,labels))
    q.put(temp)



# In[6]:
def Rotation(eval_data,angle,y,q,no_of_processes,size):
    m = 1
    x = 1024
    n = 3
    p = (int)(size/no_of_processes)
    dim = np.int(np.sqrt(x))
    eval_data = eval_data[(y-1)*p:y*p]
    labels = eval_data[:,-1]
    eval_data = eval_data[:,0:x*n]
    temp = np.ndarray.astype(np.copy(eval_data.reshape(-1,dim,dim,n)),dtype=np.uint8)
    s,r,c,n = temp.shape
    M = cv2.getRotationMatrix2D((c/2,r/2),angle,1)
    for i in range (0,s):
        temp[i] = cv2.warpAffine(temp[i],M,(c,r))
#         temp[i] = temp[i].clip(min=0,max=1)
    temp = temp.reshape(-1,x*n)
    labels = labels.reshape(temp.shape[0],1)
    temp = np.hstack((temp,labels))
    q.put(temp)



# In[1]:

def Scaling(eval_data,l,y,q,no_of_processes,size):
    k = 255
    x = 1024
    n = 3
    dim = np.int(np.sqrt(x))
    p = (int)(size/no_of_processes)
    eval_data = eval_data[(y-1)*p:y*p]
    labels = eval_data[:,-1]
    
    eval_data = eval_data[:,0:3072]
    temp = np.ndarray.astype(np.copy(eval_data.reshape(-1,dim,dim,n)),dtype=np.uint8)    
    s,r,c,n = temp.shape
    for i in range (0,s):
        img = cv2.resize(temp[i],None,fx=l, fy=l, interpolation = cv2.INTER_CUBIC)
        if img.shape[0] > dim:
            m = np.int((img.shape[0]-dim)/2)
            temp[i] = img[m:m+dim,m:m+dim]
        else :
            m = dim
            img = cv2.copyMakeBorder( img, m, m, m, m, cv2.BORDER_CONSTANT)
            m = np.int((img.shape[0]-dim)/2)
            temp[i] = img[m:m+dim,m:m+dim]
    temp = temp.reshape(-1,3072)
    labels = labels.reshape(temp.shape[0],1)
    
    temp = np.hstack((temp,labels))
    q.put(temp)
# In[8]:

def Shear(eval_data,l,y,q,no_of_processes,size):
    ik = 255
    x = 1024
    n = 3
    dim = np.int(np.sqrt(x))
    p = (int)(size/no_of_processes)
    eval_data = eval_data[(y-1)*p:y*p]
    labels = eval_data[:,-1]
    temp1 = []
    eval_data = eval_data[:,0:3072]
    temp = np.ndarray.astype(np.copy(eval_data.reshape(-1,dim,dim,n)),dtype=np.uint8)
    afine_tf = tr.AffineTransform(shear=l)
    for i in range(0,temp.shape[0]):
        p = np.empty([32,32,3])
        r = np.copy(temp[i])
        for j in range(0,3):
            p[:,:,j] = tr.warp(r[:,:,j], inverse_map=afine_tf)
        temp1.append(p)
    temp1 = np.array(temp1).reshape(-1,3072)*255
    labels = labels.reshape(temp.shape[0],1)
    
    temp = np.hstack((temp1,labels))
    q.put(temp)

def Perspective(eval_data,l,y,q,no_of_processes,size):
    k = 255
    x = 1024
    n = 3
    dim = np.int(np.sqrt(x))
    p = (int)(size/no_of_processes)
    eval_data = eval_data[(y-1)*p:y*p]
    labels = eval_data[:,-1]
    eval_data = eval_data[:,0:3072]
    temp = np.ndarray.astype(np.copy(eval_data.reshape(-1,dim,dim,n)),dtype=np.uint8)    
    pts1 = np.float32([[0,0],[32,0],[0,32],[32,32]])
    pts2 = np.float32([[0,0],[l,0],[0,l],[l,l]])
    M = cv2.getPerspectiveTransform(pts1,pts2)
    for i in range(0,temp.shape[0]):
        temp[i] = cv2.warpPerspective(temp[i],M,(32,32))
    temp = temp.reshape(-1,3072)
    labels = labels.reshape(temp.shape[0],1)
    temp = np.hstack((temp,labels))
    q.put(temp)