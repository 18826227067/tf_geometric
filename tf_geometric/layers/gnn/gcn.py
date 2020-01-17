from tensorflow.python.keras.layers import Dense

import tensorflow as tf
from tf_geometric import Graph
from tf_geometric.nn import gcn_mapper, sum_reducer, sum_updater, gcn_norm, aggregate_neighbors
from tf_geometric.layers.kernel.map_reduce import MapReduceGNN


class GCN(MapReduceGNN):

    def __init__(self, units, activation=None, use_cache=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_cache = use_cache

        self.acvitation = activation
        self.dense = Dense(units=units, use_bias=False)
        self.bias = tf.Variable(tf.zeros([units]))

    def map(self, repeated_x, neighbor_x, edge_weight=None):
        return gcn_mapper(repeated_x, neighbor_x, edge_weight)

    def reduce(self, neighbor_msg, node_index, num_nodes=None):
        return sum_reducer(neighbor_msg, node_index, num_nodes)

    def update(self, x, reduced_neighbor_msg):
        return sum_updater(x, reduced_neighbor_msg)

    @classmethod
    def create_normed_edge_weight(cls, graph: Graph, use_cache=True):
        if use_cache and graph.cached_normed_edge_weight is not None:
            return graph.cached_normed_edge_weight
        else:
            normed_edge_weight = gcn_norm(graph.edge_index, graph.num_nodes, graph.edge_weight)
            if use_cache:
                graph.cached_normed_edge_weight = normed_edge_weight
            return normed_edge_weight

    def call(self, inputs, training=None, mask=None):

        x, edge_index, normed_edge_weight = inputs
        x = self.dense(x)

        h = aggregate_neighbors(
            x,
            edge_index,
            normed_edge_weight,
            self.get_mapper(),
            self.get_reducer(),
            self.get_updater()
        )

        h += self.bias

        if self.acvitation is not None:
            h = self.acvitation(h)

        return h