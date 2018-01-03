#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 28 18:50:17 2017
Chiron queue input
@author: haotianteng
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import os
SIGNAL_LEN = 512
LABEL_LEN = 512
TRAIN_QUEUE_CAPACITY = 500000
VALID_QUEUE_CAPACITY = 100000
def read_data(filename_queue):
    """
    Reads and parses binary file of the .bin data files.
    If a N-way read parallelism is required, please call this function N times
    to give N independent Reader's.
    
    Args:
        filename_queue: A queue of strings with the filenames to read from.
        Can be generated by tf.train.string_input_producer
        
    Returns:
        return a Record class containing following fields:
            key: a scalar string Tensor describing the filename& record number for this example.
            signal_len: a uint16 Tensor given the singal length of this example.
            signal: a [SIGNAL_LEN] float32 Tensor with the signal data. True length is stored in signal_len field, padded with 0.
            label_len: a uint16 Tensor given the label length of this example.
            label: a [LABEL_LEN] uint8 Tensor with the label in the range [0-3(4)], represent A C G T (X).
    """
    class Record(object):
        pass
    record = Record()
    signal_unit = 4
    label_unit = 1
    signal_bytes = SIGNAL_LEN * signal_unit
    label_bytes = LABEL_LEN * label_unit
    len_bytes = 2
    record_len = len_bytes+signal_bytes + len_bytes + label_bytes
    
    reader = tf.FixedLengthRecordReader(record_bytes = record_len)
    record.key, value = reader.read(filename_queue)
    vec = tf.decode_raw(value,tf.int8)
    
    record.signal_len = tf.cast(tf.bitcast(tf.strided_slice(vec,[0],[len_bytes]),type = tf.uint16),dtype = tf.int32)
    record.signal_len.set_shape([])
    signal_vec = tf.reshape(tf.strided_slice(vec,[len_bytes],[len_bytes+signal_bytes]),[SIGNAL_LEN,signal_unit])
    record.signal = tf.bitcast(signal_vec,type = tf.float32)
    record.signal.set_shape([SIGNAL_LEN])
    record.label_len = tf.cast(tf.bitcast(tf.strided_slice(vec,[len_bytes+signal_bytes],[len_bytes+signal_bytes+len_bytes]),type = tf.uint16),dtype = tf.int32)
    record.label_len.set_shape([])
    record.label = tf.cast(tf.strided_slice(vec,[len_bytes+signal_bytes+len_bytes],[record_len]),dtype = tf.int32)
    record.label.set_shape([LABEL_LEN])
    return record
    
def _generate_signal_label_batch(signal,label,signal_len,batch_size,shuffle,queue_capacity=500000,min_queue_examples=200000,threads = 16):
    """
    Generate a queue of signal-label batch.
    Args:
        signal: 1D Tensor of [SIGNAL_LEN] of dtype float32
        label: 1D Tensor of [LABEL_LEN] of dtype int8
        signal_len: Scalar Tensor of dtype uint16, the unpadded length of signal
        batch_size: batch size of the mini batch.
        suffle: boolean number, indicate whether the queue is shuffled.
        queue_capacity: capacity of the queue. Default is 50000
        min_queue_examples: minimum examples in the queue. Default is 20000
        threaeds: number of threads used. Default is 16.
    """
    if shuffle:
        signal_batch,signal_len_batch,label_batch = tf.train.shuffle_batch(
                [signal,signal_len,label],
                batch_size = batch_size,
                num_threads = threads,
                capacity=queue_capacity,
                min_after_dequeue = min_queue_examples)
    else:
        signal_batch,signal_len_batch,label_batch = tf.train.batch(
                [signal,signal_len,label],
                num_threads = threads,
                capacity = queue_capacity)
    #Display the training signals in the visualizer.
    tf.summary.audio('signals',signal_batch,sample_rate = 1)
    
    return signal_batch,signal_len_batch,label_batch

def inputs(data_dir,batch_size,for_valid = False):
    """
    Construct input for Nanopore Sequencing training.
    
    Args:
        data_dir: Path to the binary data directory
        batch_size: Number of signals per batch.
        for_valid: Boolean indicating if input is for validation.
        
    Returns:
        signal_batch: 2D tensor of [batch_size, SIGNAL_LEN] size.
        signal_len_batch: 1D tensor of [batch_size] size.
        label_batch: 2D tensor of [batch_size, LABEL_LEN] size.
    
    """
    filenames = list()
    for file_name in os.listdir(data_dir):
        if file_name.endswith('bin'):
            filenames.append(os.path.join(data_dir,file_name))
    
    filename_queue = tf.train.string_input_producer(filenames)
    read_input = read_data(filename_queue)
    if for_valid:
        os.sys.stdout.write("Filling queue with %d signals before starting to validate. "
                  "This will take some time."% VALID_QUEUE_CAPACITY)
        return _generate_signal_label_batch(
                read_input.signal,
                read_input.label,
                read_input.signal_len,
                batch_size,
                queue_capacity = VALID_QUEUE_CAPACITY,
                shuffle = False)
    else:
        os.sys.stdout.write("Filling queue with %d signals before starting to train. "
                            "This will take some time."% TRAIN_QUEUE_CAPACITY)
        return _generate_signal_label_batch(
                read_input.signal,
                read_input.label,
                read_input.signal_len,
                batch_size,
                queue_capacity = TRAIN_QUEUE_CAPACITY,
                shuffle = True)
    
if __name__ == "__main__":
  TEST_FILE = '/media/haotianteng/Linux_ex/Nanopore_Data/Lambda_R9.4/file_batch_test/data_batch_1.bin'
  with tf.Session() as sess:
      q = tf.FIFOQueue(99, [tf.string], shapes=())
      q.enqueue([TEST_FILE]).run()
      q.close().run()
      result = read_data(q)
      key, label, label_len,signal,signal_len = sess.run([
            result.key, result.label, result.label_len, result.signal, result.signal_len])

