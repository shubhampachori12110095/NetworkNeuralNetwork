from __future__ import print_function
import numpy as np
import tensorflow as tf
from sklearn.utils import shuffle
from sklearn import metrics
from random import seed
import time

start_time = time.time()
tf.reset_default_graph()

## load and prepare the data
expression = np.loadtxt("../data_expression_sim.csv", dtype=float, delimiter=",")
label_vec = np.array(expression[:,-1], dtype=int)
expression = np.array(expression[:,:-1])
labels = []
for l in label_vec:
    if l == 1:
        labels.append([0,1])
    else:
        labels.append([1,0])
labels = np.array(labels,dtype=int)
partition = np.loadtxt("../partition_sim.txt", dtype=int, delimiter=None)

## omit redundant features accoring to partition
connect_count = np.sum(partition, axis=1)
partition = partition[connect_count!=0,]
expression = expression[:,connect_count!=0]
print ("Number of features after network connection filtering: ", np.shape(expression)[1])

## hyper-parameters and settings
resume = False
learning_rate = 0.0001
learning_rate2 = 0.0001
training_epochs = 200
test_prop = 0.25
batch_size = 4
display_step = 1

n_hidden_1 = np.shape(partition)[1]
n_hidden_2 = 128
n_hidden_3 = 32
n_classes = 2

## prepare for training and testing
n_features = np.shape(expression)[1]
n_instances = np.shape(expression)[0]
# expression, labels = shuffle(expression, labels)
expression_test = expression[:int(n_instances*test_prop),:]
labels_test = labels[:int(n_instances*test_prop),:]
expression = expression[int(n_instances*test_prop):,:]
labels = labels[int(n_instances*test_prop):,:]

## initiate training logs
loss_rec = np.zeros([training_epochs, 1])
training_eval = np.zeros([training_epochs, 2])
testing_eval = np.zeros([int(training_epochs/10), 2])

# def get_batch(x, y, batch_size):
#     batch_x, batch_y = shuffle(x, y, n_samples=batch_size)
#     return batch_x, batch_y


def make_1d_weights(indication):
    w = [tf.Variable(tf.truncated_normal(shape=[1, 1], stddev=0.1)) if item == 1
         else tf.zeros([1, 1]) for item in indication]
    # w = [tf.Variable(tf.truncated_normal(shape=[1, 1], stddev=0.1)) if item == 1
    #      else tf.Variable(tf.zeros([1, 1]), trainable=False) for item in indication]

    # w = [tf.get_variable(name=None, shape=[1,1], dtype=tf.float32,
    #                      initializer=tf.contrib.layers.xavier_initializer(uniform=True))
    #      if item == 1 else tf.Variable(tf.zeros([1, 1]), trainable=False) for item in indication]
    return tf.reshape(w, [len(indication), 1])


def make_weights(n_hidden, partition):
    w = make_1d_weights(partition[:,0])
    for i in range(1, n_hidden):
        temp = make_1d_weights(partition[:,i])
        w = tf.concat([w, temp], 1)
    return w


def multilayer_perceptron(x, weights, biases, keep_prob):

    layer_1 = tf.add(tf.matmul(x, weights['h1']), biases['b1'])
    layer_1 = tf.nn.relu(layer_1)

    layer_2 = tf.add(tf.matmul(layer_1, weights['h2']), biases['b2'])
    layer_2 = tf.nn.relu(layer_2)
    layer_2 = tf.nn.dropout(layer_2, keep_prob=keep_prob)

    layer_3 = tf.add(tf.matmul(layer_2, weights['h3']), biases['b3'])
    ## Do not use batch-norm
    # layer_3 = tf.contrib.layers.batch_norm(layer_3, center=True, scale=True,
    #                                   is_training=is_training)
    layer_3 = tf.nn.relu(layer_3)
    layer_3 = tf.nn.dropout(layer_3, keep_prob=keep_prob)

    out_layer = tf.matmul(layer_3, weights['out']) + biases['out']
    return out_layer


x = tf.placeholder(tf.float32, [None, n_features])
y = tf.placeholder(tf.int32, [None, n_classes])
keep_prob = tf.placeholder(tf.float32)
# is_training = tf.placeholder(tf.bool)
lr = tf.placeholder(tf.float32)

weights = {
    'h1': make_weights(n_hidden_1, partition),
    'h2': tf.Variable(tf.truncated_normal(shape=[n_hidden_1, n_hidden_2], stddev=0.1)),
    'h3': tf.Variable(tf.truncated_normal(shape=[n_hidden_2, n_hidden_3], stddev=0.1)),
    'out': tf.Variable(tf.truncated_normal(shape=[n_hidden_3, n_classes], stddev=0.1))
}

biases = {
    'b1': tf.Variable(tf.random_normal([n_hidden_1])),
    'b2': tf.Variable(tf.random_normal([n_hidden_2])),
    'b3': tf.Variable(tf.random_normal([n_hidden_3])),
    'out': tf.Variable(tf.random_normal([n_classes]))
}

# Construct model
pred = multilayer_perceptron(x, weights, biases, keep_prob)

# Define loss and optimizer
cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y))
optimizer = tf.train.AdamOptimizer(learning_rate=lr).minimize(cost)

# Create a saver
saver = tf.train.Saver(max_to_keep=2)

# Initializing the variables
init = tf.global_variables_initializer()

# Launch the graph
# seed(1)
with tf.Session() as sess:
    sess.run(init)
    if resume:
        saver = tf.train.import_meta_graph('last_saved_model.meta')
        saver.restore(sess, tf.train.latest_checkpoint('./'))
        print ("Existing model loaded.")

    total_batch = int(np.shape(expression)[0] / batch_size)
    # Training cycle
    for epoch in range(training_epochs):
        avg_cost = 0.
        expression_tmp, labels_tmp = shuffle(expression, labels)
        # Loop over all batches
        for i in range(total_batch-1):
            batch_x, batch_y = expression_tmp[i*batch_size:i*batch_size+batch_size], \
                               labels_tmp[i*batch_size:i*batch_size+batch_size]
            # Run optimization op (backprop) and cost op (to get loss value)
            if epoch <= 99:
                _, c= sess.run([optimizer, cost], feed_dict={x: batch_x, y: batch_y,
                                                         keep_prob: 0.9,
                                                         lr: learning_rate
                                                         # is_training: True
                                                         })
            else:
                _, c= sess.run([optimizer, cost], feed_dict={x: batch_x, y: batch_y,
                                                         keep_prob: 0.95,
                                                         lr: learning_rate2
                                                         # is_training: True
                                                         })
            # Compute average loss
            avg_cost += c / total_batch

        del expression_tmp
        del labels_tmp

        # Display logs per epoch step
        if epoch % display_step == 0:
            # w = sess.run(weights['h1'][1:4,10:19], feed_dict={x: batch_x, y: batch_y})
            # print (w)
            loss_rec[epoch] = avg_cost
            print ("Epoch:", '%d' % (epoch+1), "cost=", "{:.9f}".format(avg_cost))

            correct_prediction = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
            accuracy = tf.reduce_mean(tf.cast(correct_prediction, "float"))
            acc = accuracy.eval({x: expression, y: labels,
                           keep_prob: 1,
                           # is_training: False
                           })
            y_score = tf.nn.softmax(logits=pred)
            auc = metrics.roc_auc_score(labels, y_score.eval({x: expression, y: labels,
                                                              keep_prob: 1,
                                                              # is_training: False
                                                              }))
            training_eval[epoch] = [acc, auc]
            print ("Training accuracy:", acc, " Training auc:", auc)

        if epoch % 10 == 9:
            correct_prediction = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
            accuracy = tf.reduce_mean(tf.cast(correct_prediction, "float"))
            acc = accuracy.eval({x: expression_test, y: labels_test,
                           keep_prob: 1,
                           # is_training: False
                           })
            y_score = tf.nn.softmax(logits=pred)
            auc = metrics.roc_auc_score(labels_test, y_score.eval({x: expression_test, y: labels_test,
                                                                   keep_prob: 1,
                                                                   # is_training: False
                                                                   }))
            testing_eval[int(epoch/10)] = [acc, auc]
            print("*** Testing accuracy:", acc, " ***", "*** Testing auc:", auc, " ***")


            # saver.save(sess, "last_saved_model")

    np.savetxt(str(n_instances) + "s_" + str(n_features) + "g_"
               + str(n_hidden_1) + "h1_" + str(n_hidden_2) + "h2_" + str(n_hidden_3) + "h3_loss.csv",
               loss_rec, delimiter=",")
    np.savetxt(str(n_instances) + "s_" + str(n_features) + "g_"
               + str(n_hidden_1) + "h1_" + str(n_hidden_2) + "h2_" + str(n_hidden_3) + "h3_train.csv",
               training_eval, delimiter=",")
    np.savetxt(str(n_instances) + "s_" + str(n_features) + "g_"
               + str(n_hidden_1) + "h1_" + str(n_hidden_2) + "h2_" + str(n_hidden_3) + "h3_test.csv",
               testing_eval, delimiter=",")



print("Total time used: %s minutes " % ((time.time() - start_time)/60) )