#!/usr/bin/python3
# -*- coding:utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
# import glob
import numpy as np
from tensorflow.contrib.layers.python.layers import batch_norm
import argparse

"""
参数调节参考：
http://blog.csdn.net/wc781708249/article/details/78013750
only cnn no full connect
tfrecord to numpy for train
batch_norm
lrn
渐变的lr

样本数据归一化
xs is of size[N x D] (N is the number of data, D is their dimensionality).
# Z-score标准化方法
# mean = numpy.reshape(numpy.average(xs, 1), [numpy.shape(xs)[0], 1])
# std = numpy.reshape(numpy.std(xs, 1), [numpy.shape(xs)[0], 1])
# xs = (xs - mean) / (std+0.001)

# min-max标准化（Min-Max Normalization
max_ = numpy.reshape(numpy.max(xs, 1), [numpy.shape(xs)[0], 1])
min_ = numpy.reshape(numpy.min(xs, 1), [numpy.shape(xs)[0], 1])
xs = (xs - min_) / (max_ - min_+0.001)

其他 normal
X -= np.mean(X, axis = 0).
X /= np.std(X, axis = 0)

Batch Normalization

PCA and Whitening
X -= np.mean(X, axis = 0) # zero-center the data (important)
cov = np.dot(X.T, X) / X.shape[0] # get the data covariance matrix
U,S,V = np.linalg.svd(cov)
Xrot = np.dot(X, U) # decorrelate the data
Xrot_reduced = np.dot(X, U[:,:100]) # Xrot_reduced becomes [N x 100]
# whiten the data:
# divide by the eigenvalues (which are square roots of the singular values)
Xwhite = Xrot / np.sqrt(S + 1e-5)

Weight Initialization
W = 0.01* np.random.randn(D,H),

w = np.random.randn(n) / sqrt(n), where n is the number of its inputs.

w = np.random.randn(n) * sqrt(2.0/n)

http://blog.csdn.net/wc781708249/article/details/78013275
"""

parser = argparse.ArgumentParser()
parser.add_argument("-bs", "--batch_size", help="The batch size",type=int,default=128)
parser.add_argument("-do", "--droup_out", help="The droup out",type=float,default=0.7)
parser.add_argument("-lr", "--learn_rate", help="The learn rate",type=float,default=1e-1)
parser.add_argument("-ns", "--num_steps", help="The num steps",type=int,default=100000)
parser.add_argument("-ds", "--disply_step", help="The disp step",type=int,default=2000)
parser.add_argument("-ipi", "--img_piexl", help="The image piexl",type=int,default=28)
parser.add_argument("-ch", "--channels", help="The image channels",type=int,default=1)
parser.add_argument("-nc", "--n_classes", help="The image n classes",type=int,default=10)
parser.add_argument("-tr", "--train", help="The train/test mode",type=int,default=1)# 1 train 0 test
parser.add_argument("-log", "--logdir", help="The model logdir",type=str,default="./output/")
parser.add_argument("-md", "--model_name", help="The model name",type=str,default="model.ckpt")
args = parser.parse_args()
print("args:",args)


batch_size=args.batch_size
droup_out = args.droup_out
# learn_rate = args.learn_rate
INITIAL_LEARNING_RATE=args.learn_rate
num_steps = args.num_steps
disp_step = args.disply_step
img_piexl=args.img_piexl
channels=args.channels
n_classes=args.n_classes

train=args.train # 1 train 0 test
logdir=args.logdir
# Load datas
def load_images_from_tfrecord(tfrecord_file,batch_size):
    filename_queue = tf.train.string_input_producer(
        tf.train.match_filenames_once(tfrecord_file)) # 加载多个Tfrecode文件
    reader = tf.TFRecordReader()
    _, serialized = reader.read(filename_queue)

    features = tf.parse_single_example(
        serialized,
        features={
            # 'label': tf.FixedLenFeature([], tf.string),
            'label': tf.FixedLenFeature([], tf.int64),
            'image': tf.FixedLenFeature([], tf.string),
        })

    record_image = tf.decode_raw(features['image'], tf.float32)

    # Changing the image into this shape helps train and visualize the output by converting it to
    # be organized like an image.
    # 修改图像的形状有助于训练和输出的可视化
    image = tf.reshape(record_image, [img_piexl, img_piexl, channels])

    # label = tf.cast(features['label'], tf.string)
    label = tf.cast(features['label'], tf.int64)


    # label string-->int 0,1 标签
    # label = tf.case({tf.equal(label, tf.constant('ants')): lambda: tf.constant(0),
    #                         tf.equal(label, tf.constant('bees')): lambda: tf.constant(1),
    #                         }, lambda: tf.constant(-1), exclusive=True)


    min_after_dequeue = 1000
    # batch_size = 3
    capacity = min_after_dequeue + 3 * batch_size
    image_batch, label_batch = tf.train.shuffle_batch(
        [image, label], batch_size=batch_size, capacity=capacity, min_after_dequeue=min_after_dequeue)


    '''
    # Find every directory name in the imagenet-dogs directory (n02085620-Chihuahua, ...)
    labels = list(map(lambda c: c.split("\\")[-2], glob.glob(imagepath))) # 找到目录名（标签） linux使用 "/"

    # Match every label from label_batch and return the index where they exist in the list of classes
    # 匹配每个来自label_batch的标签并返回它们在类别列表中的索引
    train_labels = tf.map_fn(lambda l: tf.where(tf.equal(labels, l))[0,0:1][0], label_batch, dtype=tf.int64)
    '''

    # Converting the images to a float of [0,1) to match the expected input to convolution2d
    # 将图像转换为灰度值位于[0,1)的浮点类型，
    float_image_batch = tf.image.convert_image_dtype(image_batch, tf.float32)
    return float_image_batch,label_batch


# with tf.Graph().as_default() as graph:
x=tf.placeholder(tf.float32,[None,img_piexl,img_piexl,channels])
# y_=tf.placeholder(tf.float32,[None,n_classes])
y_ = tf.placeholder(tf.int64, [None, ])
keep=tf.placeholder(tf.float32)
is_training = tf.placeholder(tf.bool, name='MODE')

# x_img=tf.reshape(x,[-1,img_piexl,img_piexl,channels])

def batch_norm_layer(inputT, is_training=True, scope=None):
    # Note: is_training is tf.placeholder(tf.bool) type
    return tf.cond(is_training,
                   lambda: batch_norm(inputT, is_training=True,
                                      center=True, scale=True, activation_fn=tf.nn.relu, decay=0.9, scope=scope),
                   lambda: batch_norm(inputT, is_training=False,
                                      center=True, scale=True, activation_fn=tf.nn.relu, decay=0.9,
                                      scope=scope, reuse=True))

def conv2d(input, kernel_size, input_size, output_size, is_training, name):
    with tf.name_scope(name) as scope:
        with tf.variable_scope(name):
            # scope.reuse_variables()
            w = tf.get_variable('w', [kernel_size, kernel_size, input_size, output_size], tf.float32,
                                initializer=tf.random_uniform_initializer) * np.sqrt(2.0/input_size)
            b = tf.get_variable('b', [output_size], tf.float32, initializer=tf.random_normal_initializer) + 0.1
            conv = tf.nn.conv2d(input, w, [1, 1, 1, 1], padding="SAME")
            conv = tf.nn.bias_add(conv, b)
            conv = batch_norm_layer(conv, is_training, scope)
            conv = tf.nn.relu(conv)
    return conv


# -----↓------↓------↓------↓------↓------↓-------↓-----↓--------↓--------#
# convolution1
conv1=conv2d(#tf.image.convert_image_dtype(x_img,tf.float32),
                x,
                 3,1,32,is_training,'conv1')
conv1=tf.nn.max_pool(conv1,[1,2,2,1],[1,2,2,1],padding="SAME") # [n,14,14,16]
conv1 = tf.nn.dropout(conv1, keep)
conv1 = tf.nn.lrn(conv1, 4, bias=1.0, alpha=0.001 / 9.0, beta=0.75,
                  name='norm1')

# convolution2
conv2 = conv2d(conv1,
                   3, 32, 64, is_training,'conv2')
conv2=tf.nn.max_pool(conv2,[1,2,2,1],[1,2,2,1],padding="SAME") # [n,7,7,32]
conv2 = tf.nn.dropout(conv2, keep)
conv2 = tf.nn.lrn(conv2, 4, bias=1.0, alpha=0.001 / 9.0, beta=0.75,
                  name='norm2')

# conv3
conv3 = conv2d(conv2,
               3, 64, 128, is_training,'conv3')
conv3 = tf.nn.max_pool(conv3, [1, 2, 2, 1], [1, 2, 2, 1], padding="VALID")  # [n,3,3,64]
conv3 = tf.nn.lrn(conv3, 4, bias=1.0, alpha=0.001 / 9.0, beta=0.75, name='norm3')
conv3 = tf.nn.dropout(conv3, keep)


# conv4
conv4 = conv2d(conv3,
               3, 128, 10, is_training,'conv4')
conv4 = tf.nn.max_pool(conv4, [1, 2, 2, 1], [1, 2, 2, 1], padding="VALID")  # [n,1,1,10]
conv4 = tf.nn.lrn(conv4, 4, bias=1.0, alpha=0.001 / 9.0, beta=0.75, name='norm4')
# conv4 = tf.nn.dropout(conv4, keep)


# output
y=tf.reshape(conv4,[-1,n_classes])

# ------↑-----↑-------↑-----↑---------↑----↑--------↑-------↑-----↑----------#


# loss=tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(labels=y_,logits=y))

loss=tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y_,logits=y))

global_step = tf.Variable(0, name="global_step", trainable=False)
# learn_rate = tf.train.exponential_decay(INITIAL_LEARNING_RATE,
      #                                            global_step,
      #                                            10000,
      #                                            0.96,
      #                                            staircase=False)
learn_rate=tf.train.polynomial_decay(INITIAL_LEARNING_RATE,global_step,70000,1e-6,0.8,False)


train_op=tf.train.AdamOptimizer(learn_rate).minimize(loss,global_step=global_step)

# correct_prediction = tf.equal(tf.argmax(y, 1), tf.argmax(y_, 1))
correct_prediction = tf.equal(tf.argmax(y, 1), y_)

# Calculate accuracy
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

# sess=tf.InteractiveSession(graph=graph)

# tf.global_variables_initializer().run()


if __name__=="__main__":
    if train:
        img_batch, label_batch=load_images_from_tfrecord("output/training-images/*.tfrecords",batch_size)
        with tf.Session(graph=tf.get_default_graph()) as sess:
            tf.global_variables_initializer().run()
            tf.local_variables_initializer().run()
            saver = tf.train.Saver()
            # 验证之前是否已经保存了检查点文件
            ckpt = tf.train.get_checkpoint_state(logdir)
            if ckpt and ckpt.model_checkpoint_path:
                saver.restore(sess, ckpt.model_checkpoint_path)
                # initial_step = int(ckpt.model_checkpoint_path.rsplit('-', 1)[1])
            #else:
            #    tf.global_variables_initializer().run()
            #    tf.local_variables_initializer().run()

            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(sess=sess, coord=coord)
            step=0
            try:
                while not coord.should_stop():
                    for step in range(num_steps):
                    # while step<num_steps:
                        [batch_xs,batch_ys]=sess.run([img_batch,label_batch])
                        batch_xs=batch_xs.reshape([-1,img_piexl*img_piexl*channels])
                        # normal
                        batch_xs -= np.mean(batch_xs, axis=0)
                        batch_xs /= np.std(batch_xs, axis=0)+0.0001 # 防止出现除数为0
                        batch_xs = batch_xs.reshape([-1, img_piexl, img_piexl, channels])
                        batch_ys=batch_ys.reshape([-1,])
                        train_op.run({x: batch_xs, y_: batch_ys, keep: droup_out,is_training:True})
                        # step=sess.run(global_step)
                        if step % disp_step == 0:
                            print("step", step, 'acc', accuracy.eval({x: batch_xs, y_: batch_ys, keep: droup_out,is_training:True}), 'loss',
                                  loss.eval({x: batch_xs, y_: batch_ys, keep: droup_out,is_training:True}))
                        saver.save(sess, logdir + args.model_name, global_step=step)
                    else:
                        break
            except tf.errors.OutOfRangeError:
                print('Done training -- epoch limit reached')
            finally:
                coord.request_stop()
            coord.join(threads)

    else: # test
        img_batch, label_batch = load_images_from_tfrecord("output/testing-images/*.tfrecords", batch_size)
        with tf.Session(graph=tf.get_default_graph()) as sess:
            tf.global_variables_initializer().run()
            tf.local_variables_initializer().run()
            saver = tf.train.Saver()
            # 验证之前是否已经保存了检查点文件
            ckpt = tf.train.get_checkpoint_state(logdir)
            if ckpt and ckpt.model_checkpoint_path:
                saver.restore(sess, ckpt.model_checkpoint_path)
                # initial_step = int(ckpt.model_checkpoint_path.rsplit('-', 1)[1])

            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(sess=sess, coord=coord)
            try:
                while not coord.should_stop():
                    for i in range(10):
                        [batch_xs, batch_ys] = sess.run([img_batch, label_batch])
                        batch_xs = batch_xs.reshape([-1, img_piexl*img_piexl*channels])
                        batch_xs -= np.mean(batch_xs, axis=0)
                        batch_xs /= np.std(batch_xs, axis=0) + 0.0001  # 防止出现除数为0
                        batch_xs = batch_xs.reshape([-1, img_piexl, img_piexl, channels])
                        batch_ys = batch_ys.reshape([-1, ])
                        # acc=accuracy.eval({x: batch_xs, y_: batch_ys, keep: 1.,is_training:False})
                        acc = accuracy.eval({x: batch_xs, y_: batch_ys, keep: 1., is_training: True})
                        print('test acc',acc)
                    else:
                        break
            except tf.errors.OutOfRangeError:
                print('Done training -- epoch limit reached')
            finally:
                coord.request_stop()
            coord.join(threads)
