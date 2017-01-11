import tensorflow as tf
import numpy as np
from collections import deque
import random
import sys
import cv2

import flappybird.flappy_new as game # Change to specific game

GAME = 'flappybird' # Name used to store tensorflow data
ACTIONS = 2 # Number of actions per game
NOACTION = [1] + [0] * (ACTIONS - 1)  # No action performed
GAMMA = 0.99 # Decay rate of past observations
OBSERVE = True # Set to true to stop learning
EXPLORE = 2000000 # Frames to learn (modify epsilon)
INITIAL_EPSILON = 0.0001 # Initial value of epsilon
FINAL_EPSILON = 0.0001 # Final value of epsilon
REPLAY_MEMORY = 50000 # Number of previous frames to remember
BATCH = 32 # Size of batch
FRAME_PER_ACTION = 1 # Frames to skip before action
ACTION_FRAME = 1 # How many frames of actions to perform
SAVE_TICK = 10000 # save progress every SAVE_TICK iterations


"""
Generate network layers
This is used to define convolution -> ROL layers
"""
def createNetwork():
    # Network Weights
    # Convolution Layer
    WCONV_1 = weight_variable([8, 8, 4, 32])
    BCONV_1 = b_conv1 = bias_variable([32])

    WCONV_2 = weight_variable([4, 4, 32, 64])
    BCONV_2 = bias_variable([64])

    WCONV_3 = weight_variable([3, 3, 64, 64])
    BCONV_3 = bias_variable([64])

    # Fully Connected Linear Layer 
    WFCL_1 = weight_variable([1600, 512])
    BFCL_1 = bias_variable([512])

    WFCL_2 = weight_variable([512, ACTIONS])
    BFCL_2 = bias_variable([ACTIONS])

    # Input Layer
    IL = tf.placeholder("float", [None, 80, 80, 4])

    # Hidden Layers
    H_CONV1 = tf.nn.relu(conv2d(IL, WCONV_1, 4) + BCONV_1)
    H_POOL1 = max_pool_2x2(H_CONV1)

    H_CONV2 = tf.nn.relu(conv2d(H_POOL1, WCONV_2, 2) + BCONV_2)
    #H_POOL2 = max_pool_2x2(H_CONV2)

    H_CONV3 = tf.nn.relu(conv2d(H_CONV2, WCONV_3, 1) + BCONV_3)
    #H_POOL3 = max_pool_2x2(H_CONV3)

    H_CONV_FLAT = tf.reshape(H_CONV3, [-1, 1600])

    H_FCL = tf.nn.relu(tf.matmul(H_CONV_FLAT, WFCL_1) + BFCL_1)

    # Readout Output Layer
    ROL = tf.matmul(H_FCL, WFCL_2) + BFCL_2

    return IL, ROL, H_FCL

def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev = 0.01)
    return tf.Variable(initial)

def bias_variable(shape):
    initial = tf.constant(0.01, shape = shape)
    return tf.Variable(initial)

def conv2d(x, W, stride):
    return tf.nn.conv2d(x, W, strides = [1, stride, stride, 1], padding = "SAME")

def max_pool_2x2(x):
    return tf.nn.max_pool(x, ksize = [1, 2, 2, 1], strides = [1, 2, 2, 1], padding = "SAME")

"""
Generate placeholders to represent input tensors
Placeholders are used as inputs for the rest of the model
"""
def placeholder_inputs():
    action_placeholder = tf.placeholder("float", [None, ACTIONS])
    labels_placeholder = tf.placeholder("float", [None])
    return action_placeholder, labels_placeholder

"""
Create cost function
"""
def cost_function(ROL):
    action_placeholder, labels_placeholder = placeholder_inputs()
    readout_action = tf.reduce_sum(tf.mul(ROL, action_placeholder), reduction_indices = 1)
    cost = tf.reduce_mean(tf.square(labels_placeholder - readout_action))
    train_step = tf.train.AdamOptimizer(1e-6).minimize(cost)
    return action_placeholder, labels_placeholder, train_step

"""
Learn/Train network
"""
def trainNetwork(IL, ROL, H_FCL, sess):
    # Cost function
    action_placeholder, labels_placeholder, train_step = cost_function(ROL)

    # Setup game
    game_state = game.GameState()

    # Store previous frames in memory using double ended queue
    DEQ = deque()

    # Start the first frame of the game ane preprocess the image to 80x80x4
    image_data, reward, terminal = game_state.frame_step(NOACTION)
    image_data = cv2.cvtColor(cv2.resize(image_data, (80, 80)), cv2.COLOR_BGR2GRAY)
    ret, image_data = cv2.threshold(image_data,1,255,cv2.THRESH_BINARY)
    replay_stack_1 = np.stack((image_data, image_data, image_data, image_data), axis = 2)

    # Load previously saved model or start anew
    saver = tf.train.Saver()
    sess.run(tf.initialize_all_variables())
    checkpoint = tf.train.get_checkpoint_state("saved_networks")
    if checkpoint and checkpoint.model_checkpoint_path:
        saver.restore(sess, checkpoint.model_checkpoint_path)

    epsilon = INITIAL_EPSILON
    t = 0
    while True:
        # Choose an action epsilon greedily
        readout_tick = ROL.eval(feed_dict = {IL : [replay_stack_1]})[0]
        action = np.zeros([ACTIONS])
        action_index = 0
        if t % FRAME_PER_ACTION == 0:
            # Random action
            if random.random() <= epsilon:
                action[random.randrange(ACTIONS)] = 1
            # Learnt action
            else:
                action[np.argmax(readout_tick)] = 1
        # Not action frame
        else:
            action = NOACTION

        # Reduce epsilon (More learnt actions)
        if epsilon > FINAL_EPSILON and t > OBSERVE:
            epsilon -= (INITIAL_EPSILON - FINAL_EPSILON) / EXPLORE

        for i in range(0, ACTION_FRAME):
            # Run selected action and update image,replay data
            image_data_col, reward, terminal = game_state.frame_step(action)
            image_data_gray = cv2.cvtColor(cv2.resize(image_data_col, (80, 80)), cv2.COLOR_BGR2GRAY)
            ret, image_data_gray = cv2.threshold(image_data_gray,1,255,cv2.THRESH_BINARY)
            image_data_gray = np.reshape(image_data_gray, (80, 80, 1))
            replay_stack_2 = np.append(image_data_gray, replay_stack_1[:,:,:3], axis = 2)

            # Store replay data
            DEQ.append((replay_stack_1, action, reward, replay_stack_2, terminal))
            if len(DEQ) > REPLAY_MEMORY:
                DEQ.popleft()

        # Train after generating enough observation data
        if t > BATCH and (not OBSERVE):
            # Train on batch selected randomly
            batch = random.sample(DEQ, BATCH)

            # get the batch variables
            batch_replay_stack_1 = [d[0] for d in batch]
            batch_action = [d[1] for d in batch]
            batch_reward = [d[2] for d in batch]
            batch_replay_stack_2 = [d[3] for d in batch]

            batch_y = []
            batch_readout = ROL.eval(feed_dict = {IL : batch_replay_stack_2})
            for i in range(0, len(batch)):
                # if terminal only equals reward
                if batch[i][4]:
                    batch_y.append(batch_reward[i])
                else:
                    batch_y.append(batch_reward[i] + GAMMA * np.max(batch_readout[i]))

            # perform gradient step
            train_step.run(feed_dict = {
                labels_placeholder : batch_y,
                action_placeholder : batch_action,
                IL : batch_replay_stack_1})

        # Update replay stack
        replay_stack_1 = replay_stack_2
        t += 1

        # Save after set iterations        
        if t % SAVE_TICK == 0:
            saver.save(sess, 'saved_networks/' + GAME + '-dqn', global_step = t)

def playGame():
    sess = tf.InteractiveSession()
    IL, ROL, H_FCL = createNetwork()
    trainNetwork(IL, ROL, H_FCL, sess)

def main():
    playGame()

if __name__ == "__main__":
    main()