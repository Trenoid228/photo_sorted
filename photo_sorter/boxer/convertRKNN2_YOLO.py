import os
import sys
import cv2
import numpy as np
import torch
import onnx

from ultralytics import YOLO
from dotenv import load_dotenv
from rknn.api import RKNN

load_dotenv()

def filter_boxes(boxes, box_confidences, box_class_probs):
    box_confidences = box_confidences.reshape(-1)
    candidate, class_num = box_class_probs.shape

    class_max_score = np.max(box_class_probs, axis=-1)
    classes = np.argmax(box_class_probs, axis=-1)

    _class_pos = np.where(class_max_score * box_confidences >= OBJ_THRESH)
    scores = (class_max_score * box_confidences)[_class_pos]

    boxes = boxes[_class_pos]
    classes = classes[_class_pos]

    return boxes, classes, scores


def nms_boxes(boxes, scores):
    x = boxes[:, 0]
    y = boxes[:, 1]
    w = boxes[:, 2] - boxes[:, 0]
    h = boxes[:, 3] - boxes[:, 1]

    areas = w * h
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x[i], x[order[1:]])
        yy1 = np.maximum(y[i], y[order[1:]])
        xx2 = np.minimum(x[i] + w[i], x[order[1:]] + w[order[1:]])
        yy2 = np.minimum(y[i] + h[i], y[order[1:]] + h[order[1:]])

        w1 = np.maximum(0.0, xx2 - xx1 + 0.00001)
        h1 = np.maximum(0.0, yy2 - yy1 + 0.00001)
        inter = w1 * h1

        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(ovr <= NMS_THRESH)[0]
        order = order[inds + 1]
    keep = np.array(keep)
    return keep


def dfl(position):
    x = torch.tensor(position)
    n, c, h, w = x.shape
    p_num = 4
    mc = c // p_num
    y = x.reshape(n, p_num, mc, h, w)
    y = y.softmax(2)
    acc_metrix = torch.tensor(range(mc)).float().reshape(1, 1, mc, 1, 1)
    y = (y * acc_metrix).sum(2)
    return y.numpy()


def box_process(position):
    grid_h, grid_w = position.shape[2:4]
    col, row = np.meshgrid(np.arange(0, grid_w), np.arange(0, grid_h))
    col = col.reshape(1, 1, grid_h, grid_w)
    row = row.reshape(1, 1, grid_h, grid_w)
    grid = np.concatenate((col, row), axis=1)
    stride = np.array([IMG_SIZE[1] // grid_h, IMG_SIZE[0] // grid_w]).reshape(1, 2, 1, 1)

    position = dfl(position)
    box_xy = grid + 0.5 - position[:, 0:2, :, :]
    box_xy2 = grid + 0.5 + position[:, 2:4, :, :]
    xyxy = np.concatenate((box_xy * stride, box_xy2 * stride), axis=1)

    return xyxy


def post_process_yolov10_single_class_batch(outputs, batch_size):

    defualt_branch = 3
    pair_per_branch = len(outputs) // defualt_branch

    batch_results = []

    for batch_idx in range(batch_size):
        all_boxes = []
        all_scores = []

        for i in range(defualt_branch):
            boxes_data = outputs[pair_per_branch * i]
            scores_data = outputs[pair_per_branch * i + 1]

            if len(boxes_data.shape) >= 4 and boxes_data.shape[0] == batch_size:
                boxes_single = boxes_data[batch_idx:batch_idx + 1]
                scores_single = scores_data[batch_idx:batch_idx + 1]
            else:
                boxes_single = boxes_data
                scores_single = scores_data

            boxes = box_process(boxes_single)
            scores = scores_single

            boxes = boxes.transpose(0, 2, 3, 1).reshape(-1, 4)
            scores = scores.transpose(0, 2, 3, 1).reshape(-1)

            all_boxes.append(boxes)
            all_scores.append(scores)

        boxes = np.concatenate(all_boxes, axis=0)
        scores = np.concatenate(all_scores, axis=0)

        # Фильтрация по порогу
        mask = scores >= OBJ_THRESH
        boxes = boxes[mask]
        scores = scores[mask]

        if len(boxes) == 0:
            batch_results.append((None, None, None))
            continue

        # NMS
        keep = nms_boxes(boxes, scores)

        if len(keep) == 0:
            batch_results.append((None, None, None))
            continue

        boxes = boxes[keep]
        scores = scores[keep]
        classes = np.zeros(len(boxes), dtype=np.int64)

        batch_results.append((boxes, classes, scores))

    return batch_results


def post_process_yolov10_single_class(input_data):
    defualt_branch = 3
    pair_per_branch = len(input_data) // defualt_branch

    all_boxes = []
    all_scores = []

    for i in range(defualt_branch):
        boxes = box_process(input_data[pair_per_branch * i])
        scores = input_data[pair_per_branch * i + 1]

        boxes = boxes.transpose(0, 2, 3, 1).reshape(-1, 4)
        scores = scores.transpose(0, 2, 3, 1).reshape(-1)

        all_boxes.append(boxes)
        all_scores.append(scores)

    boxes = np.concatenate(all_boxes, axis=0)
    scores = np.concatenate(all_scores, axis=0)

    mask = scores >= OBJ_THRESH
    boxes = boxes[mask]
    scores = scores[mask]

    if len(boxes) == 0:
        return None, None, None

    keep = nms_boxes(boxes, scores)

    if len(keep) == 0:
        return None, None, None

    boxes = boxes[keep]
    scores = scores[keep]
    classes = np.zeros(len(boxes), dtype=np.int64)

    return boxes, classes, scores


# def draw(image, boxes, scores, classes, file_name):
#     if flag:
#         # root=r"../Project_rknn/result_mini/labels/Train"
#         # root = r"./WORK_CVAT/total_ds/labels/Train"
#         root = r"./WORK_CVAT/first_annotation"
#         os.makedirs(root, exist_ok=True)
#         annot_path = os.path.join(root, file_name[:-4] + ".txt")
#         h, w = image.shape[:2]
#
#         with open(annot_path, "w") as f:
#             for box, score, cl in zip(boxes, scores, classes):
#                 x1, y1, x2, y2 = [int(coord) for coord in box]
#
#                 x1 = max(0, min(x1, w - 1))
#                 y1 = max(0, min(y1, h - 1))
#                 x2 = max(x1 + 1, min(x2, w))
#                 y2 = max(y1 + 1, min(y2, h))
#
#                 cx = (x1 + x2) / 2.0
#                 cy = (y1 + y2) / 2.0
#                 bw = x2 - x1
#                 bh = y2 - y1
#
#                 cx_n = cx / w
#                 cy_n = cy / h
#                 w_n = bw / w
#                 h_n = bh / h
#
#                 f.write(f"{cl} {cx_n:.6f} {cy_n:.6f} {w_n:.6f} {h_n:.6f}\n")
#
#                 cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 1)
#                 x_txt = (x1 + x2) // 2
#                 y_txt = (y1 + y2) // 2
#                 cv2.putText(image, f'{CLASSES[cl]} {score:.2f}',
#                             (x_txt, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

def draw(image, boxes, scores, classes):
    # root = r"./WORK_CVAT/first_annotation"
    # os.makedirs(root, exist_ok=True)
    # annot_path = os.path.join(root, file_name[:-4] + ".txt")
    h, w = image.shape[:2]
    for box, score, cl in zip(boxes, scores, classes):
        x1, y1, x2, y2 = [int(coord) for coord in box]

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        bw = x2 - x1
        bh = y2 - y1

        cx_n = cx / w
        cy_n = cy / h
        w_n = bw / w
        h_n = bh / h


        cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 1)
        x_txt = (x1 + x2) // 2
        y_txt = (y1 + y2) // 2
        cv2.putText(image, f'{CLASSES[cl]} {score:.2f}',
                    (x_txt, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

def convert_to_rknn():
    platform, do_quant, output_path, model_type = ["rv1126b", False, RKNN_MODEL_PATH, "i8"]

    rknn = RKNN(verbose=True)

    try:
        print('\n1. Конфигурация модели...')
        ret = rknn.config(
            mean_values=[[0, 0, 0]],
            std_values=[[255, 255, 255]],
            target_platform=platform,
            quant_img_RGB2BGR=False
        )

        print('\n2. Загрузка ONNX модели...')
        ret = rknn.load_onnx(model=ONNX_MODEL_PATH)
        if ret != 0:
            print('ОШИБКА загрузки модели!')
            exit(ret)
        print('   OK')

        print('\n3. Построение RKNN модели...')
        ret = rknn.build(
            do_quantization=do_quant,
            dataset=DATASET_PATH if do_quant else None
        )
        if ret != 0:
            print('ОШИБКА построения модели!')
            exit(ret)
        print('   OK')

        print('\n4. Экспорт RKNN модели...')
        ret = rknn.export_rknn(output_path)
        if ret != 0:
            print('ОШИБКА экспорта модели!')
            exit(ret)
        print('   OK')

    except Exception as e:
        print(f'\n✗ ОШИБКА: {e}')
        exit(1)
    return rknn


def get_batch_size_from_model(rknn):
    try:

        inputs = rknn.get_inputs()
        if inputs and len(inputs) > 0:
            input_shape = inputs[0].shape
            if len(input_shape) > 0:
                batch_size = input_shape[0]
                return batch_size
    except:
        pass
    return 1


if __name__ == '__main__':

    DATASET_PATH = os.getenv('DATASET_PATH', './dataset.txt')
    ONNX_MODEL_PATH = os.getenv('ONNX_MODEL_PATH', '../../c/Users/Professional/Downloads/best_19052026.onnx')
    # ONNX_MODEL_PATH = os.getenv('ONNX_MODEL_PATH', '../../c/Users/Professional/Downloads/yolov10s_body_v14_416.onnx')
    RKNN_MODEL_PATH = os.getenv('RKNN_MODEL_PATH', './models/rknn/yolo10_v17_48k_c1_v2_RGB_1212.rknn')
    INPUT_SIZE = 416
    IMG_SIZE = (INPUT_SIZE, INPUT_SIZE)
    flag = True
    OBJ_THRESH = 0.24
    NMS_THRESH = 0.35

    CLASSES = ("person")
    rknn = convert_to_rknn()
    rknn.init_runtime()

    MODEL_BATCH_SIZE = 1

    root = os.getenv('ROOT','./dataset')
    # root = r"../Project_rknn/big_view"
    # root = r"./WORK_CVAT/total_ds/images/Train"
    # root = r"../Project_rknn/result_mini/images/Train"
    img_dir = os.listdir(root)

    os.makedirs("./yolo_rknn_res1", exist_ok=True)

    if MODEL_BATCH_SIZE == 1:
        print("\n🔄 Режим обработки: batch=1 (по одному изображению)")
        for img_file in img_dir:
            if not img_file.endswith(".jpg"):
                continue

            img_tmp = cv2.imread(os.path.join(root, img_file))
            if img_tmp is None:
                continue

            img = cv2.cvtColor(img_tmp, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE))
            inp_img = np.expand_dims(img, 0)

            outputs = rknn.inference([inp_img])
            boxes, classes, scores = post_process_yolov10_single_class(outputs)

            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            print(f"{img_file}: {len(boxes) if boxes is not None else 0} объектов")

            if boxes is not None:
                draw(img, boxes, scores, classes)
                cv2.imwrite(f"./yolo_rknn_res1/{img_file}.jpg", img)


    else:

        img_files = [f for f in img_dir if f.endswith(".jpg")]

        for i in range(0, len(img_files), MODEL_BATCH_SIZE):
            batch_files = img_files[i:i + MODEL_BATCH_SIZE]

            batch_images = []
            valid_files = []

            for img_file in batch_files:
                img_path = os.path.join(root, img_file)
                img = cv2.imread(img_path)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE))
                    batch_images.append(img)
                    valid_files.append(img_file)
            while len(batch_images) < MODEL_BATCH_SIZE and len(batch_images) > 0:
                batch_images.append(batch_images[-1])
                valid_files.append(valid_files[-1])

            if len(batch_images) == 0:
                continue

            batch_input = np.stack(batch_images, axis=0)  # [batch, H, W, C]
            outputs = rknn.inference([batch_input])
            batch_results = post_process_yolov10_single_class_batch(outputs, len(batch_images))

            for idx, img_file in enumerate(valid_files):
                if idx >= len(batch_results):
                    break

                boxes, classes, scores = batch_results[idx]
                img_draw = cv2.imread(os.path.join(root, img_file))
                img_draw = cv2.cvtColor(img_draw, cv2.COLOR_BGR2RGB)
                img_draw = cv2.resize(img_draw, (INPUT_SIZE, INPUT_SIZE))
                img_draw = cv2.cvtColor(img_draw, cv2.COLOR_RGB2BGR)

                print(f"  {img_file}: {len(boxes) if boxes is not None else 0} объектов")

                if boxes is not None and len(boxes) > 0:
                    draw(img_draw, boxes, scores, classes, img_file)
                    if len(scores) > 0:
                        print(f" max confidence: {scores[0]:.3f}")

                cv2.imwrite(f"./yolo_rknn_res1/{img_file}.jpg", img_draw)

    print("Обработка завершена!")
    rknn.release()