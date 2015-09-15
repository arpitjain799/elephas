from __future__ import absolute_import

import numpy as np

from pyspark.sql import Row
from pyspark.ml import Estimator, Transformer

from .spark_model import SparkModel
from .utils.rdd_utils import from_vector, to_vector
from .ml.adapter import df_to_simple_rdd

class ElephasEstimator(SparkModel, Estimator):
    def __init__(self, sc, master_network, categorical=True):
        super(ElephasEstimator, self).__init__(sc, master_network)
        self.categorical = categorical

    def _fit(self, df):
        simple_rdd = df_to_simple_rdd(df, categorical=self.categorical)
        print '>>> Converted to RDD'
        self.train(simple_rdd)
        print '>>> Training phase done'
        return ElephasTransformer(self.spark_context, self.master_network)

class ElephasTransformer(SparkModel, Transformer):
    def __init__(self, sc, master_network):
        super(ElephasTransformer, self).__init__(sc, master_network)

    def _transform(self, df):
        rdd = df.rdd
        features = np.asarray(rdd.map(lambda x: from_vector(x.features)).collect())
        # Note that we collect, since executing this on the rdd would require model serialization once again
        predictions = self.spark_context.parallelize(self.master_network.predict_classes(features))
        results_rdd = rdd.zip(predictions).map(lambda pair: Row(features=to_vector(pair[0].features), 
                                                        label=pair[0].label, prediction=float(pair[1])))
        results_df = df.sql_ctx.createDataFrame(results_rdd)
        return results_df
