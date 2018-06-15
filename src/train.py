#!/usr/bin/env python3


trial      = '02'
batch_size = 2**6
step_eval  = 2**7
step_save  = 2**12
ckpt       = None


from model import model
from os.path import expanduser, join
from tqdm import tqdm
from utils import permute, batch, PointedIndex, decode
import numpy as np
import tensorflow as tf
tf.set_random_seed(0)


src_train = np.load("trial/data/train_src.npy")
tgt_train = np.load("trial/data/train_tgt.npy")

i = permute(len(src_train))
src_train = src_train[i]
tgt_train = tgt_train[i]
del i

src, tgt = batch((src_train, tgt_train), batch_size= batch_size)
m = model(src= src, tgt= tgt
          , dim= 256, dim_mid= 512
          , num_head= 4, num_layer= 2)

########################
# autoregressive model #
########################

m.p = m.pred[:,-1]
src = np.load("trial/data/valid_src.npy")
rng = range(0, len(src) + batch_size, batch_size)
idx = PointedIndex(np.load("trial/data/index.npy").item()['idx2tgt'])

def write_trans(path, src= src, rng= rng, idx= idx, batch_size= batch_size):
    with open(path, 'w') as f:
        for i, j in zip(rng, rng[1:]):
            for p in trans(m, src[i:j])[:,1:]:
                print(decode(idx, p), file= f)

def trans(m, src, begin= 2, len_cap= 256):
    w = m.w.eval({m.src: src, m.training: False})
    x = np.full((len(src), len_cap), m.end, dtype= np.int32)
    x[:,0] = begin
    for i in range(1, len_cap):
        p = m.p.eval({m.w: w, m.x: x[:,:i], m.training: False})
        if np.alltrue(p == m.end): break
        x[:,i] = p
    return x

############
# training #
############

path = expanduser("~/cache/tensorboard-logdir/explicharr")
wtr = tf.summary.FileWriter(join(path, "trial{}".format(trial)))
# wtr = tf.summary.FileWriter(join(path, "graph"), tf.get_default_graph())
saver = tf.train.Saver()
sess = tf.InteractiveSession()

if ckpt:
    saver.restore(sess, ckpt)
else:
    tf.global_variables_initializer().run()

summ = tf.summary.merge((
    tf.summary.scalar('step_loss', m.loss)
    , tf.summary.scalar('step_acc', m.acc)))

while True:
    for _ in tqdm(range(step_save), ncols= 70):
        sess.run(m.up)
        step = sess.run(m.step)
        if not (step % step_eval):
            wtr.add_summary(sess.run(summ, {m.training: False}), step)
    saver.save(sess, "trial/model/m", step)
    write_trans("trial/pred/m{}".format(step))
