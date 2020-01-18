# coding=utf-8
import os


# Enable GPU 0
from tf_geometric.utils.graph_utils import convert_edge_index_to_undirected

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import tf_geometric as tfg
from tf_geometric.layers import GCN, MapReduceGNN, GAT
from tf_geometric.datasets.ppi import PPIDataset
import tensorflow as tf
import numpy as np


# ==================================== Graph Data Structure ====================================
# In tf_geometric, graph data can be either individual Tensors or Graph objects
# A graph usually consists of x(node features), edge_index and edge_weight(optional)

# Node Features => (num_nodes, num_features)
x = np.random.randn(5, 20).astype(np.float32) # 5 nodes, 20 features

# Edge Index => (2, num_edges)
# edge_index is directed
edge_index = np.array([
    [0, 0, 1, 3],
    [1, 2, 2, 1]
])

# Edge Weight => (num_edges)
edge_weight = np.array([0.9, 0.8, 0.1, 0.2]).astype(np.float32)

# Make the edge_index undirected such that we can use it as the input of GCN
edge_index, edge_weight = convert_edge_index_to_undirected(edge_index, edge_weight=edge_weight)


# We can convert these numpy array as TensorFlow Tensors and pass them to gnn functions
outputs = tfg.nn.gcn(
    tf.Variable(x),
    tf.constant(edge_index),
    tf.constant(edge_weight),
    tf.Variable(tf.random.truncated_normal([20, 2])), # GCN Weight
)
print(outputs)

# Usually, we use a graph object to manager these information
# edge_weight is optional, we can set it to None if you don't need it
graph = tfg.Graph(x=x, edge_index=edge_index, edge_weight=edge_weight)

# You can easily convert these numpy arrays as Tensors with the Graph Object API
graph.convert_data_to_tensor()

# Then, we can use them without too many manual conversion
outputs = tfg.nn.gcn(
    graph.x,
    graph.edge_index,
    graph.edge_weight,
    tf.Variable(tf.random.truncated_normal([20, 2])),  # GCN Weight
    cache=graph.cache  # GCN use caches to avoid re-computing of the normed edge information
)
print(outputs)


# For algorithms that deal with batches of graphs, we can pack a batch of graph into a BatchGraph object
# Batch graph wrap a batch of graphs into a single graph, where each nodes has an unique index and a graph index.
# The node_graph_index is the index of the corresponding graph for each node in the batch.
# The edge_graph_index is the index of the corresponding edge for each node in the batch.
batch_graph = tfg.BatchGraph.from_graphs([graph, graph, graph, graph])

# Graph Pooling algorithms often rely on such batch data structure
# Most of them accept a BatchGraph's data as input and output a feature vector for each graph in the batch
outputs = tfg.nn.mean_pooling(batch_graph.x, batch_graph.node_graph_index, num_graphs=batch_graph.num_graphs)
print(outputs)

# We can reversely split a BatchGraph object into Graphs objects
graphs = batch_graph.to_graphs()




# ==================================== Built-in Datasets ====================================
# all graph data are in numpy format
train_data, valid_data, test_data = PPIDataset().load_data()

# we can convert them into tensorflow format
test_data = [graph.convert_data_to_tensor() for graph in test_data]





# ==================================== Basic OOP API ====================================
# OOP Style GCN (Graph Convolutional Network)
gcn_layer = GCN(units=20, activation=tf.nn.relu)

for graph in test_data:
    # Cache can speed-up GCN by caching the normed edge information
    outputs = gcn_layer([graph.x, graph.edge_index, graph.edge_weight], cache=graph.cache)
    print(outputs)


# OOP Style GAT (Graph Attention Network)
gat_layer = GAT(units=20, activation=tf.nn.relu)
for graph in test_data:
    outputs = gat_layer([graph.x, graph.edge_index])
    print(outputs)



# ==================================== Basic Functional API ====================================
# Functional Style GCN
# Functional API is more flexible for advanced algorithms
# You can pass both data and parameters to functional APIs

dense_w = tf.Variable(tf.random.truncated_normal([test_data[0].num_features, 20]))
for graph in test_data:
    outputs = tfg.nn.gcn(graph.x, edge_index, edge_weight, dense_w, activation=tf.nn.relu)
    print(outputs)


# ==================================== Advanced OOP API ====================================
# All APIs are implemented with Map-Reduce Style
# This is a gcn without weight normalization and transformation.
# Create your own GNN Layer by subclassing the MapReduceGNN class
class NaiveGCN(MapReduceGNN):

    def map(self, repeated_x, neighbor_x, edge_weight=None):
        return tfg.nn.identity_mapper(repeated_x, neighbor_x, edge_weight)

    def reduce(self, neighbor_msg, node_index, num_nodes=None):
        return tfg.nn.sum_reducer(neighbor_msg, node_index, num_nodes)

    def update(self, x, reduced_neighbor_msg):
        return tfg.nn.sum_updater(x, reduced_neighbor_msg)


naive_gcn = NaiveGCN()

for graph in test_data:
    print(naive_gcn([graph.x, graph.edge_index, graph.edge_weight]))


# ==================================== Advanced Functional API ====================================
# All APIs are implemented with Map-Reduce Style
# This is a gcn without without weight normalization and transformation
# Just pass the mapper/reducer/updater functions to the Functional API

for graph in test_data:
    outputs = tfg.nn.aggregate_neighbors(
        x=graph.x,
        edge_index=graph.edge_index,
        edge_weight=graph.edge_weight,
        mapper=tfg.nn.identity_mapper,
        reducer=tfg.nn.sum_reducer,
        updater=tfg.nn.sum_updater
    )
    print(outputs)
