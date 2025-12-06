import numpy as np
import tensorflow as tf

class ASLModel:
    def __init__(self, tflite_path):
        # Load TFLite model
        self.interpreter = tf.lite.Interpreter(model_path=tflite_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()[0]
        self.output_details = self.interpreter.get_output_details()[0]

        # Expected input shape
        self.feature_dim = self.input_details["shape"][1]

    def predict(self, feature_vector: np.ndarray):
        """
        feature_vector: np.ndarray shape (n_samples, feature_dim)
        returns: (pred_indices, confidences)
        """
        fv = feature_vector.astype(np.float32)
        if fv.ndim == 1:
            fv = np.expand_dims(fv, 0)
        if fv.shape[1] != self.feature_dim:
            raise ValueError(f"Expected feature size {self.feature_dim}, got {fv.shape[1]}")

        self.interpreter.set_tensor(self.input_details["index"], fv)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details["index"])
        preds = np.argmax(output, axis=1)
        confidences = np.max(output, axis=1)
        return preds, confidences
