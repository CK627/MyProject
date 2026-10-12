# -*- coding: utf-8 -*-
"""JudgeNet 二进制模型 I/O（.ctfj 单一格式，轻量版 ONNX/GGUF 风格）。

唯一格式：.ctfj (CtfSweep JudgeNet Binary)
（旧版 JSON 模型格式已移除——模型统一用二进制 .ctfj，加载更快、体积更小）

二进制格式规范（.ctfj）:
    Magic: 4 bytes "CTFJ"
    Version: 4 bytes LE uint32 (当前 = 1)
    Num features: 4 bytes LE uint32
    Feature names: [utf8 string, length-prefixed]
    Num members: 4 bytes LE uint32
    For each member:
        Num layers: 4 bytes LE uint32
        Layers: [(input_dim, output_dim), ...]
        Weights: float32 row-major, size = sum(input*output + output)
        Biases: float32 row-major, size = sum(output)

用法:
    from ctfsweep.core import model_io
    model_io.save_binary(predictor, 'model.ctfj')  # 保存
    predictor = model_io.load_binary('model.ctfj')  # 加载
"""
import struct
import os


# ================================================================= 常量
MAGIC = b'CTFJ'  # CtfSweep JudgeNet
VERSION = 1
FLOAT_SIZE = 4  # float32


# ================================================================= 二进制保存
def save_binary(predictor, path, features=None):
    """保存 JudgePredictor 为二进制格式。

    Args:
        predictor: JudgePredictor 实例
        path: 输出路径（.ctfj 或 .bin）
        features: 特征列表（可选，默认使用 ctfsweep.core.judge.FEATURES）
    """
    import array
    from ctfsweep.core.judge import FEATURES
    features = features or list(FEATURES)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    with open(path, 'wb') as f:
        # Header
        f.write(MAGIC)  # 4 bytes
        f.write(struct.pack('<I', VERSION))  # 4 bytes
        f.write(struct.pack('<I', len(features)))  # 4 bytes

        # Feature names
        for feat in features:
            feat_bytes = feat.encode('utf-8')
            f.write(struct.pack('<I', len(feat_bytes)))
            f.write(feat_bytes)

        # Members
        f.write(struct.pack('<I', len(predictor.nets)))

        for net in predictor.nets:
            # Architecture
            f.write(struct.pack('<I', len(net.sizes) - 1))  # num layers
            for i in range(len(net.sizes) - 1):
                f.write(struct.pack('<II', net.sizes[i], net.sizes[i + 1]))

            # Weights (row-major float32)
            # W[layer][neuron][input_dim]
            all_weights = []
            for layer in net.W:
                for neuron in layer:
                    all_weights.extend(neuron)
            f.write(struct.pack('<I', len(all_weights)))
            f.write(array.array('f', all_weights).tobytes())

            # Biases (row-major float32)
            # b[layer][neuron]
            all_biases = []
            for layer in net.b:
                all_biases.extend(layer)
            f.write(struct.pack('<I', len(all_biases)))
            f.write(array.array('f', all_biases).tobytes())

    file_size = os.path.getsize(path)
    print('已保存二进制模型: %s (%d bytes)' % (path, file_size))
    return path


# ================================================================= 二进制加载
def load_binary(path):
    """加载二进制模型为 JudgePredictor。"""
    import array
    from ctfsweep.core.judge import JudgeNet, JudgePredictor, FEATURES, param_count

    with open(path, 'rb') as f:
        # Header
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError('无效的模型格式（期望 %r，实际 %r）' % (MAGIC, magic))

        version = struct.unpack('<I', f.read(4))[0]
        if version != VERSION:
            raise ValueError('不支持的模型版本 %d（期望 %d）' % (version, VERSION))

        num_features = struct.unpack('<I', f.read(4))[0]

        # Feature names
        loaded_features = []
        for _ in range(num_features):
            feat_len = struct.unpack('<I', f.read(4))[0]
            feat_bytes = f.read(feat_len)
            loaded_features.append(feat_bytes.decode('utf-8'))

        # Check feature compatibility
        if loaded_features != list(FEATURES):
            raise ValueError(
                '模型特征版本不一致（期望 %d 维，实际 %d 维）\n'
                '请重新运行 `ctfsweep train` 训练模型。'
                % (len(FEATURES), num_features)
            )

        # Members
        num_members = struct.unpack('<I', f.read(4))[0]
        nets = []

        for _ in range(num_members):
            # Architecture
            num_layers = struct.unpack('<I', f.read(4))[0]

            # Read architecture as (input_dim, output_dim) pairs
            architecture = []
            for _ in range(num_layers):
                input_dim, output_dim = struct.unpack('<II', f.read(8))
                architecture.append((input_dim, output_dim))

            # Reconstruct sizes from architecture
            sizes = [architecture[0][0]]  # input dim
            for input_dim, output_dim in architecture:
                sizes.append(output_dim)

            # Create net
            net = JudgeNet.__new__(JudgeNet)
            net.sizes = sizes
            net.W = []
            net.b = []
            net._zs, net._acts = [], []

            # Weights
            # W[layer][neuron][input_dim] - row-major, flattened
            w_count = struct.unpack('<I', f.read(4))[0]
            all_w = list(struct.unpack('<%df' % w_count, f.read(w_count * 4)))

            idx = 0
            for li, (input_dim, output_dim) in enumerate(architecture):
                W_layer = []
                for _ in range(output_dim):
                    w = all_w[idx:idx + input_dim]
                    W_layer.append(w)
                    idx += input_dim
                net.W.append(W_layer)

            # Biases
            # b[layer][neuron]（先读数量前缀，与保存端对称）
            b_count = struct.unpack('<I', f.read(4))[0]
            all_b = list(struct.unpack('<%df' % b_count, f.read(b_count * 4)))

            idx = 0
            for li, (input_dim, output_dim) in enumerate(architecture):
                b_layer = all_b[idx:idx + output_dim]
                net.b.append(b_layer)
                idx += output_dim

            nets.append(net)

    predictor = JudgePredictor(nets, meta={'format': 'ctfj', 'version': VERSION})
    print('已加载二进制模型: %s (%s)' % (path, predictor.describe()))
    return predictor


# ================================================================= 模型加载（自动）
def load_model(path):
    """加载模型（.ctfj 二进制格式；无扩展名时按二进制尝试）。"""
    return load_binary(path)
