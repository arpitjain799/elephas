import pytest
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential
from elephas.utils import serialization


def test_model_to_dict():
    model = Sequential()
    model.add(Dense(1, input_shape=(1,)))
    dict_model = serialization.model_to_dict(model)
    assert list(dict_model.keys()) == ['model', 'weights']


def test_dict_to_model():
    model = Sequential()
    model.add(Dense(1, input_shape=(1,)))
    dict_model = serialization.model_to_dict(model)

    recovered = serialization.dict_to_model(dict_model)
    assert recovered.to_json() == model.to_json()
